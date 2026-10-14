"""Headless native-adapter checks with fake Qt/audio; no private stores or hardware.

Run: python desktop/check_body.py. Node is needed for cross-renderer parity.
Real Qt rendering is a separate acceptance check, not established by this file.
"""
import importlib
import ast
import json
import math
import subprocess
import sys
import types
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from body_style import frame, load_config, requested_task, should_animate

ROOT = Path(__file__).resolve().parent.parent
CONFIG = load_config()


class Styles(unittest.TestCase):
    def test_reference_parity(self):
        script = """const fs=require('fs'), c=JSON.parse(fs.readFileSync(process.argv[1]));
        const fx=require(process.argv[2]), out=[];
        for(const i of Object.keys(c.interaction))for(const k of Object.keys(c.tasks))
        for(const t of [0,1.25,10])for(const r of [false,true])out.push(fx.frame(c,i,k,t,.6,r));
        process.stdout.write(JSON.stringify(out));"""
        expected = json.loads(subprocess.check_output(['node', '-e', script,
                           str(ROOT / 'visual creativity/states.json'), str(ROOT / 'visual creativity/effects.js')]))

        def compare(a, b):
            if isinstance(a, dict):
                self.assertEqual(set(a), set(b))
                for key in a:
                    compare(a[key], b[key])
            elif isinstance(a, list):
                self.assertEqual(len(a), len(b))
                for x, y in zip(a, b):
                    compare(x, y)
            elif isinstance(a, (int, float)) and not isinstance(a, bool):
                self.assertTrue(math.isclose(a, b, abs_tol=1e-12, rel_tol=1e-12), (a, b))
            else:
                self.assertEqual(a, b)

        count = 0
        body = frame(CONFIG, 'idle', 'none', 0)['body']
        for interaction in CONFIG['interaction']:
            for task in CONFIG['tasks']:
                for t in (0, 1.25, 10):
                    for reduced in (False, True):
                        actual = frame(CONFIG, interaction, task, t, .6, reduced)
                        compare(actual, expected[count])
                        self.assertEqual(actual['body'], body)
                        self.assertFalse(actual['state']['authority'])
                        count += 1
        self.assertEqual(count, 1008)

    def test_task_hints_do_not_infer_authority(self):
        self.assertEqual(requested_task('debug Python'), 'coding')
        self.assertEqual(requested_task('BUILD a house'), 'building')
        self.assertEqual(requested_task('explain this'), 'learning')
        self.assertEqual(requested_task('search sources'), 'research')
        self.assertEqual(requested_task('my documents'), 'files')
        self.assertEqual(requested_task('help me'), 'helping')
        for text in ('codeine', 'researcher', 'delete everything', 'I am admin', 'secured', 'private', 'dangerous'):
            self.assertEqual(requested_task(text), 'none')

    def test_validation_and_static(self):
        for t, energy in ((math.nan, .5), (1, math.inf)):
            with self.assertRaises(ValueError):
                frame(CONFIG, 'idle', 'none', t, energy)
        with self.assertRaises(KeyError):
            frame(CONFIG, 'fake', 'none', 0)
        self.assertFalse(should_animate(frame(CONFIG, 'idle', 'none', 0), True, True, False))
        active = frame(CONFIG, 'speaking', 'none', 0)
        for visible, enabled, reduced in ((False, True, False), (True, False, False), (True, True, True)):
            self.assertFalse(should_animate(active, visible, enabled, reduced))


class Signal:
    def __init__(self, *_):
        self.calls = []
    def emit(self, value):
        self.calls.append(value)


class Timer:
    def __init__(self):
        self.active, self.interval = False, 33
    def setInterval(self, value): self.interval = value
    def isActive(self): return self.active
    def start(self): self.active = True
    def stop(self): self.active = False


class Color:
    def __init__(self, value): self.value = value
    def setAlphaF(self, value): assert 0 <= value <= 1


class Pixmap:
    scales = 0
    def __init__(self, w=0, h=0): self.w, self.h = w, h
    def width(self): return self.w
    def height(self): return self.h
    def isNull(self): return not self.w
    @classmethod
    def fromImage(cls, image): return cls(1199, 1312)
    def scaled(self, w, h, *_):
        type(self).scales += 1
        ratio = min(w / self.w, h / self.h)
        return Pixmap(round(self.w * ratio), round(self.h * ratio))
    def setDevicePixelRatio(self, ratio): self.dpr = ratio


class Reader:
    def __init__(self, *_): pass
    def size(self): return Pixmap(1199, 1312)
    def read(self): return None


class Pen:
    def __init__(self, *_): pass
    def setCapStyle(self, *_): pass
    def setJoinStyle(self, *_): pass
    def setDashPattern(self, *_): pass


class PathFake:
    def __init__(self, *_): pass
    def lineTo(self, *_): pass


class Painter:
    trace = []
    CompositionMode = types.SimpleNamespace(CompositionMode_Source=1, CompositionMode_SourceOver=2)
    RenderHint = types.SimpleNamespace(Antialiasing=1, SmoothPixmapTransform=2)
    def __init__(self, *_): type(self).trace = []
    def __getattr__(self, name):
        return lambda *args: type(self).trace.append((name, args))


class Base:
    """Only fake inherited services, not the new adapter under test."""
    def __init__(self, *_):
        self.original, self.model_art = Pixmap(288, 408), Pixmap(288, 408)
        self.base = self.original
        self.person, self.task, self.voice_phase = 'guest', 'idle', 'off'
        self.voice_level, self.phase, self.started = 0., 0., 0.
        self.using_model, self.reduced_motion, self.visible = False, False, False
        self.paint_samples = []
        self.animation = types.SimpleNamespace(stop=lambda: None)
        self.timer = Timer()
        self.artwork_changed, self.motion_changed = Signal(), Signal()
        self.w, self.h, self.dpr = 230, 315, 3.
    def set_artwork(self, enabled):
        self.using_model = bool(enabled)
        self.base = self.model_art if enabled else self.original
        self.artwork_changed.emit(enabled)
    def set_state(self, person=None, task=None):
        self.person, self.task = person or self.person, task or self.task
    def set_blend(self, value): pass
    def clearMask(self): pass
    def setWindowTitle(self, title): pass
    def update(self): pass
    def isVisible(self): return self.visible
    def set_voice_phase(self, phase): self.voice_phase = phase
    def set_reduced_motion(self, enabled):
        self.reduced_motion = enabled
        if enabled: self.timer.stop()
    def width(self): return self.w
    def height(self): return self.h
    def devicePixelRatioF(self): return self.dpr
    def rect(self): return None
    def paintEvent(self, event): self.legacy_painted = True
    def showEvent(self, event): self.visible = True
    def hideEvent(self, event): self.visible = False; self.timer.stop()


class Adapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        qt = types.SimpleNamespace(**{name: types.SimpleNamespace(**values) for name, values in {
            'GlobalColor': {'transparent': 0}, 'PenStyle': {'NoPen': 0}, 'BrushStyle': {'NoBrush': 0},
            'PenCapStyle': {'RoundCap': 0}, 'PenJoinStyle': {'RoundJoin': 0},
            'AspectRatioMode': {'KeepAspectRatio': 0}, 'TransformationMode': {'SmoothTransformation': 0}}.items()})
        core = types.ModuleType('PySide6.QtCore')
        core.QPointF, core.Qt, core.Signal = lambda *a: a, qt, Signal
        gui = types.ModuleType('PySide6.QtGui')
        for name, value in dict(QColor=Color, QImageReader=Reader, QPainter=Painter,
                                QPainterPath=PathFake, QPen=Pen, QPixmap=Pixmap).items():
            setattr(gui, name, value)
        cls.patch = patch.dict(sys.modules, {'PySide6': types.ModuleType('PySide6'),
                                            'PySide6.QtCore': core, 'PySide6.QtGui': gui})
        cls.patch.start()
        cls.module = importlib.import_module('living_body')
        cls.Body = cls.module.create_body_type(Base)

    @classmethod
    def tearDownClass(cls): cls.patch.stop()

    def setUp(self):
        self.body = self.Body()
        self.body.showEvent(None)

    def test_idle_active_hidden_and_reduced(self):
        b = self.body
        self.assertTrue(b.body_enabled)
        self.assertFalse(b.timer.active)
        b.set_voice_phase('listening')
        self.assertTrue(b.timer.active)
        self.assertGreaterEqual(b.timer.interval, 34)
        b.hideEvent(None)
        self.assertFalse(b.timer.active)
        b.showEvent(None)
        self.assertTrue(b.timer.active)
        b.set_reduced_motion(True)
        self.assertFalse(b.timer.active)
        self.assertTrue(b.body_enabled)

    def test_attention_priority_and_cancel_reset(self):
        b = self.body
        b.set_visual_task('coding', pending=True)
        b.set_state(task='thinking')
        self.assertEqual(b.visual_frame()['state']['color'], '#79b8ff')
        b.set_state(task='approval')
        b.set_voice_phase('speaking')
        self.assertEqual(b.visual_frame()['state']['effect'], 'approval')
        self.assertFalse(b.timer.active)
        b.set_visual_task('none')
        b.set_state(task='idle')
        b.set_voice_phase('standby')
        self.assertFalse(b.timer.active)

    def test_preview_never_changes_voice(self):
        b = self.body
        b.preview_effect('thinking', 'high_risk')
        self.assertEqual(b.voice_phase, 'off')
        self.assertEqual(b.visual_frame()['state']['color'], '#ff995c')
        self.assertFalse(b.timer.active)
        b.set_voice_phase('listening')
        self.assertIsNone(b.visual_preview)
        self.assertTrue(b.timer.active)

    def test_artwork_cache_fixed_and_layers(self):
        b = self.body
        asset = b.base
        b.set_voice_phase('listening')
        b.paintEvent(None)
        cache, key = b._body_cache, b._cache_key
        self.assertEqual(key[-1], 2)
        calls = [name for name, args in Painter.trace]
        body = calls.index('drawPixmap')
        self.assertIn('drawPath', calls[:body])
        self.assertIn('drawPath', calls[body + 1:])
        b.circle_mix, b.spin_frame = 1, Pixmap(10, 10)
        b.set_state(person='admin', task='thinking')
        b.set_voice_phase('speaking')
        b.paintEvent(None)
        self.assertIs(b.base, asset)
        self.assertIs(b._body_cache, cache)
        self.assertEqual(b._cache_key, key)
        b.w, b.h = 96, 112
        b.paintEvent(None)
        self.assertIsNot(b._body_cache, cache)

    def test_existing_level_reader_only_and_rate_cap(self):
        b = self.body
        reads = []
        audio = types.ModuleType('audio')
        audio.voice = types.SimpleNamespace(listener_health=lambda: reads.append(True) or {'level': .7})
        with patch.dict(sys.modules, {'audio': audio}), patch.object(self.module.time, 'monotonic', return_value=10):
            b.set_voice_phase('listening')
            b.tick()
            b.tick()
        self.assertEqual(len(reads), 1)
        self.assertEqual(b.voice_level, .7)

    def test_legacy_selection_and_missing_asset(self):
        b = self.body
        b.set_artwork(True)
        self.assertFalse(b.body_enabled)
        b.paintEvent(None)
        self.assertTrue(b.legacy_painted)
        b.set_body_enabled(True)
        self.assertTrue(b.body_enabled)
        self.assertFalse(b.using_model)
        with patch.object(self.module, 'ASSET', Path('/nonexistent-lya-body.png')):
            other = self.Body()
        self.assertFalse(other.body_enabled)
        self.assertIs(other.base, other.original)

    def test_low_power_keeps_body(self):
        b = self.body
        asset = b.base
        b.low_power_fallback()
        self.assertIs(b.base, asset)
        self.assertTrue(b.body_enabled)
        self.assertTrue(b.reduced_motion)
        self.assertFalse(b.timer.active)

    def test_request_lifecycle_and_stale_response(self):
        # Execute the actual changed application methods, without Desktop's
        # constructor (which creates real Brain/voice/private runtime objects).
        source = ast.parse((ROOT / 'desktop/app.py').read_text(encoding='utf-8'))
        desktop = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'Desktop')
        methods = [n for n in desktop.body if isinstance(n, ast.FunctionDef)
                   and n.name in {'ask_brain', 'on_brain', 'close_panel'}]
        namespace = {'BrainJob': lambda *args: args}
        exec(compile(ast.Module(body=methods, type_ignores=[]), 'app.py', 'exec'), namespace)
        audio = types.ModuleType('audio')
        audio.voice = types.SimpleNamespace(_THINKING=threading.Event())
        answers, jobs, footnotes, clears = [], [], [], []
        state = types.SimpleNamespace(orb=self.body, brain_busy=False, generation=4,
             brain_cancel=threading.Event(), brain_signals=object(),
             brain=types.SimpleNamespace(client=types.SimpleNamespace(last_route=None),
                                         clear_temporary=lambda: clears.append('brain')),
             panel=types.SimpleNamespace(show_answer=lambda *a: answers.append(a), hide=lambda: None,
                                         footnote=types.SimpleNamespace(setText=footnotes.append)),
             pool=types.SimpleNamespace(start=jobs.append, clear=lambda: clears.append('pool')),
             motion=types.SimpleNamespace(stop=lambda: None), fade=types.SimpleNamespace(stop=lambda: None),
             open_panel=lambda: None, set_state=self.body.set_state)
        with patch.dict(sys.modules, {'audio': audio}):
            namespace['ask_brain'](state, 'debug Python')
            self.assertEqual(jobs[0][1], 'debug Python')
            self.assertEqual(jobs[0][3], 4)
            self.assertEqual(self.body.visual_task, 'coding')
            self.assertTrue(audio.voice._THINKING.is_set())
            namespace['ask_brain'](state, 'build a web page')
            self.assertEqual(len(jobs), 1)
            self.assertEqual(self.body.visual_task, 'coding')
            namespace['close_panel'](state)
            self.assertTrue(state.brain_cancel.is_set())
            self.assertEqual(state.generation, 5)
            self.assertEqual(self.body.visual_task, 'none')
            self.assertFalse(self.body.timer.active)
            self.body.preview_effect('listening')
            namespace['on_brain'](state, 4, types.SimpleNamespace(route='blocked', text='stale'))
            self.assertEqual(self.body.visual_preview, ('listening', 'none'))
            self.assertNotEqual(answers[-1][-1], 'stale')
            state.brain_cancel = threading.Event()
            for route, expected in (('blocked', 'approval'), ('error', 'error'), ('private-local', 'idle')):
                namespace['ask_brain'](state, 'learn this')
                namespace['on_brain'](state, 5, types.SimpleNamespace(route=route, text='synthetic reply'))
                self.assertEqual(self.body.task, expected)
                self.assertEqual(self.body.visual_task, 'none')
                self.assertFalse(audio.voice._THINKING.is_set())
            self.assertEqual(footnotes[-1], 'LOCAL ONLY · CLOUD BLOCKED')


if __name__ == '__main__':
    unittest.main()
