import math

from typing import Callable

from PySide6.QtCore import Qt, QRect, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen
from PySide6.QtWidgets import QWidget


class PetWidget(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(100, 110)

        self._phase = 0.0
        self._thinking = False
        self._dots = 0
        self._dot_counter = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

        self._drag_pos = None
        self._normal_pos = None
        self._move_callback: Callable[[QRect], None] | None = None

    def set_thinking(self, on: bool):
        self._thinking = on
        self._dots = 0
        self._dot_counter = 0

    # -- animation -----------------------------------------------------------

    def _animate(self):
        self._phase += 0.08
        if self._thinking:
            self._dot_counter += 1
            if self._dot_counter >= 8:
                self._dots = (self._dots + 1) % 4
                self._dot_counter = 0
        self.update()

    # -- paint ---------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # breathing scale
        breath = 1.0 + 0.025 * math.sin(self._phase)
        cx, cy = w / 2, h / 2 - 5
        painter.translate(cx, cy)
        painter.scale(breath, breath)
        painter.translate(-cx, -cy)

        self._draw_glow(painter)
        self._draw_body(painter, w, h)
        if not self._thinking:
            self._draw_eyes(painter, w, h)
            self._draw_blush(painter, w, h)
            self._draw_mouth(painter, w, h)
        else:
            self._draw_thinking_eyes(painter, w, h)
            self._draw_dots(painter, w, h)

    def _draw_glow(self, p: QPainter):
        alpha = int(35 + 25 * math.sin(self._phase))
        grad = QRadialGradient(50, 55, 55)
        grad.setColorAt(0.0, QColor(255, 190, 150, alpha))
        grad.setColorAt(0.6, QColor(255, 190, 150, alpha // 2))
        grad.setColorAt(1.0, QColor(255, 190, 150, 0))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(-5, 0, 110, 110))

    @staticmethod
    def _draw_body(p: QPainter, w: int, h: int):
        body = QRectF(10, 15, 80, 75)
        grad = QColor(255, 190, 150)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(body, 35, 35)

        # belly highlight
        belly = QRectF(25, 40, 50, 40)
        p.setBrush(QColor(255, 215, 185, 100))
        p.drawRoundedRect(belly, 20, 20)

    @staticmethod
    def _draw_eyes(p: QPainter, w: int, h: int):
        # left eye
        p.setBrush(Qt.white)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(35, 40), 10, 12)
        p.setBrush(QColor(50, 50, 50))
        p.drawEllipse(QPointF(37, 42), 6, 7)
        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(39, 40), 2.5, 2.5)

        # right eye
        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(65, 40), 10, 12)
        p.setBrush(QColor(50, 50, 50))
        p.drawEllipse(QPointF(63, 42), 6, 7)
        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(61, 40), 2.5, 2.5)

    @staticmethod
    def _draw_thinking_eyes(p: QPainter, w: int, h: int):
        # looking up
        p.setBrush(Qt.white)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(35, 38), 10, 12)
        p.setBrush(QColor(50, 50, 50))
        p.drawEllipse(QPointF(35, 35), 5, 5)
        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(36, 33), 2, 2)

        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(65, 38), 10, 12)
        p.setBrush(QColor(50, 50, 50))
        p.drawEllipse(QPointF(65, 35), 5, 5)
        p.setBrush(Qt.white)
        p.drawEllipse(QPointF(64, 33), 2, 2)

    @staticmethod
    def _draw_blush(p: QPainter, w: int, h: int):
        p.setBrush(QColor(255, 150, 150, 80))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(20, 55), 8, 5)
        p.drawEllipse(QPointF(80, 55), 8, 5)

    @staticmethod
    def _draw_mouth(p: QPainter, w: int, h: int):
        pen = QPen(QColor(180, 100, 80), 2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        path = [
            QPointF(43, 58),
            QPointF(48, 63),
            QPointF(50, 64),
            QPointF(52, 63),
            QPointF(57, 58),
        ]
        for i in range(len(path) - 1):
            p.drawLine(path[i], path[i + 1])

    def _draw_dots(self, p: QPainter, w: int, h: int):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(100, 100, 100))
        dot_count = self._dots if self._dots > 0 else 3
        for i in range(dot_count):
            p.drawEllipse(QPointF(45 + i * 12, 8), 3, 3)

    # -- mouse events --------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            self._normal_pos = self.pos()

    def set_move_callback(self, cb: Callable[[QRect], None] | None):
        self._move_callback = cb

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._move_callback:
            self._move_callback(self.geometry())

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self._normal_pos + delta)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos and (event.globalPosition().toPoint() - self._drag_pos).manhattanLength() < 5:
                self.clicked.emit()
            self._drag_pos = None
            self._normal_pos = None
