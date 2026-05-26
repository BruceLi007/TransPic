import math
import random

from typing import Callable

from PySide6.QtCore import Qt, QRect, QTimer, QRectF, QPointF, Signal, Property, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QPen, QLinearGradient, QBrush, QCursor,
    QFont, QPainterPath,
)
from PySide6.QtWidgets import QWidget

_PET_Y_OFFSET = 48
_BUILD_MSGS = ["点我 点我！", "翻译一下？", "截个图吧~", "学英语啦！"]


class PetWidget(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(110, 170)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self._phase = 0.0
        self._thinking = False
        self._dots = 0
        self._dot_counter = 0
        self._dot_alpha = [0, 0, 0]

        # blink state
        self._blink = 0.0
        self._blink_timer = random.randint(3000, 5000)
        self._blink_elapsed = 0
        self._blinking = False

        # click bounce
        self._bounce = 0.0

        # hover
        self._hovered = False
        self._hover_alpha = 0.0

        # speech bubble state
        self._bubble_alpha = 0.0
        self._bubble_msg = random.choice(_BUILD_MSGS)
        self._bubble_state = "fading_in"  # idle | fading_in | visible | fading_out
        self._bubble_state_elapsed = 0
        self._bubble_idle_dur = random.randint(12000, 25000)  # 12-25s hidden
        self._bubble_show_dur = 3500   # 3.5s visible
        self._bubble_bob = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)  # ~60fps

        self._drag_pos = None
        self._normal_pos = None
        self._move_callback: Callable[[QRect], None] | None = None

    def set_thinking(self, on: bool):
        self._thinking = on
        self._dots = 0
        self._dot_counter = 0
        self._dot_alpha = [0, 0, 0]
        if on:
            self._bubble_state = "idle"
            self._bubble_state_elapsed = 0
            self._bubble_alpha = 0.0

    # -- animation -----------------------------------------------------------

    def _animate(self):
        dt = 16 / 1000.0
        self._phase += 0.05

        # blink logic
        if not self._thinking:
            self._blink_elapsed += 16
            if not self._blinking and self._blink_elapsed >= self._blink_timer:
                self._blinking = True
                self._blink_elapsed = 0
            if self._blinking:
                self._blink_elapsed += 16
                if self._blink_elapsed < 80:
                    self._blink = min(1.0, self._blink_elapsed / 80.0)
                elif self._blink_elapsed < 200:
                    self._blink = 1.0
                elif self._blink_elapsed < 280:
                    self._blink = max(0.0, 1.0 - (self._blink_elapsed - 200) / 80.0)
                else:
                    self._blink = 0.0
                    self._blinking = False
                    self._blink_elapsed = 0
                    self._blink_timer = random.randint(2500, 5000)

        # bounce decay
        if self._bounce > 0.001:
            self._bounce *= 0.88
        else:
            self._bounce = 0.0

        # hover alpha smoothing
        target = 1.0 if self._hovered else 0.0
        self._hover_alpha += (target - self._hover_alpha) * 0.15

        # thinking dots
        if self._thinking:
            self._dot_counter += 1
            if self._dot_counter >= 10:
                self._dots = (self._dots + 1) % 4
                self._dot_counter = 0
            for i in range(3):
                target_a = 255 if i < self._dots else 40
                self._dot_alpha[i] += (target_a - self._dot_alpha[i]) * 0.3

        # speech bubble state machine (only when not thinking)
        if not self._thinking:
            self._bubble_state_elapsed += 16
            if self._bubble_state == "idle":
                if self._bubble_state_elapsed >= self._bubble_idle_dur:
                    self._bubble_state = "fading_in"
                    self._bubble_state_elapsed = 0
                    self._bubble_msg = random.choice(_BUILD_MSGS)
            elif self._bubble_state == "fading_in":
                self._bubble_alpha = min(1.0, self._bubble_state_elapsed / 300.0)
                self._bubble_bob = math.sin(self._bubble_alpha * math.pi) * 6
                if self._bubble_state_elapsed >= 300:
                    self._bubble_state = "visible"
                    self._bubble_state_elapsed = 0
                    self._bubble_alpha = 1.0
            elif self._bubble_state == "visible":
                self._bubble_bob = math.sin(self._phase * 1.2) * 2
                if self._bubble_state_elapsed >= self._bubble_show_dur:
                    self._bubble_state = "fading_out"
                    self._bubble_state_elapsed = 0
            elif self._bubble_state == "fading_out":
                self._bubble_alpha = max(0.0, 1.0 - self._bubble_state_elapsed / 250.0)
                if self._bubble_state_elapsed >= 250:
                    self._bubble_state = "idle"
                    self._bubble_state_elapsed = 0
                    self._bubble_alpha = 0.0
                    self._bubble_idle_dur = random.randint(12000, 25000)

        self.update()

    def _trigger_bounce(self):
        self._bounce = 1.0
        # dismiss bubble on click
        if self._bubble_state in ("visible", "fading_in"):
            self._bubble_state = "fading_out"
            self._bubble_state_elapsed = 0

    # -- paint ---------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        # breathing + bounce
        breath = 1.0 + 0.02 * math.sin(self._phase)
        bounce_y = -abs(self._bounce) * 6 * math.sin(self._bounce * math.pi)

        # pet center (shifted down by _PET_Y_OFFSET for bubble space)
        cx, cy = w / 2, h / 2 - 4 + _PET_Y_OFFSET / 2
        painter.translate(cx, cy + bounce_y)
        painter.scale(breath, breath)
        painter.translate(-cx, -cy)

        # speech bubble (drawn before pet, so it's behind if overlapping)
        self._draw_speech_bubble(painter, w)

        self._draw_glow(painter, w, h)
        self._draw_shadow(painter)
        self._draw_body(painter, w, h)
        self._draw_ears(painter, w, h)
        self._draw_feet(painter, w, h)
        if not self._thinking:
            self._draw_eyes(painter, w, h)
            self._draw_blush(painter, w, h)
            self._draw_mouth(painter, w, h)
        else:
            self._draw_thinking_eyes(painter, w, h)
            self._draw_thinking_dots(painter, w, h)

    def _draw_speech_bubble(self, p: QPainter, w: int):
        if self._bubble_alpha < 0.01:
            return

        p.save()
        p.setOpacity(self._bubble_alpha)

        # measure text
        font = QFont()
        font.setPixelSize(12)
        font.setBold(True)
        p.setFont(font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(self._bubble_msg)
        th = fm.height()

        # bubble dimensions
        pad_h = 14
        pad_v = 8
        bw = tw + pad_h * 2
        bh = th + pad_v * 2
        bx = (w - bw) / 2
        by = 4 + self._bubble_bob
        arrow_h = 6
        arrow_w = 10

        bubble_rect = QRectF(bx, by, bw, bh)

        # shadow
        shadow_path = QPainterPath()
        shadow_rect = QRectF(bubble_rect).translated(0, 2)
        shadow_path.addRoundedRect(shadow_rect, bh / 2, bh / 2)
        # arrow shadow
        ax = w / 2
        ay = by + bh
        shadow_path.moveTo(ax - arrow_w / 2, ay + 2)
        shadow_path.lineTo(ax, ay + arrow_h + 2)
        shadow_path.lineTo(ax + arrow_w / 2, ay + 2)
        shadow_path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 30))
        p.drawPath(shadow_path)

        # bubble body with gradient
        bubble_path = QPainterPath()
        bubble_path.addRoundedRect(bubble_rect, bh / 2, bh / 2)
        # arrow
        bubble_path.moveTo(ax - arrow_w / 2, ay)
        bubble_path.lineTo(ax, ay + arrow_h)
        bubble_path.lineTo(ax + arrow_w / 2, ay)
        bubble_path.closeSubpath()

        bg_grad = QLinearGradient(bubble_rect.topLeft(), bubble_rect.bottomLeft())
        bg_grad.setColorAt(0.0, QColor(255, 255, 255))
        bg_grad.setColorAt(1.0, QColor(245, 240, 255))
        p.setBrush(bg_grad)
        p.setPen(QPen(QColor(200, 190, 220), 1))
        p.drawPath(bubble_path)

        # claymorphism top highlight
        hl_rect = QRectF(bubble_rect.left() + 3, bubble_rect.top() + 1,
                         bubble_rect.width() - 6, bubble_rect.height() * 0.45)
        hl_path = QPainterPath()
        hl_path.addRoundedRect(hl_rect, bh / 2 - 2, bh / 2 - 2)
        hl_grad = QLinearGradient(hl_rect.topLeft(), hl_rect.bottomLeft())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 130))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(hl_grad)
        p.setPen(Qt.NoPen)
        p.drawPath(hl_path)

        # text
        p.setPen(QColor(124, 58, 237))
        p.drawText(bubble_rect, Qt.AlignCenter, self._bubble_msg)

        p.restore()

    def _draw_shadow(self, p: QPainter):
        """Soft shadow beneath the pet."""
        grad = QRadialGradient(55, 100 + _PET_Y_OFFSET, 45)
        grad.setColorAt(0.0, QColor(0, 0, 0, 35))
        grad.setColorAt(0.5, QColor(0, 0, 0, 15))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(15, 88 + _PET_Y_OFFSET, 80, 22))

    def _draw_glow(self, p: QPainter, w: int, h: int):
        base_alpha = 40 + 30 * math.sin(self._phase)
        hover_boost = int(self._hover_alpha * 40)
        alpha = min(255, base_alpha + hover_boost)
        grad = QRadialGradient(55, 55 + _PET_Y_OFFSET, 60)
        grad.setColorAt(0.0, QColor(255, 184, 140, alpha))
        grad.setColorAt(0.5, QColor(255, 184, 140, alpha // 2))
        grad.setColorAt(1.0, QColor(255, 184, 140, 0))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(-8, -8 + _PET_Y_OFFSET, 126, 126))

    def _draw_body(self, p: QPainter, w: int, h: int):
        body = QRectF(12, 18 + _PET_Y_OFFSET, 86, 78)

        grad = QLinearGradient(body.topLeft(), body.bottomRight())
        grad.setColorAt(0.0, QColor(255, 200, 160))
        grad.setColorAt(0.4, QColor(255, 184, 140))
        grad.setColorAt(1.0, QColor(245, 165, 120))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(body, 38, 38)

        hl = QRectF(body.left() + 6, body.top() + 4, body.width() - 12, body.height() * 0.45)
        hl_grad = QLinearGradient(hl.topLeft(), hl.bottomLeft())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 90))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(hl_grad)
        p.drawRoundedRect(hl, 30, 30)

        belly = QRectF(28, 48 + _PET_Y_OFFSET, 54, 38)
        p.setBrush(QColor(255, 220, 195, 120))
        p.drawRoundedRect(belly, 22, 22)

    def _draw_ears(self, p: QPainter, w: int, h: int):
        p.setPen(Qt.NoPen)
        off = _PET_Y_OFFSET
        left_ear = QRectF(16, 10 + off, 22, 20)
        grad_l = QLinearGradient(left_ear.topLeft(), left_ear.bottomRight())
        grad_l.setColorAt(0.0, QColor(255, 195, 155))
        grad_l.setColorAt(1.0, QColor(240, 160, 120))
        p.setBrush(grad_l)
        p.drawRoundedRect(left_ear, 10, 10)
        inner_l = QRectF(20, 13 + off, 14, 14)
        p.setBrush(QColor(255, 180, 160, 100))
        p.drawRoundedRect(inner_l, 7, 7)

        right_ear = QRectF(72, 10 + off, 22, 20)
        grad_r = QLinearGradient(right_ear.topLeft(), right_ear.bottomRight())
        grad_r.setColorAt(0.0, QColor(255, 195, 155))
        grad_r.setColorAt(1.0, QColor(240, 160, 120))
        p.setBrush(grad_r)
        p.drawRoundedRect(right_ear, 10, 10)
        inner_r = QRectF(76, 13 + off, 14, 14)
        p.setBrush(QColor(255, 180, 160, 100))
        p.drawRoundedRect(inner_r, 7, 7)

    def _draw_feet(self, p: QPainter, w: int, h: int):
        p.setPen(Qt.NoPen)
        off = _PET_Y_OFFSET
        foot_grad = QLinearGradient(0, 90 + off, 0, 100 + off)
        foot_grad.setColorAt(0.0, QColor(245, 165, 125))
        foot_grad.setColorAt(1.0, QColor(230, 145, 105))
        p.setBrush(foot_grad)
        p.drawEllipse(QRectF(28, 90 + off, 22, 12))
        p.drawEllipse(QRectF(60, 90 + off, 22, 12))

    def _draw_eyes(self, p: QPainter, w: int, h: int):
        if self._blink > 0.01:
            self._draw_blink_eyes(p, w, h)
            return
        off = _PET_Y_OFFSET
        self._draw_eye(p, 36, 42 + off, -2)
        self._draw_eye(p, 74, 42 + off, 2)

    def _draw_eye(self, p: QPainter, cx: float, cy: float, pupil_off: float):
        p.setBrush(QColor(255, 255, 255))
        p.setPen(QPen(QColor(200, 180, 170), 1.2))
        p.drawEllipse(QPointF(cx, cy), 11, 13)

        iris_grad = QRadialGradient(cx, cy, 7)
        iris_grad.setColorAt(0.0, QColor(60, 40, 30))
        iris_grad.setColorAt(0.6, QColor(80, 55, 40))
        iris_grad.setColorAt(1.0, QColor(100, 70, 50))
        p.setBrush(iris_grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx + pupil_off * 0.5, cy + 1), 6.5, 7.5)

        p.setBrush(QColor(20, 15, 10))
        p.drawEllipse(QPointF(cx + pupil_off * 0.7, cy + 1), 4, 4.5)

        p.setBrush(QColor(255, 255, 255, 240))
        p.drawEllipse(QPointF(cx + pupil_off * 0.3 - 1, cy - 3), 3, 2.8)
        p.setBrush(QColor(255, 255, 255, 100))
        p.drawEllipse(QPointF(cx + pupil_off * 0.3 + 4, cy + 3), 1.8, 1.5)

    def _draw_blink_eyes(self, p: QPainter, w: int, h: int):
        off = _PET_Y_OFFSET
        p.setPen(QPen(QColor(80, 50, 40), 2))
        for cx in [36, 74]:
            y = 42 + off
            p.drawLine(QPointF(cx - 8, y), QPointF(cx + 8, y))
            p.setPen(QPen(QColor(80, 50, 40, int(80 * self._blink)), 1.5))
            p.drawArc(QRectF(cx - 9, y - 3, 18, 6), 0, 180 * 16)

    def _draw_blush(self, p: QPainter, w: int, h: int):
        off = _PET_Y_OFFSET
        for cx, cy in [(22, 58 + off), (88, 58 + off)]:
            grad = QRadialGradient(cx, cy, 10)
            grad.setColorAt(0.0, QColor(255, 140, 140, 90))
            grad.setColorAt(0.5, QColor(255, 160, 150, 50))
            grad.setColorAt(1.0, QColor(255, 180, 170, 0))
            p.setBrush(grad)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, cy), 9, 6)

    def _draw_mouth(self, p: QPainter, w: int, h: int):
        off = _PET_Y_OFFSET
        pen = QPen(QColor(170, 90, 70), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(43, 60 + off, 24, 16), 0, -180 * 16)

    def _draw_thinking_eyes(self, p: QPainter, w: int, h: int):
        off = _PET_Y_OFFSET
        for cx in [36, 74]:
            p.setBrush(QColor(255, 255, 255))
            p.setPen(QPen(QColor(200, 180, 170), 1.2))
            p.drawEllipse(QPointF(cx, 39 + off), 10, 12)
            p.setBrush(QColor(70, 50, 38))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx, 35 + off), 5, 5)
            p.setBrush(QColor(20, 15, 10))
            p.drawEllipse(QPointF(cx, 34 + off), 2.8, 3)
            p.setBrush(QColor(255, 255, 255, 230))
            p.drawEllipse(QPointF(cx - 1, 32 + off), 2, 1.8)

    def _draw_thinking_dots(self, p: QPainter, w: int, h: int):
        off = _PET_Y_OFFSET
        for i in range(3):
            alpha = int(self._dot_alpha[i])
            if alpha < 5:
                continue
            p.setBrush(QColor(140, 120, 180, alpha))
            p.setPen(Qt.NoPen)
            y_offset = -i * 10 - 6 * math.sin(self._phase * 2 + i)
            p.drawEllipse(QPointF(55, 2 + off + y_offset), 3.5, 3.5)

    # -- mouse events --------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._normal_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self._normal_pos + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos and (event.globalPosition().toPoint() - self._drag_pos).manhattanLength() < 5:
                self._trigger_bounce()
                self.clicked.emit()
            self._drag_pos = None
            self._normal_pos = None

    def enterEvent(self, event):
        self._hovered = True

    def leaveEvent(self, event):
        self._hovered = False

    def set_move_callback(self, cb: Callable[[QRect], None] | None):
        self._move_callback = cb

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._move_callback:
            self._move_callback(self.geometry())
