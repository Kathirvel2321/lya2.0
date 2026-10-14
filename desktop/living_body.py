"""Native fixed-artwork body and layered effects; no WebView or sensor reader."""
import time
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImageReader, QPainter, QPainterPath, QPen, QPixmap

from body_style import frame, load_config, should_animate
from layout import PERSON_COLORS, TASK_COLORS, accent

ASSET = Path(__file__).resolve().parent.parent / 'visual creativity' / 'assets' / 'lya-body-anchor.png'


def create_body_type(crystal_type):
    """Inherit input/drag/keyboard behavior without importing app recursively."""
    class LivingBody(crystal_type):
        body_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.body_enabled = False
            self.body_art = QPixmap()
            self.body_config = None
            self.visual_task = 'none'
            self.request_pending = False
            self._finished_thought = False
            self.visual_preview = None
            self._body_cache = None
            self._cache_key = None
            self._last_frame = 0.0
            try:
                self.body_config = load_config()
                if not ASSET.is_file() or ASSET.stat().st_size > 2_000_000:
                    raise ValueError('Missing or oversized body artwork')
                reader = QImageReader(str(ASSET))
                size = reader.size()
                if not (0 < size.width() <= 1600 and 0 < size.height() <= 1600):
                    raise ValueError('Invalid body dimensions')
                self.body_art = QPixmap.fromImage(reader.read())
                if self.body_art.isNull():
                    raise ValueError('Unreadable body artwork')
            except (OSError, ValueError, KeyError, TypeError):
                self.body_config = None  # Existing crystal stays usable.
            self.set_body_enabled(self.body_config is not None)

        def set_body_enabled(self, enabled):
            self.body_enabled = bool(enabled and self.body_config and not self.body_art.isNull())
            if self.body_enabled:
                self.animation.stop()
                self.using_model = False
                self.base = self.body_art
                self.clearMask()
                self.setWindowTitle('LYA')
                self.set_blend(1.0)
                self.paint_samples.clear()
                self.refresh_effects()
                self.artwork_changed.emit(False)
            else:
                super().set_artwork(self.using_model)
            self.body_changed.emit(self.body_enabled)
            self.update()

        def set_artwork(self, enabled):
            self.body_enabled = False
            super().set_artwork(enabled)
            self.body_changed.emit(False)

        def set_state(self, person=None, task=None):
            self.visual_preview = None
            if not getattr(self, 'body_enabled', False):
                return super().set_state(person, task)
            if person is not None:
                if person not in PERSON_COLORS:
                    raise ValueError('Unknown presentation palette')
                self.person = person
            if task is not None:
                if task not in TASK_COLORS:
                    raise ValueError('Unknown task state')
                self.task = task
            self.start_color = self.target_color = QColor(accent(self.person, self.task))
            self.animation.stop()
            self.set_blend(1.0)
            self.refresh_effects()

        def set_visual_task(self, task, pending=False):
            if self.body_config is None:
                return
            if task not in self.body_config['tasks']:
                raise ValueError('Unknown visual task')
            self._finished_thought = task == 'none' and self.request_pending
            self.visual_task, self.request_pending = task, bool(pending)
            self.visual_preview = None
            if self.body_enabled:
                self.refresh_effects()

        def preview_effect(self, interaction='idle', task='none'):
            if self.body_config is None:
                return
            # Validate before storing; preview never changes the voice phase.
            frame(self.body_config, interaction, task, 0)
            self.visual_preview = (interaction, task)
            if self.body_enabled:
                self.refresh_effects()

        def visual_frame(self, elapsed=0):
            if self.visual_preview is not None:
                return frame(self.body_config, *self.visual_preview, elapsed, .35, self.reduced_motion)
            interaction = {'off': 'voice_off', 'transcribing': 'thinking'}.get(self.voice_phase, self.voice_phase)
            if interaction not in self.body_config['interaction']:
                interaction = 'idle'
            if self._finished_thought and interaction == 'thinking':
                interaction = 'idle'  # End the request effect without changing input state.
            task = self.visual_task
            if self.task in ('approval', 'error', 'success', 'files'):
                task = self.task
            elif self.task == 'thinking' and self.request_pending:
                interaction = 'thinking'
            # A request accent does not make voice-off appear to be listening.
            return frame(self.body_config, interaction, task, elapsed,
                         self.voice_level if self.voice_phase in ('listening', 'hearing') else .35,
                         self.reduced_motion)

        def refresh_effects(self):
            if not getattr(self, 'body_enabled', False):
                return
            current = self.visual_frame()
            moving = should_animate(current, self.isVisible(), self.body_enabled, self.reduced_motion)
            self.timer.setInterval(34)  # No more than 30 scheduled frames/sec.
            if moving and not self.timer.isActive():
                self.started = time.monotonic()
                self._last_frame = 0.0
                self.timer.start()
            elif not moving:
                self.timer.stop()
                self.phase = 0.0
            self.update()

        def animate_briefly(self):
            if getattr(self, 'body_enabled', False):
                self.refresh_effects()
            else:
                super().animate_briefly()

        def set_voice_phase(self, phase):
            self.visual_preview = None
            self._finished_thought = False
            super().set_voice_phase(phase)
            if self.body_enabled:
                self.refresh_effects()

        def set_reduced_motion(self, enabled):
            super().set_reduced_motion(enabled)
            if self.body_enabled:
                self.refresh_effects()

        def tick(self):
            if not self.body_enabled:
                return super().tick()
            now = time.monotonic()
            if not should_animate(self.visual_frame(), self.isVisible(), True, self.reduced_motion):
                self.refresh_effects()
                return
            if now - self._last_frame < 1 / 30:
                return
            self._last_frame = now
            self.phase = now - self.started
            if self.voice_phase in ('listening', 'hearing'):
                # Read only the existing listener's level; never open another mic.
                from audio import voice
                self.voice_level = voice.listener_health()['level']
            self.update()

        def low_power_fallback(self):
            if self.body_enabled:
                self.set_reduced_motion(True)  # Keep the same body, static effects.
            else:
                super().low_power_fallback()

        def paintEvent(self, event):
            if not self.body_enabled:
                return super().paintEvent(event)
            started = time.perf_counter()
            p = QPainter(self)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            unit = min(self.width() / 1.14, self.height() / .96)
            p.translate(self.width() / 2, self.height() / 2)
            current = self.visual_frame(self.phase)

            def draw_layer(layer):
                for command in current['commands']:
                    if command['layer'] != layer:
                        continue
                    color = QColor(command['color'])
                    if command['kind'] == 'dot':
                        color.setAlphaF(command['alpha'])
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(color)
                        radius = max(.55, command['r'] * unit)
                        p.drawEllipse(QPointF(command['x'] * unit, command['y'] * unit), radius, radius)
                        continue
                    points = command['points']
                    if len(points) < 2:
                        continue
                    path = QPainterPath(QPointF(points[0][0] * unit, points[0][1] * unit))
                    for x, y in points[1:]:
                        path.lineTo(x * unit, y * unit)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    # Two soft edge strokes avoid a per-frame blur/render target.
                    for extra, opacity in ((4, .05), (2, .10), (0, 1)):
                        if extra and not command['glow']:
                            continue
                        color.setAlphaF(command['alpha'] * opacity)
                        width = max(.65, command['width'] * unit / 300) + extra * min(1, unit / 300)
                        pen = QPen(color, width)
                        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                        if command['dash']:
                            pen.setDashPattern(command['dash'])
                        p.setPen(pen)
                        p.drawPath(path)

            draw_layer('back')
            # One cached sprite for each widget size/DPR. State never tints it.
            height = unit * .82
            width = height * self.body_art.width() / self.body_art.height()
            dpr = max(1., min(2., self.devicePixelRatioF()))
            key = (round(width * dpr), round(height * dpr), dpr)
            if key != self._cache_key:
                self._body_cache = self.body_art.scaled(key[0], key[1], Qt.AspectRatioMode.KeepAspectRatio,
                                                        Qt.TransformationMode.SmoothTransformation)
                self._body_cache.setDevicePixelRatio(dpr)
                self._cache_key = key
            p.drawPixmap(QPointF(-self._body_cache.width() / dpr / 2,
                                -self._body_cache.height() / dpr / 2), self._body_cache)
            draw_layer('front')
            p.end()
            self.paint_samples.append((time.perf_counter() - started) * 1000)
            self.paint_samples = self.paint_samples[-30:]
            if len(self.paint_samples) == 30 and sum(self.paint_samples) / 30 > 8 and not self.reduced_motion:
                # Do not toggle geometry when a device is slow.
                self.set_reduced_motion(True)

        def showEvent(self, event):
            super().showEvent(event)
            if self.body_enabled:
                self.refresh_effects()

    return LivingBody
