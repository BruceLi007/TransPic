from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QGuiApplication, QImage
from PySide6.QtWidgets import QWidget

import mss
from PIL import Image

_TOOLBAR_W = 64
_TOOLBAR_H = 28
_TOOLBAR_R = 6
_BTN_W = 22
_BTN_H = 20


class ScreenshotOverlay(QWidget):
    region_selected = Signal(object)  # PIL.Image
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._virtual = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(self._virtual)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._pixmap = self._capture()
        self._start = None
        self._end = None
        self._dragging = False
        self._confirmed = False
        self._pending_img = None
        self._hover_btn = None
        self._confirm_rect = QRect()
        self._cancel_rect = QRect()
        self._toolbar_rect = QRect()

    def _capture(self):
        with mss.mss() as sct:
            raw = sct.grab(sct.monitors[0])
            img = QImage(raw.rgb, raw.width, raw.height, raw.width * 3, QImage.Format_RGB888)
            return img

    # -- helpers --------------------------------------------------------------

    def _normalized_rect(self):
        if not self._start or not self._end:
            return QRect()
        p1 = self._start
        p2 = self._end
        return QRect(
            min(p1.x(), p2.x()),
            min(p1.y(), p2.y()),
            abs(p1.x() - p2.x()),
            abs(p1.y() - p2.y()),
        )

    def _crop_selection(self):
        rect = self._normalized_rect()
        if rect.width() < 5 or rect.height() < 5:
            return None

        ox = self._virtual.x()
        oy = self._virtual.y()
        x = rect.x() + ox
        y = rect.y() + oy
        w = rect.width()
        h = rect.height()

        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            raw = sct.grab(monitor)
            return Image.frombytes("RGB", raw.size, raw.rgb)

    def _toolbar_geometry(self, sel_rect: QRect):
        """Position toolbar near bottom-right of selection, avoid overflow."""
        tx = sel_rect.right() - _TOOLBAR_W - 6
        ty = sel_rect.bottom() + 6
        if tx < sel_rect.left():
            tx = sel_rect.left() + 2
        if ty + _TOOLBAR_H > self._virtual.bottom():
            ty = sel_rect.bottom() - _TOOLBAR_H - 6
        toolbar = QRect(tx, ty, _TOOLBAR_W, _TOOLBAR_H)
        self._cancel_rect = QRect(tx + 7, ty + 4, _BTN_W, _BTN_H)
        self._confirm_rect = QRect(tx + 35, ty + 4, _BTN_W, _BTN_H)
        self._toolbar_rect = toolbar

    def _confirm(self):
        self._confirmed = False
        if self._pending_img:
            self.region_selected.emit(self._pending_img)
            self._pending_img = None

    def _cancel_confirm(self):
        self._confirmed = False
        self._pending_img = None
        self._start = None
        self._end = None
        self.update()

    # -- paint ----------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.drawImage(0, 0, self._pixmap)

        if not self._start or not self._end:
            return

        rect = self._normalized_rect()
        if rect.isEmpty():
            return

        # dim overlay outside selection
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        r = self.rect()
        painter.setBrush(QColor(0, 0, 0, 80))
        painter.setPen(Qt.NoPen)
        painter.drawRect(r)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.drawRect(rect)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # border
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)

        # size label at top-left of selection during drag
        if self._dragging:
            painter.setPen(Qt.white)
            font = QFont()
            font.setPixelSize(12)
            painter.setFont(font)
            painter.drawText(
                rect.topLeft() + QPoint(4, -6),
                f"{rect.width()} × {rect.height()}",
            )

        # toolbar when confirmed
        if self._confirmed and not self._toolbar_rect.isEmpty():
            tb = QRectF(self._toolbar_rect)

            # toolbar bg
            painter.setBrush(QColor(45, 45, 45, 220))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(tb, _TOOLBAR_R, _TOOLBAR_R)

            # hover highlight
            if self._hover_btn == "cancel":
                painter.setBrush(QColor(255, 255, 255, 30))
                painter.drawRoundedRect(QRectF(self._cancel_rect), 4, 4)
            elif self._hover_btn == "confirm":
                painter.setBrush(QColor(255, 255, 255, 30))
                painter.drawRoundedRect(QRectF(self._confirm_rect), 4, 4)

            # cancel — X shape
            painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
            cr = QRectF(self._cancel_rect)
            pad = 5
            painter.drawLine(
                QPointF(cr.left() + pad, cr.top() + pad),
                QPointF(cr.right() - pad, cr.bottom() - pad),
            )
            painter.drawLine(
                QPointF(cr.right() - pad, cr.top() + pad),
                QPointF(cr.left() + pad, cr.bottom() - pad),
            )

            # confirm — ✓ checkmark
            cm = QRectF(self._confirm_rect)
            cx1, cy1 = cm.left() + 4, cm.center().y() + 1
            cx2, cy2 = cm.center().x() - 1, cm.bottom() - 4
            cx3, cy3 = cm.right() - 4, cm.top() + 4
            painter.drawLine(QPointF(cx1, cy1), QPointF(cx2, cy2))
            painter.drawLine(QPointF(cx2, cy2), QPointF(cx3, cy3))

    # -- mouse events ---------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        pos = event.position().toPoint()

        if self._confirmed:
            if self._confirm_rect.contains(pos):
                self._confirm()
            elif self._cancel_rect.contains(pos):
                self._cancel_confirm()
            else:
                self._cancel_confirm()
            return

        self._start = pos
        self._end = pos
        self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.setCursor(Qt.CrossCursor)
            self._end = event.position().toPoint()
            self.update()
        elif self._confirmed:
            pos = event.position().toPoint()
            prev = self._hover_btn
            if self._confirm_rect.contains(pos):
                self._hover_btn = "confirm"
                self.setCursor(Qt.PointingHandCursor)
            elif self._cancel_rect.contains(pos):
                self._hover_btn = "cancel"
                self.setCursor(Qt.PointingHandCursor)
            else:
                self._hover_btn = None
                self.setCursor(Qt.ArrowCursor)
            if prev != self._hover_btn:
                self.update()
        else:
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._end = event.position().toPoint()
            self._dragging = False
            img = self._crop_selection()
            if img:
                self._confirmed = True
                self._pending_img = img
                self._toolbar_geometry(self._normalized_rect())
            else:
                self.cancelled.emit()
            self.update()

    # -- keyboard -------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self._confirmed:
                self._cancel_confirm()
                self.update()
            else:
                self.cancelled.emit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._confirmed:
                self._confirm()
