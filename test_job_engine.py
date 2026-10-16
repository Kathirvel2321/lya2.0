"""Task-governance lab: fake owner proof/accounts, temporary metadata and in-memory private reports."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import Mock

from cloud.job_policy import Job, Limits, due_slot, from_dict
from cloud.job_store import JobStore
from cloud.job_runner import Runner, Result, LinkRequest
from cloud.job_adapters import PublicReports, TechnologyUpdates


def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
START=stamp('2026-10-16T12:30:00Z')  # 18:00 Asia/Kolkata.
NOTIFY=stamp('2026-10-16T13:30:00Z')


def spec(**values):
    base=Job('fixture_job',1,'inbox_review','oracle','private','18:00','19:00',
        account='account_fake',owner='owner_fake',private_remote=True,importance_rules=('fixture_rules',),
        catalog=(('video_link','https://example.invalid/video'),),
        limits=Limits(seconds=60,requests=8,items=20,result_bytes=4096,sends=3))
    return replace(base,**values).validate()


def request(**values):
    data={'item':'a'*64,'account':'account_fake','target':'b'*64,'resource':'video_link'};data.update(values)
    return LinkRequest(**data)


class Reports:
    """Test-only RAM sink. Never a production private-storage qualification."""
    def __init__(self,private=True):self.private=private;self.values={}
    def supports(self,job):return job.sensitivity=='public' or self.private
    def write(self,job,run,body,expires):
        key=hashlib.sha256(run.encode()+body).hexdigest();self.values[key]=(body,expires);return key


class Connector:
    zero_spend=True
    def __init__(self):
        self.collects=0;self.sent=[];self.requests=();self.important=1;self.uncertain=0;self.partial=False
    def preflight(self,job):return job.account=='account_fake'
    def collect(self,job,context):
        self.collects+=1;context.request();context.item()
        return Result(b'PRIVATE_FAKE_MESSAGE_CANARY',self.important,self.uncertain,self.requests,self.partial)
    def validate_inbound(self,job,item):return item.target=='b'*64
    def send_approved_link(self,job,item,url,context):
        self.sent.append((item.target,url));return 'c'*64


class PolicyChecks(unittest.TestCase):
    def test_schema_and_full_contract_digest_are_stable(self):
        job=spec();self.assertEqual(from_dict(json.loads(job.canonical())),job)
        self.assertNotEqual(job.digest(),replace(job,notify='20:00').digest())
        self.assertNotEqual(job.digest(),replace(job,limits=replace(job.limits,requests=7)).digest())

    def test_unknown_authority_fields_and_commands_are_rejected(self):
        data=json.loads(spec().canonical())
        for key in ('approved','shell','webhook','token','command'):
            with self.subTest(key=key),self.assertRaises(ValueError):from_dict({**data,key:'do it'})

    def test_private_cloud_needs_explicit_permission_and_exact_public_links(self):
        for changes in ({'private_remote':False},{'zero_spend':False},{'placement':'anywhere'},
                        {'catalog':(('video_link','http://example.invalid'),)},
                        {'catalog':(('video_link','https://example.invalid/?token=SECRET'),)}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):spec(**changes)

    def test_invalid_budgets_and_ambiguous_time_are_refused(self):
        for change in ({'seconds':0},{'requests':True},{'sends':21},{'result_bytes':70000}):
            with self.subTest(change=change),self.assertRaises(ValueError):spec(limits=replace(Limits(),**change))
        for time in ('6pm','18','25:00','18:80'):
            with self.assertRaises(ValueError):spec(start=time)

    def test_six_pm_work_and_seven_pm_report_are_distinct(self):
        slot=due_slot(spec(),START);self.assertEqual(slot['scheduled'],START);self.assertEqual(slot['notify'],NOTIFY)
        self.assertIsNone(due_slot(spec(),START-1))
        self.assertEqual(due_slot(spec(),START+900)['late_seconds'],900)
        self.assertIsNone(due_slot(spec(),START+1801))

    def test_dst_gap_skips_and_repeat_uses_first_occurrence(self):
        job=spec(zone='America/New_York',start='02:30',notify='03:30')
        self.assertIsNone(due_slot(job,stamp('2026-03-08T07:30:00Z')))
        job=replace(job,start='01:30',notify='03:30',catchup_seconds=7200)
        first=due_slot(job,stamp('2026-11-01T05:30:00Z'))
        second=due_slot(job,stamp('2026-11-01T06:30:00Z'))
        self.assertEqual(first['id'],second['id'])

    def test_important_filter_requires_owner_rules_and_input_window_is_bounded(self):
        with self.assertRaises(ValueError):spec(importance_rules=())
        with self.assertRaises(ValueError):spec(lookback_hours=10000)

    def test_next_day_notification_and_retention_bounds(self):
        job=spec(start='23:00',notify='00:30')
        slot=due_slot(job,stamp('2026-10-16T17:30:00Z'))
        self.assertEqual(slot['notify'],stamp('2026-10-16T19:00:00Z'))
        with self.assertRaises(ValueError):spec(retention_hours=25)


class EngineChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'jobs.sqlite';self.now=START;self.mono=0
        self.verifications=[]
        def verify(operation,job,proof):
            self.verifications.append((operation,job.digest()))
            return proof=='FAKE_VERIFIED_OWNER_PROOF' and job.owner=='owner_fake'
        self.store=JobStore(self.path,verify);self.job=spec();self.connector=Connector();self.reports=Reports()
        self.runner=Runner(self.store,placement='oracle',adapters={'inbox_review':self.connector},reports=self.reports,
                           clock=lambda:self.now,monotonic=lambda:self.mono)
        self.proof='FAKE_VERIFIED_OWNER_PROOF'

    def enable(self,job=None):self.store.enable(job or self.job,self.proof,self.now,self.now+2*86400)
    def execute_fixture(self,job=None):return self.runner.execute(job or self.job)

    def test_default_deny_and_unapproved_spec_cannot_execute(self):
        with self.assertRaises(PermissionError):JobStore(self.path).enable(self.job,self.proof,self.now,self.now+100)
        with self.assertRaises(PermissionError):self.execute_fixture()
        self.assertEqual(self.connector.collects,0)

    def test_revision_account_schedule_or_send_changes_need_new_approval(self):
        self.enable()
        for job in (replace(self.job,notify='20:00'),replace(self.job,account='another_account'),replace(self.job,send_mode='approved_catalog')):
            with self.assertRaises(PermissionError):self.execute_fixture(job)
        self.assertEqual(self.connector.collects,0)

    def test_completed_collection_persists_no_private_body_in_metadata(self):
        self.enable();result=self.execute_fixture();self.assertEqual(result['state'],'completed')
        self.assertIn(result['report'],self.reports.values)
        self.assertEqual(result['started'],START);self.assertEqual(result['finished'],START)
        self.assertEqual(result['usage']['items'],1)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT digest FROM contracts').fetchone()[0],self.job.digest())
        self.assertNotIn(b'PRIVATE_FAKE_MESSAGE_CANARY',self.path.read_bytes())
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT state FROM outbox').fetchone()[0],'pending')

    def test_restart_and_second_worker_cannot_repeat_same_slot(self):
        self.enable();first=self.execute_fixture();second=self.execute_fixture()
        self.assertEqual(first,second);self.assertEqual(self.connector.collects,1)
        fresh=Runner(JobStore(self.path),placement='oracle',adapters={'inbox_review':self.connector},reports=self.reports,clock=lambda:self.now)
        self.assertEqual(fresh.execute(self.job)['id'],first['id']);self.assertEqual(self.connector.collects,1)

    def test_concurrent_claim_is_atomic(self):
        self.enable();slot=due_slot(self.job,self.now)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda _:self.store.claim(self.job,slot,self.now),range(10)))
        self.assertEqual(sum(result is not None for result in results),1)

    def test_wrong_place_missing_connector_or_private_sink_blocks_before_read(self):
        for kind in ('place','connector','sink'):
            with self.subTest(kind=kind):
                job=replace(self.job,id='fixture_'+kind);self.enable(job)
                runner=Runner(self.store,placement='desktop' if kind=='place' else 'oracle',
                    adapters={} if kind=='connector' else {'inbox_review':self.connector},
                    reports=Reports(private=False) if kind=='sink' else self.reports,clock=lambda:self.now)
                self.assertEqual(runner.execute(job)['state'],'blocked')
        self.assertEqual(self.connector.collects,0)

    def test_paid_or_unestablished_connector_is_blocked(self):
        self.enable();self.connector.zero_spend=False
        self.assertEqual(self.execute_fixture()['reason'],'zero_spend_not_established');self.assertEqual(self.connector.collects,0)

    def test_revocation_during_collection_stops_reply_and_report_commit(self):
        self.enable();old=self.connector.collect
        def collect(job,ctx):
            result=old(job,ctx);self.store.revoke(job,self.proof);return result
        self.connector.collect=collect
        self.assertEqual(self.execute_fixture()['state'],'blocked');self.assertEqual(self.connector.sent,[]);self.assertEqual(self.reports.values,{})

    def test_time_call_item_and_result_caps_stop_work(self):
        original=self.connector.collect
        for name in ('time','calls','items','bytes'):
            job=replace(self.job,id='limit_'+name);self.enable(job)
            def collect(job,ctx):
                if name=='time':self.mono+=100
                elif name=='calls':
                    for _ in range(9):ctx.request()
                elif name=='items':
                    for _ in range(21):ctx.item()
                else:
                    ctx.item();return Result(b'x'*4097,important=1)
                return original(job,ctx)
            self.connector.collect=collect
            self.assertEqual(self.execute_fixture(job)['state'],'limit_reached')
            self.mono=0

    def test_cancelled_work_never_becomes_completed(self):
        self.enable();cancel=threading.Event();cancel.set()
        self.assertEqual(self.runner.execute(self.job,cancel)['state'],'cancelled');self.assertEqual(self.connector.collects,0)

    def test_draft_only_never_sends_a_link(self):
        self.enable();self.connector.requests=(request(),)
        self.assertEqual(self.execute_fixture()['state'],'completed');self.assertEqual(self.connector.sent,[])

    def test_exact_approved_link_replies_once_across_jobs(self):
        job=replace(self.job,send_mode='approved_catalog');self.enable(job);self.connector.requests=(request(),)
        self.assertEqual(self.execute_fixture(job)['state'],'completed');self.assertEqual(len(self.connector.sent),1)
        other=replace(job,id='duplicate_job');self.enable(other)
        self.assertEqual(self.execute_fixture(other)['state'],'completed');self.assertEqual(len(self.connector.sent),1)
        self.assertEqual(self.connector.sent[0][1],'https://example.invalid/video')

    def test_invented_recipient_account_or_resource_never_sends(self):
        for index,values in enumerate(({'target':'d'*64},{'account':'other_account'},{'resource':'invented_link'})):
            job=replace(self.job,id='target_'+str(index),send_mode='approved_catalog');self.enable(job)
            self.connector.requests=(request(**values),)
            self.assertEqual(self.execute_fixture(job)['state'],'blocked')
        self.assertEqual(self.connector.sent,[])

    def test_uncertain_send_is_quarantined_and_not_retried(self):
        job=replace(self.job,send_mode='approved_catalog');self.enable(job);self.connector.requests=(request(),)
        attempts=[]
        def send(*args):attempts.append(1);raise TimeoutError('PRIVATE_PROVIDER_CANARY')
        self.connector.send_approved_link=send
        self.assertEqual(self.execute_fixture(job)['state'],'needs_review')
        self.assertEqual(self.execute_fixture(job)['state'],'needs_review')
        other=replace(job,id='other_job');self.enable(other)
        self.assertEqual(self.execute_fixture(other)['state'],'needs_review');self.assertEqual(len(attempts),1)
        self.assertNotIn(b'PRIVATE_PROVIDER_CANARY',self.path.read_bytes())

    def test_changed_payload_for_already_sent_item_requires_review(self):
        job=replace(self.job,send_mode='approved_catalog');self.enable(job);self.connector.requests=(request(),);self.execute_fixture(job)
        other=replace(job,id='changed_payload',catalog=(('video_link','https://example.invalid/other'),));self.enable(other)
        self.assertEqual(self.execute_fixture(other)['state'],'needs_review');self.assertEqual(len(self.connector.sent),1)

    def test_receipt_survives_revocation_during_send_but_run_cannot_complete(self):
        job=replace(self.job,send_mode='approved_catalog');self.enable(job);self.connector.requests=(request(),)
        def send(*args):self.store.revoke(job,self.proof);return 'c'*64
        self.connector.send_approved_link=send
        self.assertEqual(self.execute_fixture(job)['state'],'blocked')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT state FROM actions').fetchone()[0],'sent')

    def test_commit_checks_revocation_atomically_after_report_write(self):
        self.enable();old=self.reports.write
        def write(*args):
            reference=old(*args);self.store.revoke(self.job,self.proof);return reference
        self.reports.write=write
        self.assertEqual(self.execute_fixture()['state'],'blocked')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)

    def test_exception_details_do_not_leak_private_messages_into_ledger(self):
        self.enable()
        def collect(*args):raise PermissionError('VERY_PRIVATE_MESSAGE_BODY')
        self.connector.collect=collect
        self.assertEqual(self.execute_fixture()['reason'],'permission_denied')
        self.assertNotIn(b'VERY_PRIVATE_MESSAGE_BODY',self.path.read_bytes())

    def test_important_filter_and_uncertainty_are_explicit(self):
        for index,(mode,important,uncertain,expected) in enumerate((('important_only',0,0,0),('important_or_uncertain',0,1,1),('important_only',0,1,0),('always',0,0,1))):
            job=replace(self.job,id='filter_'+str(index),notification_filter=mode);self.enable(job)
            self.connector.important,self.connector.uncertain=important,uncertain
            run=self.execute_fixture(job)
            with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox WHERE run=?',(run['id'],)).fetchone()[0],expected)

    def test_partial_collection_is_labelled_partial_and_queues_a_report(self):
        self.enable();self.connector.partial=True;self.connector.important=0
        self.assertEqual(self.execute_fixture()['state'],'partial')
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],1)

    def test_notification_waits_until_seven_and_requests_once(self):
        self.enable();run=self.execute_fixture();notifier=Mock();notifier.zero_spend=True;notifier.preflight.return_value=True;notifier.notify_owner.return_value='d'*64
        self.assertFalse(self.runner.notify(self.job,run['id'],notifier));notifier.notify_owner.assert_not_called()
        self.now=NOTIFY
        self.assertTrue(self.runner.notify(self.job,run['id'],notifier));self.assertFalse(self.runner.notify(self.job,run['id'],notifier))
        self.assertEqual(notifier.notify_owner.call_args.args[0],'owner_fake')

    def test_notification_wrong_contract_expired_report_or_revoked_grant_never_sends(self):
        self.enable();run=self.execute_fixture();self.now=NOTIFY;notifier=Mock();notifier.zero_spend=True;notifier.preflight.return_value=True
        with self.assertRaises(PermissionError):self.runner.notify(replace(self.job,owner='other_owner'),run['id'],notifier)
        self.store.revoke(self.job,self.proof)
        self.assertFalse(self.runner.notify(self.job,run['id'],notifier));notifier.notify_owner.assert_not_called()

    def test_unknown_push_outcome_is_not_blindly_retried(self):
        self.enable();run=self.execute_fixture();self.now=NOTIFY;notifier=Mock();notifier.zero_spend=True;notifier.preflight.return_value=True
        notifier.notify_owner.side_effect=TimeoutError('offline')
        self.assertFalse(self.runner.notify(self.job,run['id'],notifier));self.assertFalse(self.runner.notify(self.job,run['id'],notifier))
        self.assertEqual(notifier.notify_owner.call_count,1)

    def test_keep_later_and_dismiss_are_owner_scoped_metadata_decisions(self):
        self.enable();run=self.execute_fixture()
        with self.assertRaises(PermissionError):self.store.inbox_decision(self.job,run['id'],'dismiss','no proof',self.now)
        self.store.inbox_decision(self.job,run['id'],'later',self.proof,self.now,until=NOTIFY+3600)
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT due FROM outbox').fetchone()[0],NOTIFY+3600)
        self.store.inbox_decision(self.job,run['id'],'keep',self.proof,self.now)
        self.store.inbox_decision(self.job,run['id'],'dismiss',self.proof,self.now)
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT state FROM outbox').fetchone()[0],'dismissed')
        with self.assertRaises(ValueError):self.store.inbox_decision(self.job,run['id'],'later',self.proof,self.now,until=self.now+25*3600)

    def test_recovery_fences_old_worker_and_never_replays_inflight_run(self):
        self.enable();slot=due_slot(self.job,self.now);epoch=self.store.claim(self.job,slot,self.now)
        self.store.recover(self.job,slot['id'],self.proof)
        self.assertFalse(self.store.active(self.job.id,self.job.digest(),epoch,self.now))
        self.assertEqual(self.store.view(slot['id'])['state'],'needs_review')
        with self.assertRaises(PermissionError):self.execute_fixture()

    def test_expiring_and_owner_changing_grants_are_refused(self):
        with self.assertRaises(ValueError):self.store.enable(self.job,self.proof,self.now,self.now+31*86400)
        self.enable()
        with self.assertRaises(ValueError):self.enable()
        other=replace(self.job,owner='another_owner',revision=2)
        self.store.verify_owner=lambda *args:True
        with self.assertRaises(PermissionError):self.enable(other)

    def test_collection_window_ends_at_scheduled_time_not_notification_time(self):
        self.enable();seen=[];original=self.connector.collect
        def collect(job,ctx):
            seen.append((ctx.window_start,ctx.window_end));return original(job,ctx)
        self.connector.collect=collect;self.execute_fixture()
        self.assertEqual(seen,[(START-86400,START)])

    def test_expired_report_and_unestablished_paid_notifications_never_send(self):
        self.enable();run=self.execute_fixture();notifier=Mock();notifier.preflight.return_value=True
        self.now=NOTIFY;self.assertFalse(self.runner.notify(self.job,run['id'],notifier))
        notifier.zero_spend=True;self.now=START+25*3600
        self.assertFalse(self.runner.notify(self.job,run['id'],notifier));notifier.notify_owner.assert_not_called()

    def test_forged_slot_and_mismatched_revocation_are_refused(self):
        self.enable();slot=due_slot(self.job,self.now)
        with self.assertRaises(ValueError):self.store.claim(self.job,{**slot,'id':'f'*64},self.now)
        with self.assertRaises(PermissionError):self.store.revoke(replace(self.job,notify='20:00'),self.proof)

    def test_public_sink_refuses_private_reports(self):
        sink=PublicReports(self.path.with_name('public.sqlite'))
        self.assertFalse(sink.supports(self.job))
        with self.assertRaises(PermissionError):sink.write(self.job,'a'*64,b'PRIVATE',self.now+100)
        self.assertFalse(sink.path.exists())

    def test_public_report_expiry_read_and_purge_are_enforced(self):
        public=Job('public_fixture',1,'technology_updates','oracle','public','18:00','19:00',owner='owner_fake')
        sink=PublicReports(self.path.with_name('public.sqlite'))
        reference=sink.write(public,'a'*64,b'PUBLIC_FIXTURE',self.now+3600)
        self.assertEqual(sink.read(reference,self.now),b'PUBLIC_FIXTURE')
        with self.assertRaises(LookupError):sink.read(reference,self.now+3601)
        self.assertEqual(sink.purge(self.now+3601),1)

    def test_public_report_sink_refuses_an_unrelated_existing_database(self):
        with sqlite3.connect(self.path) as db:db.execute('CREATE TABLE other_data(value TEXT)')
        public=Job('public_fixture',1,'technology_updates','oracle','public','18:00','19:00',owner='owner_fake')
        with self.assertRaises(ValueError):PublicReports(self.path).write(public,'a'*64,b'public',self.now+100)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('other_data',)])

    def test_public_news_adapter_runs_under_same_daily_contract_without_models(self):
        job=Job('news_fixture',1,'technology_updates','oracle','public','18:00','19:00',owner='owner_fake')
        self.enable(job)
        def fetch(source,**kw):
            kw['reserve']();return [{'title':'Introducing a new coding model','preview':'A model preview.', 'published_at':'2026-10-16T12:00:00Z','url':source.url}],0
        adapter=TechnologyUpdates(fetch)
        runner=Runner(self.store,placement='oracle',adapters={'technology_updates':adapter},reports=PublicReports(self.path.with_name('public.sqlite')),clock=lambda:self.now,monotonic=lambda:0)
        result=runner.execute(job)
        self.assertEqual(result['state'],'completed');self.assertEqual(result['uncertain'],3)


if __name__=='__main__':unittest.main()
