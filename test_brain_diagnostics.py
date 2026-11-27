"""Synthetic provider and website capability checks without live calls."""
import errno
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from brain.oracle import OracleModel
from brain.workflow import Brain, LocalModel
from cloud.inference import infer


class BrainDiagnosticsChecks(unittest.TestCase):
    def bridge(self, packet, researcher=None):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps(packet)))
        model = OracleModel({'host':'192.0.2.1', 'key_file':'synthetic.key'},runner)
        return Brain(client=model, researcher=researcher), runner

    def test_rejected_credential_is_explained_without_inventing_expiry(self):
        brain, runner = self.bridge({'error':'provider_http_401',
            'attempts':[{'status':'provider_http_401','route':'FAKE_SECRET'}], 'detail':'FAKE_SECRET'})
        with patch.object(Path,'is_file',return_value=True):
            first = brain.respond('Hello')
            follow_up = brain.respond('What happened?')
        self.assertEqual(follow_up.route,'diagnostic')
        self.assertTrue(follow_up.text.startswith(first.text))
        self.assertIn('Want me to research',follow_up.text)
        self.assertIn('rejected',follow_up.text)
        self.assertIn('does not identify why',follow_up.text)
        self.assertIn('No provider fallback was attempted',follow_up.text)
        self.assertNotIn('FAKE_SECRET',follow_up.text)
        runner.assert_called_once()
        brain.clear_temporary()
        self.assertIn('no recorded problem',brain.respond('What happened?').text)

    def test_timeout_and_successful_fallback_are_distinguished(self):
        packet={'messages':[{'role':'user','content':'Fixture'}]}
        config={'provider':'groq','api_key':'FAKE_KEY','model':'fixture'}
        for error in (TimeoutError(), URLError(TimeoutError())):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(infer(packet,config,Mock(side_effect=error)),{'error':'provider_timeout'})
        brain, runner = self.bridge({'text':'Fallback answer','route':'fallback',
            'attempts':[{'status':'provider_timeout'},{'status':'ok'}]})
        with patch.object(Path,'is_file',return_value=True):
            self.assertEqual(brain.respond('Hello').text,'Fallback answer')
            self.assertIn('approved fallback answered',brain.respond('LYA, what happened?').text)
        runner.assert_called_once()
        local=Brain(client=LocalModel(model='fixture'))
        with patch('urllib.request.build_opener',return_value=Mock(open=Mock(side_effect=TimeoutError('FAKE_SECRET')))):
            self.assertIn('stayed on this computer',local.respond('Hello').text)
            self.assertIn('local model',local.respond('What happened?').text)
        self.assertNotIn('FAKE_SECRET',local.respond('What happened?').text)

    def test_website_task_requires_consent_and_sends_a_public_summary(self):
        finder=Mock(return_value=[])
        model=Mock(return_value='{"claims":[{"text":"The public evidence is insufficient.","kind":"unknown","source_ids":[]}]}')
        brain=Brain(client=lambda messages:model(messages),researcher=lambda *args,**kwargs:finder(*args,**kwargs))
        command='Open https://example.com/account?tag=FAKE_PRIVATE and submit a form for account FAKE_NUMBER'
        offer=brain.respond(command)
        self.assertEqual(offer.route,'website-offer')
        finder.assert_not_called()
        model.assert_not_called()
        self.assertIn('leave',brain.respond('No thanks').text)
        finder.assert_not_called()
        brain.respond(command)
        self.assertEqual(brain.respond('Yes, please').route,'verified-research')
        question=finder.call_args.args[0]
        self.assertIn('example.com',question)
        self.assertIn('submit a form',question)
        self.assertNotIn('FAKE_',question)
        self.assertNotIn('/account',question)
        self.assertNotIn('FAKE_',str(model.call_args))
        self.assertIsNone(brain.pending_research)
        self.assertEqual(brain.respond('Open my browser and do this task').route,'website-scope')
        self.assertEqual(brain.respond('Open https://laptop.example.ts.net and find a page').route,'website-scope')
        self.assertEqual(brain.respond('private: Open example.com and submit a form').route,'blocked')
        finder.assert_called_once()

    def test_internal_exception_reports_a_code_location_without_the_exception_text(self):
        def failing_model(_):
            raise RuntimeError('FAKE_PRIVATE_DETAIL')
        brain=Brain(client=failing_model)
        self.assertEqual(brain.respond('Hello').route,'error')
        diagnostic=brain.respond('What happened?').text
        self.assertRegex(diagnostic, r'brain/workflow\.py:\d+')
        self.assertIn('unconfirmed',diagnostic)
        self.assertNotIn('FAKE_PRIVATE_DETAIL',diagnostic)

    def test_new_runtime_failure_uses_observed_evidence_only_after_consent(self):
        failure = OSError(errno.ENOSPC, 'FAKE_PRIVATE_PATH')
        model = Mock(side_effect=[failure, '{"claims":[{"text":"The source does not establish the cause.","kind":"unknown","source_ids":[]}]}'])
        search = Mock(return_value=[])
        brain = Brain(client=lambda messages:model(messages), researcher=lambda *a,**kw:search(*a,**kw))
        self.assertEqual(brain.respond('FAKE_ORIGINAL_REQUEST').route, 'error')
        explanation = brain.respond('Why did LYA stop working?')
        self.assertIn('OSError ENOSPC', explanation.text)
        self.assertIn('unconfirmed', explanation.text)
        search.assert_not_called()
        self.assertEqual(brain.respond('Yes').route, 'verified-research')
        self.assertIn('OSError ENOSPC', search.call_args.args[0])
        self.assertNotIn('FAKE_', str(search.call_args) + str(model.call_args))
        self.assertNotIn('brain/workflow.py:', search.call_args.args[0])
        self.assertIn('plausible causes', str(model.call_args))
        search.assert_called_once()

    def test_unknown_provider_error_can_return_sources_even_if_model_stays_down(self):
        source = {'id':'source-1', 'url':'https://example.com/docs/status',
                  'retrieved_at':'2026-11-27T00:00:00Z', 'claim':'Example evidence.', 'excerpt':'Example evidence.'}
        researcher = SimpleNamespace(investigate=Mock(return_value=SimpleNamespace(records=[source],
            source_status=[{'id':'source-1', 'kind':'page_excerpt'}], criteria=[])))
        brain, runner = self.bridge({'error':'provider_http_507',
            'attempts':[{'status':'provider_http_507'}], 'detail':'FAKE_PRIVATE_DETAIL'}, researcher)
        with patch.object(Path,'is_file',return_value=True):
            self.assertIn('HTTP 507', brain.respond('Hello').text)
            self.assertIn('Want me to research', brain.respond('What went wrong?').text)
            researcher.investigate.assert_not_called()
            researched = brain.respond('Yes')
        self.assertEqual(researched.route, 'research-evidence')
        self.assertEqual(researched.evidence, [source])
        self.assertIn(source['url'], researched.text)
        self.assertIn('remain unconfirmed', researched.text)
        self.assertIn('HTTP 507', researcher.investigate.call_args.args[0])
        self.assertIsNone(researcher.investigate.call_args.kwargs['planner'])
        self.assertEqual(runner.call_count, 2)

    def test_missing_or_private_failure_does_not_start_public_research(self):
        search = Mock()
        def fail(_):
            raise RuntimeError('FAKE_PRIVATE_DETAIL')

        brain = Brain(client=fail, local_client=fail, researcher=lambda *a,**kw:search(*a,**kw))
        self.assertIn('no recorded problem', brain.respond('What went wrong?').text)
        self.assertEqual(brain.respond('Find a fix').route, 'diagnostic')
        self.assertEqual(brain.respond('private: FAKE_PRIVATE_REQUEST').route, 'error')
        self.assertNotIn('Want me to research', brain.respond('What went wrong?').text)
        self.assertEqual(brain.respond('Find a fix').route, 'diagnostic')
        brain.respond('Public test request')
        self.assertIn('Want me to research', brain.respond('What went wrong?').text)
        brain.clear_temporary()
        self.assertEqual(brain.respond('Find a fix').route, 'diagnostic')
        search.assert_not_called()
