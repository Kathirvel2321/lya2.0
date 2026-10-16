"""Run an entirely synthetic 18:00 collection / 19:00 owner-report example.

No network, real accounts, system timer, notifications, enrollment or private store.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cloud.job_policy import Job, Limits
from cloud.job_store import JobStore
from cloud.job_runner import Runner, Result, LinkRequest


def main():
    now=[1792153800.0]  # Replaced below by an explicit timezone-bearing fixture.
    from datetime import datetime
    now[0]=datetime.fromisoformat('2026-10-16T12:30:00+00:00').timestamp()
    job=Job('synthetic_inbox',1,'inbox_review','oracle','private','18:00','19:00',
        account='account_fake',owner='owner_fake',private_remote=True,
        importance_rules=('fake_owner_rule',),send_mode='approved_catalog',
        catalog=(('video_link','https://example.invalid/video'),),limits=Limits(sends=1))
    class RAMReports:
        def __init__(self):self.contents={}
        def supports(self,job):return True  # Test-only RAM sink, not production private storage.
        def write(self,job,run,body,expires):
            key=hashlib.sha256(body+run.encode()).hexdigest();self.contents[key]=body;return key
    class FakeAccount:
        zero_spend=True
        def __init__(self):self.replies=[];self.notifications=[]
        def preflight(self,job):return job.account=='account_fake'
        def collect(self,job,ctx):
            ctx.request();ctx.item()
            return Result(b'SYNTHETIC_PRIVATE_REPORT',important=1,
                replies=(LinkRequest('a'*64,job.account,'b'*64,'video_link'),))
        def validate_inbound(self,job,item):return item.target=='b'*64
        def send_approved_link(self,job,item,url,ctx):
            self.replies.append((item.target,url));return 'c'*64
        def notify_owner(self,owner,report,run,timeout=10):
            self.notifications.append((owner,report));return 'd'*64
    with tempfile.TemporaryDirectory(prefix='lya-job-policy-lab-') as folder:
        account=FakeAccount();reports=RAMReports()
        proof='FAKE_OWNER_PROOF_ONLY_FOR_THIS_LAB'
        store=JobStore(Path(folder)/'control.sqlite',
            lambda operation,proposal,supplied:supplied==proof and proposal.digest()==job.digest())
        store.enable(job,proof,now[0],now[0]+86400)
        runner=Runner(store,placement='oracle',adapters={'inbox_review':account},reports=reports,
            clock=lambda:now[0],monotonic=lambda:0)
        result=runner.execute(job)
        before_seven=runner.notify(job,result['id'],account)
        now[0]+=3600
        at_seven=runner.notify(job,result['id'],account)
        repeated=runner.notify(job,result['id'],account)
        private_in_control=b'SYNTHETIC_PRIVATE_REPORT' in store.path.read_bytes()
        output={'data':'synthetic_only','network_calls':0,'real_messages_sent':0,
            'collection_state':result['state'],'mock_link_replies':len(account.replies),
            'notification_before_19_00':before_seven,'mock_notification_at_19_00':at_seven,
            'repeated_notification':repeated,'private_report_in_plain_control_store':private_in_control,
            'real_account_connection':'not_configured','production_deployment':'not_run'}
        assert result['state']=='completed' and not before_seven and at_seven and not repeated and not private_in_control
        print(json.dumps(output,indent=2))


if __name__=='__main__':main()
