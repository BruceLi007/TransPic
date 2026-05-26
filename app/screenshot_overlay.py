from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, Signal, QTimer
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QGuiApplication, QImage,
    QPainterPath, QLinearGradient,
)
from PySide6.QtWidgets import QWidget

import mss
from PIL import Image

_TOOLBAR_W = 74
_TOOLBAR_H = 34
_TOOLBAR_R = 17
_BTN_SIZE = 26


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
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self._pixmap = self._capture()
        self._start = None
        self._end = None
        self._dragging = False
        self._confirmed = False
        self._pending_img = None
        self._hover_btn = None
        self._cancel_rect = QRect()
        self._confirm_rect = QRect()
        self._toolbar_rect = QRect()

        # instruction text fade
        self._hint_opacity = 1.0
        self._hint_timer = QTimer(self)
        self._hint_timer.timeout.connect(self._fade_hint)
        self._hint_timer.start(50)

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
        tx = sel_rect.right() - _TOOLBAR_W - 8
        ty = sel_rect.bottom() + 10
        if tx < sel_rect.left() + 2:
            tx = sel_rect.left() + 2
        if ty + _TOOLBAR_H > self._virtual.bottom():
            ty = sel_rect.bottom() - _TOOLBAR_H - 10
        self._toolbar_rect = QRect(tx, ty, _TOOLBAR_W, _TOOLBAR_H)
        btn_y = ty + (_TOOLBAR_H - _BTN_SIZE) // 2
        self._cancel_rect = QRect(tx + 8, btn_y, _BTN_SIZE, _BTN_SIZE)
        self._confirm_rect = QRect(tx + _TOOLBAR_W - _BTN_SIZE - 8, btn_y, _BTN_SIZE, _BTN_SIZE)

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

    def _fade_hint(self):
        if self._dragging and self._hint_opacity > 0:
            self._hint_opacity = max(0, self._hint_opacity - 0.08)
            self.update()
        elif not self._dragging and self._hint_opacity < 1.0:
            self._hint_opacity = min(1.0, self._hint_opacity + 0.05)
            self.update()

    def _corner_handles(self, rect: QRectF):
        """Return 4 corner points for a rounded rect."""
        r = 8
        return [
            QPointF(rect.left() + r, rect.top() + r),       # top-left
            QPointF(rect.right() - r, rect.top() + r),       # top-right
            QPointF(rect.left() + r, rect.bottom() - r),     # bottom-left
            QPointF(rect.right() - r, rect.bottom() - r),    # bottom-right
        ]

    # -- paint ----------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.drawImage(0, 0, self._pixmap)

        # instruction hint at top center
        if self._hint_opacity > 0.01 and not self._confirmed:
            painter.save()
            hint = "拖拽框选需要翻译的英文文本"
            font = QFont()
            font.setPixelSize(15)
            painter.setFont(font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(hint) + 32
            th = fm.height() + 20
            hx = (self.width() - tw) // 2
            hy = 40

            hint_rect = QRectF(hx, hy, tw, th)
            painter.setOpacity(self._hint_opacity)
            painter.setBrush(QColor(0, 0, 0, 140))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(hint_rect, 10, 10)
            painter.setPen(QColor(255, 255, 255, 220))
            painter.drawText(hint_rect, Qt.AlignCenter, hint)
            painter.setOpacity(1.0)
            painter.restore()

        if not self._start or not self._end:
            return

        rect = self._normalized_rect()
        if rect.isEmpty():
            return

        rf = QRectF(rect)

        # dim overlay
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # cut out selection with rounded corners
        path = QPainterPath()
        path.addRoundedRect(rf, 8, 8)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.setBrush(Qt.black)
        painter.drawPath(path)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # selection border
        if self._dragging:
            pen = QPen(QColor(255, 255, 255, 200), 2)
            pen.setStyle(Qt.DashLine)
            pen.setDashOffset(self._start.x() if self._start else 0)
        else:
            pen = QPen(QColor(255, 255, 255, 230), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rf, 8, 8)

        # corner handles on confirmed selection
        if self._confirmed:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 200))
            for pt in self._corner_handles(rf):
                painter.drawEllipse(pt, 5, 5)
            painter.setBrush(QColor(124, 58, 237, 180))
            for pt in self._corner_handles(rf):
                painter.drawEllipse(pt, 3, 3)

        # size label during drag
        if self._dragging:
            label = f"{rect.width()} × {rect.height()}"
            font = QFont()
            font.setPixelSize(12)
            painter.setFont(font)
            fm = painter.fontMetrics()
            lw = fm.horizontalAdvance(label) + 14
            lh = fm.height() + 8
            lx = rect.left() + 6
            ly = rect.top() - lh - 6
            if ly < 0:
                ly = rect.top() + 6

            lbl_rect = QRectF(lx, ly, lw, lh)
            painter.setBrush(QColor(0, 0, 0, 160))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(lbl_rect, 6, 6)
            painter.setPen(QColor(255, 255, 255, 230))
            painter.drawText(lbl_rect, Qt.AlignCenter, label)

        # toolbar
        if self._confirmed and not self._toolbar_rect.isEmpty():
            self._draw_toolbar(painter)

    def _draw_toolbar(self, p: QPainter):
        tb = QRectF(self._toolbar_rect)

        # claymorphism shadow
        shadow = QRectF(tb).translated(0, 3)
        p.setBrush(QColor(0, 0, 0, 50))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(shadow, _TOOLBAR_R, _TOOLBAR_R)

        # toolbar body
        grad = QLinearGradient(tb.topLeft(), tb.bottomLeft())
        grad.setColorAt(0.0, QColor(55, 50, 65))
        grad.setColorAt(1.0, QColor(35, 30, 42))
        p.setBrush(grad)
        p.drawRoundedRect(tb, _TOOLBAR_R, _TOOLBAR_R)

        # inner highlight
        hl = QRectF(tb.left() + 2, tb.top() + 1, tb.width() - 4, tb.height() * 0.4)
        hl_grad = QLinearGradient(hl.topLeft(), hl.bottomLeft())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 25))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(hl_grad)
        p.drawRoundedRect(hl, _TOOLBAR_R, _TOOLBAR_R)

        # cancel button
        self._draw_toolbar_btn(p, self._cancel_rect, "cancel")

        # confirm button
        self._draw_toolbar_btn(p, self._confirm_rect, "confirm")

    def _draw_toolbar_btn(self, p: QPainter, rect: QRect, kind: str):
        is_hover = self._hover_btn == kind
        r = QRectF(rect)

        if is_hover:
            # hover background
            hover_rect = r.adjusted(-2, -2, 2, 2)
            if kind == "confirm":
                p.setBrush(QColor(16, 185, 129, 40))
            else:
                p.setBrush(QColor(239, 68, 68, 40))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(hover_rect, 8, 8)

        pen_w = 2.5
        if kind == "confirm":
            color = QColor(16, 185, 129) if not is_hover else QColor(52, 211, 153)
        else:
            color = QColor(239, 68, 68) if not is_hover else QColor(248, 113, 113)

        pen = QPen(color, pen_w)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

        pad = 6
        if kind == "confirm":
            # checkmark
            cx = r.center().x()
            cy = r.center().y()
            p.drawLine(
                QPointF(cx - 5, cy),
                QPointF(cx - 1, cy + 4),
            )
            p.drawLine(
                QPointF(cx - 1, cy + 4),
                QPointF(cx + 6, cy - 5),
            )
        else:
            # X
            p.drawLine(
                QPointF(r.left() + pad, r.top() + pad),
                QPointF(r.right() - pad, r.bottom() - pad),
            )
            p.drawLine(
                QPointF(r.right() - pad, r.top() + pad),
                QPointF(r.left() + pad, r.bottom() - pad),
            )

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
