"""Bounded trusted-adapter executor. No natural-language commands, shell, or implicit accounts.

A supervising service must invoke this executor; this module installs no timer.
Adapter callbacks are a trusted integration boundary, not model-selected plugins.
"""
from dataclasses import dataclass
import hashlib
import json
import threading
import time

from cloud.job_policy import OPAQUE, due_slot


class LimitReached(ValueError):pass
class ReviewRequired(RuntimeError):pass


@dataclass(frozen=True)
class LinkRequest:
    item: str           # Opaque verified inbound item reference, not message text.
    account: str
    target: str         # Opaque recipient reference resolved by the trusted connector.
    resource: str       # Exact key in the owner-approved catalogue.


@dataclass(frozen=True)
class Result:
    body: bytes
    important: int = 0
    uncertain: int = 0
    replies: tuple = ()
    partial: bool = False


class Context:
    def __init__(self,store,job,run,epoch,clock,monotonic,cancelled,scheduled):
        self.store,self.job,self.run,self.epoch=store,job,run,epoch
        self.clock,self.monotonic,self.cancelled=clock,monotonic,cancelled
        self.deadline=monotonic()+job.limits.seconds
        self.window_end=scheduled
        self.window_start=scheduled-job.lookback_hours*3600
        self.calls=self.items=self.sends=0

    def check(self):
        if self.cancelled.is_set():raise InterruptedError('cancelled')
        if self.monotonic()>=self.deadline:raise LimitReached('time_limit')
        if not self.store.active(self.job.id,self.job.digest(),self.epoch,self.clock()):
            raise PermissionError('delegation_changed')
        if self.monotonic()>=self.deadline:raise LimitReached('time_limit')

    def request(self):
        self.check()
        if self.calls>=self.job.limits.requests:raise LimitReached('request_limit')
        self.calls+=1

    def item(self):
        self.check()
        if self.items>=self.job.limits.items:raise LimitReached('item_limit')
        self.items+=1

    def outgoing(self):
        self.check()
        if self.sends>=self.job.limits.sends:raise LimitReached('send_limit')
        self.sends+=1


class Runner:
    def __init__(self,store,*,placement,adapters=None,reports=None,clock=time.time,monotonic=time.monotonic):
        if placement not in ('oracle','desktop'):raise ValueError('Unknown runner placement.')
        self.store,self.placement=store,placement
        self.adapters=adapters or {};self.reports=reports
        self.clock,self.monotonic=clock,monotonic

    def execute(self,job,cancelled=None):
        job.validate();slot=due_slot(job,self.clock())
        if slot is None:return None
        epoch=self.store.claim(job,slot,self.clock())
        if epoch is None:return self.store.view(slot['id'])
        context=Context(self.store,job,slot['id'],epoch,self.clock,self.monotonic,cancelled or threading.Event(),slot['scheduled'])
        state,reason='failed','adapter_error'
        result=None
        def usage():
            return {'requests':context.calls,'items':context.items,'reply_attempts':context.sends,
                    'result_bytes':len(result.body) if isinstance(result,Result) and type(result.body) is bytes else 0}
        try:
            context.check()
            if job.placement!=self.placement:raise PermissionError('wrong_placement')
            adapter=self.adapters.get(job.kind)
            if adapter is None or adapter.preflight(job) is not True:raise PermissionError('connector_or_account_unavailable')
            if getattr(adapter,'zero_spend',False) is not True:raise PermissionError('zero_spend_not_established')
            if self.reports is None or self.reports.supports(job) is not True:raise PermissionError('protected_report_store_unavailable')
            result=adapter.collect(job,context)
            context.check()
            if not isinstance(result,Result) or type(result.body) is not bytes or not result.body.strip() or type(result.partial) is not bool:
                raise ValueError('Invalid bounded adapter result.')
            if len(result.body)>job.limits.result_bytes:raise LimitReached('result_byte_limit')
            if any(type(n) is not int or not 0<=n<=context.items for n in (result.important,result.uncertain)) or result.important+result.uncertain>context.items:
                raise ValueError('Invalid importance counts.')
            if type(result.replies) is not tuple or len(result.replies)>context.items:
                raise ValueError('Invalid bounded link-request list.')
            for request in result.replies:
                context.check()
                if not isinstance(request,LinkRequest) or not OPAQUE.fullmatch(request.item) or not OPAQUE.fullmatch(request.target):
                    raise PermissionError('unverified_inbound_target')
                if request.account!=job.account or request.resource not in dict(job.catalog):
                    raise PermissionError('out_of_scope_link_request')
                if adapter.validate_inbound(job,request) is not True:raise PermissionError('unverified_inbound_target')
                if job.send_mode=='draft_only':continue
                url=dict(job.catalog)[request.resource]
                # One reply per original item/account, even across revisions or duplicate jobs.
                key=hashlib.sha256((request.account+'\n'+request.item).encode()).hexdigest()
                payload=hashlib.sha256((request.target+'\n'+url).encode()).hexdigest()
                context.outgoing();context.request()
                if not self.store.prepare_action(slot['id'],job,epoch,key,payload,self.clock()):continue
                try:
                    receipt=adapter.send_approved_link(job,request,url,context)
                    # Record a trusted receipt even if authority changed while the I/O ran.
                    self.store.action_receipt(key,receipt)
                except Exception as exc:
                    raise ReviewRequired('send_outcome_unknown') from exc
                context.check()
            context.check()
            report=self.reports.write(job,slot['id'],result.body,self.clock()+job.retention_hours*3600)
            if type(report) is not str or not OPAQUE.fullmatch(report):raise ValueError('Report must have an opaque durable reference.')
            context.check()
            notify=(result.partial or job.notification_filter=='always' or result.important>0
                    or (job.notification_filter=='important_or_uncertain' and result.uncertain>0))
            self.store.end(slot['id'],'partial' if result.partial else 'completed',
                report=report,expires=self.clock()+job.retention_hours*3600,important=result.important,
                uncertain=result.uncertain,notify=notify,now=self.clock(),usage=usage())
            return self.store.view(slot['id'])
        except InterruptedError:state,reason='cancelled','cancelled'
        except PermissionError as exc:
            state,reason='blocked',str(exc) if str(exc) in ('wrong_placement','connector_or_account_unavailable','zero_spend_not_established','protected_report_store_unavailable','unverified_inbound_target','out_of_scope_link_request','delegation_changed') else 'permission_denied'
        except LimitReached as exc:
            state,reason='limit_reached',str(exc) if str(exc) in ('time_limit','request_limit','item_limit','result_byte_limit','send_limit') else 'resource_limit'
        except ReviewRequired:state,reason='needs_review','send_outcome_unknown'
        except RuntimeError:state,reason='needs_review','outgoing_reconciliation_required'
        except Exception:state,reason='failed','adapter_or_report_error'
        self.store.end(slot['id'],state,reason,now=self.clock(),usage=usage())
        return self.store.view(slot['id'])

    def notify(self,job,run,notifier):
        """A separate invocation at/after the report time; no one-hour busy wait.

        The trusted notifier must independently enforce owner routing and current
        notification consent. A receipt acknowledges a request, not human reading.
        """
        if notifier is None or getattr(notifier,'zero_spend',False) is not True or notifier.preflight(job) is not True:return False
        row=self.store.notification_claim(run,self.clock(),job)
        if row is None:return False
        # A delayed report must remain bound to its original owner/contract.
        if row['digest']!=job.digest():raise PermissionError('Notification contract mismatch.')
        try:
            receipt=notifier.notify_owner(job.owner,row['report'],run,timeout=10)
            self.store.notification_receipt(run,receipt)
            return True
        except Exception:
            return False  # Keep 'requesting': never blindly repeat an uncertain push.
