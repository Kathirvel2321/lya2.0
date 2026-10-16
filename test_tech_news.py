"""Official-source fixtures, disposable public caches and actual offscreen Qt only."""
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
from cloud.news_sources import (SOURCES, Source, announcement, parse_source,
    OfficialNewsFetcher, MAX_BYTES)
from cloud.tech_news import NewsStore, NewsMonitor, render_brief, relevance, INTERVAL
from desktop.news import NewsController, quiet

NOW = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc).timestamp()
OPENAI, GEMINI, ANTHROPIC = SOURCES


def item(source=OPENAI, **changes):
    row = announcement(source, 'Introducing Fixture GPT 7 coding model',
        'https://openai.com/index/fixture-model', '2026-10-16T09:00:00Z',
        'A coding assistant is announced; availability is limited to a preview.')
    row.update(changes)
    return row


def rss(title='Introducing Fixture GPT 7', link='https://openai.com/index/fixture-model', date='Fri, 16 Oct 2026 09:00:00 GMT'):
    return f'<rss version="2.0"><channel><item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate><description><![CDATA[<p>A new coding model; preview access only.</p>]]></description></item></channel></rss>'.encode()


class ParsingChecks(unittest.TestCase):
    def test_rss_dates_preview_and_official_origin(self):
        values, rejected = parse_source(rss(), OPENAI)
        self.assertEqual(rejected, 0); self.assertEqual(values[0]['published_at'], '2026-10-16T09:00:00Z')
        self.assertEqual(values[0]['preview'], 'A new coding model; preview access only.')
        self.assertEqual(parse_source(rss(), OPENAI)[0][0]['id'], values[0]['id'])

    def test_missing_date_and_off_publisher_links_cannot_be_announcements(self):
        for raw in (rss(date=''), rss(link='https://fake.invalid/news'), rss(link='https://127.0.0.1/news'),rss(date='Fri, 16 Oct 2026 09:00:00')):
            with self.subTest(raw=raw), self.assertRaises(ValueError):parse_source(raw,OPENAI)

    def test_atom_uses_published_not_updated_as_launch_date(self):
        body=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New coding model</title><link href="https://openai.com/index/new"/><published>2026-10-15T20:00:00Z</published><updated>2026-10-16T09:00:00Z</updated></entry></feed>'
        self.assertEqual(parse_source(body,OPENAI)[0][0]['published_at'],'2026-10-15T20:00:00Z')
        with self.assertRaises(ValueError):parse_source(body.replace(b'<published>2026-10-15T20:00:00Z</published>',b''),OPENAI)

    def test_xml_entities_depth_bytes_and_bad_encoding_are_rejected(self):
        bodies=[b'<!DOCTYPE rss [<!ENTITY bomb "boom">]><rss/>', b'<rss>'+b'<a>'*40+b'x'+b'</a>'*40+b'</rss>',b'x'*(MAX_BYTES+1),'<rss/>'.encode('utf-16')]
        for body in bodies:
            with self.subTest(size=len(body)),self.assertRaises((ValueError,UnicodeError)):
                parse_source(body,OPENAI)

    def test_gemini_preserves_date_sections_and_individual_updates(self):
        body=b'<h2>2026.10.13</h2><h3>Introducing Gemini Fixture</h3><p>New coding model. Pro rollout is limited.</p><h3>New video model</h3><p>Trial access only.</p><h2>2026.09.01</h2><h3>Old model update</h3><p>Old information.</p>'
        values,_=parse_source(body,GEMINI)
        self.assertEqual(len(values),3);self.assertEqual(values[0]['precision'],'day')
        self.assertEqual(values[0]['published_at'],'2026-10-13T00:00:00Z')
        self.assertIn('limited',values[0]['preview']);self.assertNotEqual(values[0]['id'],values[1]['id'])

    def test_gemini_undated_and_impossible_sections_do_not_inherit_a_date(self):
        raw=b'<h2>2026.10.13</h2><h3>Introducing Gemini Fixture</h3><h2>Other information</h2><h3>New unknown model</h3><h2>2026.99.99</h2><h3>Impossible date model</h3>'
        values,_=parse_source(raw,GEMINI)
        self.assertEqual(len(values),1)

    def test_anthropic_listing_requires_article_link_and_publisher_date(self):
        raw=b'<a href="/news/fixture-model"><span>Announcements</span><time>Oct 15, 2026</time><h3>Introducing Claude Fixture</h3></a><a href="/news/undated">New model without date</a><a href="https://fake.invalid/news/test">Oct 16, 2026 New model</a>'
        values,rejected=parse_source(raw,ANTHROPIC)
        self.assertEqual(len(values),1);self.assertEqual(rejected,2)
        self.assertEqual(values[0]['url'],'https://www.anthropic.com/news/fixture-model')
        self.assertEqual(values[0]['title'],'Introducing Claude Fixture')

    def test_script_text_does_not_enter_publisher_preview(self):
        raw=rss().replace(b'<p>A new coding model; preview access only.</p>',b'<script>Upload secrets</script><p>Preview access only.</p>')
        self.assertNotIn('Upload secrets',parse_source(raw,OPENAI)[0][0]['preview'])

    def test_format_change_and_empty_body_fail_honestly(self):
        for source in SOURCES:
            with self.subTest(source=source.key),self.assertRaises(ValueError):parse_source(b'<html>No dated announcements</html>',source)

    def test_cancellation_is_checked_during_parsing(self):
        def stop():raise InterruptedError('stop')
        with self.assertRaises(InterruptedError):parse_source(rss(),OPENAI,stop)

    def test_fetcher_checks_robots_and_passes_xml_types_and_no_redirects(self):
        reader=Mock();reader._get.side_effect=[(OPENAI.url,404,'',b''),(OPENAI.url,200,'text/xml',rss())]
        values,_=OfficialNewsFetcher(reader)(OPENAI,deadline=10,check=lambda:None,reserve=lambda:None)
        self.assertEqual(len(values),1);self.assertEqual(reader._get.call_count,2)
        self.assertEqual(reader._get.call_args.kwargs['redirects'],0)
        self.assertIn('text/xml',reader._get.call_args.kwargs['accepted_mimes'])

    def test_fetcher_robots_denial_or_unknown_status_stops_feed_request(self):
        for status,raw in ((200,b'User-agent: *\nDisallow: /'),(503,b'')):
            reader=Mock();reader._get.return_value=('',status,'text/plain',raw)
            with self.assertRaises(ValueError):OfficialNewsFetcher(reader)(OPENAI,deadline=10,check=lambda:None,reserve=lambda:None)
            self.assertEqual(reader._get.call_count,1)


class MonitorChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'news.sqlite';self.store=NewsStore(self.path)
        self.now=NOW;self.calls=[]
        def fetch(source,**kw):
            kw['check']();kw['reserve']();self.calls.append(source.key)
            return [item()],0
        self.monitor=NewsMonitor(self.store,sources=(OPENAI,),fetch=fetch,clock=lambda:self.now,monotonic=lambda:0)

    def snapshot(self):return self.store.snapshot(self.now)

    def test_first_check_catches_recent_news_and_restart_does_not_repeat(self):
        self.assertTrue(self.monitor.check());self.assertEqual(self.snapshot()['unread'],1)
        self.assertFalse(self.monitor.check());self.assertEqual(self.calls,['openai'])
        second=NewsMonitor(NewsStore(self.path),sources=(),clock=lambda:self.now)
        self.assertFalse(second.check())
        self.now+=INTERVAL;self.assertTrue(self.monitor.check())
        self.assertEqual(len(self.snapshot()['items']),1)

    def test_four_day_old_launch_is_in_opening_catchup(self):
        self.monitor.fetch=lambda *a,**kw:([item(published_at='2026-10-12T09:00:00Z')],0)
        self.monitor.check();self.assertEqual(self.snapshot()['unread'],1)

    def test_old_future_and_undated_items_do_not_become_fresh_launches(self):
        self.monitor.fetch=lambda *a,**kw:([item(published_at='2026-09-01T00:00:00Z'),item(published_at='2026-10-17T00:00:00Z')],0)
        self.monitor.check();self.assertEqual(self.snapshot()['items'],[])

    def test_clock_rollback_does_not_trigger_flood(self):
        self.monitor.check();self.now-=86400
        self.assertFalse(self.monitor.check());self.assertEqual(len(self.calls),1)

    def test_concurrent_reservation_allows_one_network_round(self):
        from concurrent.futures import ThreadPoolExecutor
        def reserve(_):return NewsStore(self.path).reserve(NOW)
        with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(reserve,range(12)))
        self.assertEqual(sum(results),1)

    def test_failures_keep_old_cache_and_report_incomplete_coverage(self):
        self.monitor.check();self.now+=INTERVAL
        def fail(*a,**kw):raise OSError('fixture offline')
        self.monitor.fetch=fail;self.monitor.check()
        snapshot=self.snapshot();self.assertEqual(len(snapshot['items']),1)
        self.assertIn('unavailable',snapshot['coverage'][0]['status'])
        self.assertFalse(self.monitor.check())

    def test_partial_sources_never_claim_all_were_checked(self):
        self.monitor.sources=(OPENAI,GEMINI)
        def fetch(source,**kw):
            if source==GEMINI:raise ValueError('changed')
            return [item()],0
        self.monitor.fetch=fetch;self.monitor.check()
        status=[value['status'] for value in self.snapshot()['coverage']]
        self.assertEqual(status,['read','unavailable or format changed'])

    def test_cancelled_round_never_commits_discovered_news(self):
        cancelled=threading.Event()
        def fetch(*a,**kw):cancelled.set();return [item()],0
        self.monitor.fetch=fetch
        with self.assertRaises(InterruptedError):self.monitor.check(cancelled)
        self.assertEqual(self.snapshot()['items'],[])
        self.assertIsNotNone(self.snapshot()['last_attempt'])

    def test_paused_setting_persists_and_blocks_fetch(self):
        self.store.set_enabled(False);self.assertFalse(self.monitor.check())
        self.assertEqual(self.calls,[]);self.assertFalse(NewsStore(self.path).enabled())
        self.store.set_enabled(True);self.assertTrue(self.monitor.check())

    def test_pause_mid_round_rolls_back_new_results(self):
        def fetch(*a,**kw):self.store.set_enabled(False);return [item()],0
        self.monitor.fetch=fetch
        with self.assertRaises(InterruptedError):self.monitor.check()
        self.assertEqual(self.snapshot()['items'],[])

    def test_http_and_time_budgets_stop_more_work(self):
        now=[0]
        def fetch(*a,**kw):
            for _ in range(7):kw['reserve']()
            return [item()],0
        self.monitor.fetch=fetch;self.monitor.check()
        self.assertEqual(self.snapshot()['items'],[])
        self.now+=INTERVAL
        self.monitor.monotonic=lambda:next(values)
        values=iter([0,21])
        self.monitor.check();self.assertEqual(self.snapshot()['coverage'][0]['status'],'time budget reached')

    def test_mark_seen_and_notification_requested_are_distinct_and_durable(self):
        self.monitor.check();key=self.snapshot()['items'][0]['id']
        self.store.mark([key],self.now,notified=True)
        self.assertEqual(self.snapshot()['unread'],1)
        self.assertTrue(self.snapshot()['items'][0]['notification_requested'])
        NewsStore(self.path).mark([key],self.now)
        self.assertEqual(self.snapshot()['unread'],0)

    def test_changed_headline_does_not_repeat_same_article_url(self):
        self.monitor.check();key=self.snapshot()['items'][0]['id'];self.store.mark([key],self.now)
        self.now+=INTERVAL
        self.monitor.fetch=lambda *a,**kw:([item(title='Updated Fixture GPT 7 announcement')],0)
        self.monitor.check();self.assertEqual(self.snapshot()['unread'],0)

    def test_cache_schema_links_and_corruption_fail_without_deleting(self):
        self.path.write_bytes(b'not sqlite')
        with self.assertRaises(sqlite3.DatabaseError):self.store.snapshot(self.now)
        self.assertEqual(self.path.read_bytes(),b'not sqlite')
        link=self.path.with_name('link.sqlite');link.symlink_to(self.path)
        with self.assertRaises(ValueError):NewsStore(link).enabled()

    def test_unrelated_or_future_schema_is_not_migrated(self):
        with sqlite3.connect(self.path) as db:db.execute('CREATE TABLE private_fixture(value TEXT)')
        with self.assertRaises(ValueError):self.store.enabled()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('private_fixture',)])

    def test_storage_and_lookback_are_bounded(self):
        values=[item(id=f'{i:064x}',url=f'https://openai.com/index/{i}') for i in range(300)]
        for chunk in (values[:150],values[150:]):self.store.finish(chunk,[],self.now)
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM items').fetchone()[0],256)
        self.assertLessEqual(len(self.snapshot()['items']),12)
        self.now+=8*86400;self.assertEqual(self.snapshot()['items'],[])

    def test_rendering_discloses_dates_preview_and_unknown_access(self):
        self.monitor.check();text=render_brief(self.snapshot())
        self.assertIn('2026-10-16T09:00:00Z',text)
        self.assertIn('Publisher preview',text);self.assertIn('not been independently checked',text)
        self.assertNotIn('best model',text.lower());self.assertIn('https://openai.com/index/fixture-model',text)

    def test_empty_cache_does_not_claim_no_launch_exists(self):
        text=render_brief(self.snapshot())
        self.assertIn('does not establish that nothing new',text)
        self.assertIn('No source check has completed',text)

    def test_company_administration_is_not_a_tool_launch(self):
        self.assertEqual(relevance(item(title='Anthropic opens a new Singapore office',preview='Office opening.')),[])
        self.assertEqual(relevance(item(title='How a retailer uses an AI model',preview='Existing customer story.')),[])


class QtNewsChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=NewsStore(Path(temp.name)/'news.sqlite')
        NewsMonitor(self.store,sources=(OPENAI,),fetch=lambda *a,**kw:([item()],0),clock=lambda:NOW,monotonic=lambda:0).check()
        self.allowed=True;self.owner=QObject();self.owner.app=self.app;self.owner.tray=Mock()
        self.monitor=Mock();self.clock=[0]
        self.controller=NewsController(self.owner,store=self.store,monitor=self.monitor,clock=lambda:NOW,
            monotonic=lambda:self.clock[0],can_present=lambda:self.allowed,tray_available=lambda:True,autostart=False)
        self.controller.snapshot=self.store.snapshot(NOW)
        self.addCleanup(self.controller.shutdown)
        self.addCleanup(self.app.processEvents)

    def test_opening_catchup_is_real_qt_plain_text_and_marks_seen(self):
        self.controller.present()
        dialog=self.controller.dialog
        self.assertTrue(dialog.isVisible());self.assertIn('Fixture GPT',dialog.body.toPlainText())
        self.assertEqual(self.store.snapshot(NOW)['unread'],0)
        self.assertFalse(dialog.body.openExternalLinks());self.assertFalse(dialog.body.openLinks())
        self.owner.tray.showMessage.assert_not_called()

    def test_background_toast_is_requested_once_without_marking_seen(self):
        self.controller.want_brief=False;self.controller.present();self.controller.present()
        self.owner.tray.showMessage.assert_called_once()
        self.assertEqual(self.store.snapshot(NOW)['unread'],1)
        self.assertTrue(self.store.snapshot(NOW)['items'][0]['notification_requested'])
        self.assertIsNone(self.controller.dialog)

    def test_unsupported_notifications_leave_unread_for_in_app_view(self):
        self.controller.want_brief=False;self.controller.tray_available=lambda:False
        self.controller.present();self.owner.tray.showMessage.assert_not_called()
        self.assertFalse(self.store.snapshot(NOW)['items'][0]['notification_requested'])
        self.controller.show_brief();self.assertTrue(self.controller.dialog.isVisible())

    def test_private_busy_and_sleep_suppress_automatic_delivery(self):
        self.allowed=False;self.controller.present();self.controller.tick()
        self.assertIsNone(self.controller.dialog);self.monitor.check.assert_not_called()
        self.controller.suspend();self.allowed=True;self.controller.present()
        self.assertIsNone(self.controller.dialog);self.owner.tray.showMessage.assert_not_called()

    def test_paused_or_env_disabled_does_not_request_alerts(self):
        self.controller.snapshot['enabled']=False;self.controller.present();self.controller.tick()
        self.assertIsNone(self.controller.dialog);self.monitor.check.assert_not_called()
        self.controller.snapshot['enabled']=True;self.controller.disabled=True
        self.controller.present();self.controller.tick();self.monitor.check.assert_not_called()

    def test_late_worker_signal_is_rejected_after_interruption_or_shutdown(self):
        generation=self.controller.generation
        self.controller.interrupt()
        self.controller.cancelled=threading.Event()
        self.controller.on_ready(generation,self.store.snapshot(NOW),'')
        self.assertIsNone(self.controller.dialog)
        self.controller.shutdown()
        self.controller.on_ready(self.controller.generation,self.store.snapshot(NOW),'')
        self.assertIsNone(self.controller.dialog)

    def test_reopening_and_timer_ticks_do_not_bypass_hourly_worker_limit(self):
        self.controller.want_brief=False
        self.controller.tick();self.controller.worker.join(2);self.app.processEvents()
        self.controller.tick(requested=True);self.controller.tick(requested=True)
        self.assertEqual(self.monitor.check.call_count,1)
        self.clock[0]+=INTERVAL
        self.controller.tick();self.controller.worker.join(2);self.app.processEvents()
        self.assertEqual(self.monitor.check.call_count,2)

    def test_one_worker_can_run_and_shutdown_does_not_wait_for_it(self):
        entered=threading.Event();release=threading.Event()
        def check(cancelled):entered.set();release.wait(2)
        self.monitor.check.side_effect=check;self.controller.want_brief=False
        self.controller.tick();self.assertTrue(entered.wait(1));self.controller.tick()
        self.assertEqual(self.monitor.check.call_count,1)
        start=time.monotonic();self.controller.shutdown()
        self.assertLess(time.monotonic()-start,.2)
        release.set();self.controller.worker.join(2);self.app.processEvents()

    def test_manual_view_can_show_cached_items_while_background_is_private(self):
        self.controller.snapshot['items']=[];self.allowed=False
        self.controller.show_brief()
        self.assertIn('Fixture GPT',self.controller.dialog.body.toPlainText())
        self.monitor.check.assert_not_called()

    def test_delivery_policy_blocks_speech_camera_setup_and_private_mode(self):
        owner=SimpleNamespace(brain_busy=False,brain=SimpleNamespace(private_mode=False))
        self.assertTrue(quiet(owner))
        for name,value in [('brain_busy',True),('listener_phase','speaking'),('first_run_setup',True),('quitting',True)]:
            setattr(owner,name,value);self.assertFalse(quiet(owner))
            if name=='brain_busy':owner.brain_busy=False
            else:delattr(owner,name)
        owner.brain_busy=False;owner.brain.private_mode=True;self.assertFalse(quiet(owner))
        owner.brain.private_mode=False;owner.speech=SimpleNamespace(busy=True);self.assertFalse(quiet(owner))

    def test_desktop_hooks_preserve_original_launch_art_and_voice_entry_points(self):
        root=Path(__file__).parent
        app=ast.parse((root/'desktop/app.py').read_text());experience=ast.parse((root/'desktop/experience.py').read_text())
        desktop=next(n for n in app.body if isinstance(n,ast.ClassDef) and n.name=='Desktop')
        methods={n.name:ast.unparse(n) for n in desktop.body if isinstance(n,ast.FunctionDef)}
        self.assertIn('NewsController(self)',methods['__init__'])
        self.assertIn('self.news.suspend()',methods['sleep']);self.assertIn('self.news.shutdown()',methods['quit'])
        self.assertIn('self.news.interrupt()',methods['command']);self.assertIn('technology updates',methods['command'])
        self.assertIn('self.news.opened()',methods['open_panel'])
        # Execute the actual command body with a synthetic owner, without booting Desktop.
        command_node=next(n for n in desktop.body if isinstance(n,ast.FunctionDef) and n.name=='command')
        namespace={}
        exec(compile(ast.Module(body=[command_node],type_ignores=[]),'desktop-command-fixture','exec'),namespace)
        fake=SimpleNamespace(news=Mock(),brain_busy=False,generation=0,show_technology_updates=Mock())
        for text in ('Technology updates?', 'Any news about technology updates?', 'Latest AI news!'):
            namespace['command'](fake,text)
        self.assertEqual(fake.show_technology_updates.call_count,3)
        self.assertEqual(fake.news.interrupt.call_count,3)
        orb=next(n for n in experience.body if isinstance(n,ast.ClassDef) and n.name=='OrbDesktop')
        wake=next(n for n in orb.body if isinstance(n,ast.FunctionDef) and n.name=='wake')
        self.assertIn('self.news.opened()',ast.unparse(wake))
        main=next(n for n in app.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        artwork=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='set_artwork']
        self.assertEqual(ast.unparse(artwork[0].args[0]),'args.model_art and (not args.original_art)')


if __name__=='__main__':unittest.main()
