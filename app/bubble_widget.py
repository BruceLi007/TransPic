import re

import pyperclip
from PySide6.QtCore import Qt, QRect, QRectF, Signal, QPointF, QPropertyAnimation, QEasingCurve, QTimer, Property
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QGuiApplication, QPainterPath,
    QLinearGradient, QRadialGradient,
)
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGraphicsOpacityEffect,
)

_MAX_WIDTH = 720
_MAX_HEIGHT = 520
_MARGIN = 24
_RADIUS = 14

_ACCENT = {
    "原文": ("#94A3B8", "#CBD5E1"),
    "标准中文翻译": ("#7C3AED", "#A78BFA"),
    "考研重点词汇解析": ("#F59E0B", "#FBBF24"),
    "翻译结果": ("#7C3AED", "#A78BFA"),
}

_SECTION_ICONS = {
    "原文": "text",
    "标准中文翻译": "translate",
    "考研重点词汇解析": "vocab",
    "翻译结果": "translate",
}


class BubbleWidget(QWidget):
    closed = Signal()

    def __init__(self, pet_rect: QRect, original: str, translated: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._original = original
        self._translated = translated
        self._pet_rect = pet_rect
        self._copy_success = False
        self._slide_offset = 0.0

        self._setup_ui()
        self._position_near(pet_rect)

        # entry animation
        self._animate_entry()

    # -- entry animation -------------------------------------------------------

    def _animate_entry(self):
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim_opacity = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim_opacity.setDuration(220)
        self._anim_opacity.setStartValue(0.0)
        self._anim_opacity.setEndValue(1.0)
        self._anim_opacity.setEasingCurve(QEasingCurve.OutCubic)

        # slide animation
        self._slide_start_y = self.y()
        self._anim_slide = QPropertyAnimation(self, b"slideOffset")
        self._anim_slide.setDuration(220)
        self._anim_slide.setStartValue(20.0)
        self._anim_slide.setEndValue(0.0)
        self._anim_slide.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_opacity.start()
        self._anim_slide.start()

    def _get_slide_offset(self):
        return self._slide_offset

    def _set_slide_offset(self, val):
        self._slide_offset = val
        self.move(self.x(), int(self._slide_start_y + val))

    slideOffset = Property(float, _get_slide_offset, _set_slide_offset)

    def close_with_animation(self):
        """Animate out then close."""
        if not self._opacity_effect:
            self.close()
            return
        self._anim_opacity.setDuration(150)
        self._anim_opacity.setStartValue(1.0)
        self._anim_opacity.setEndValue(0.0)
        self._anim_opacity.setEasingCurve(QEasingCurve.InCubic)
        self._anim_opacity.finished.connect(self._on_close_done)
        self._anim_opacity.start()

        self._anim_slide.setDuration(150)
        self._anim_slide.setStartValue(0.0)
        self._anim_slide.setEndValue(15.0)
        self._anim_slide.setEasingCurve(QEasingCurve.InCubic)
        self._anim_slide.start()

    def _on_close_done(self):
        self.closed.emit()

    # -- layout ----------------------------------------------------------------

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        hdr = QHBoxLayout()
        hdr.setContentsMargins(_MARGIN, 16, _MARGIN - 4, 12)

        title = QLabel("TransPic")
        title.setStyleSheet(
            "color: #7C3AED; font-size: 13px; font-weight: bold;"
            "letter-spacing: 1.5px; background: transparent;"
        )
        hdr.addWidget(title)
        hdr.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton {"
            "  background: transparent; border: none; color: #94A3B8;"
            "  font-size: 16px; border-radius: 13px;"
            "}"
            "QPushButton:hover {"
            "  background: #F1F5F9; color: #475569;"
            "}"
        )
        btn_close.clicked.connect(self.close_with_animation)
        hdr.addWidget(btn_close)
        layout.addLayout(hdr)

        # separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "  stop:0 #E2E8F0, stop:0.5 #CBD5E1, stop:1 #E2E8F0);"
            "  border: none;"
        )
        layout.addWidget(sep)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: transparent; margin: 2px 0; }"
            "QScrollBar::handle:vertical {"
            "  background: #CBD5E1; border-radius: 2px; min-height: 28px;"
            "}"
            "QScrollBar::handle:vertical:hover { background: #94A3B8; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        inner = QVBoxLayout(body)
        inner.setContentsMargins(_MARGIN, 4, _MARGIN, _MARGIN)
        inner.setSpacing(0)

        self._build_sections(inner)

        scroll.setWidget(body)
        layout.addWidget(scroll)

        self._clamp_size(scroll)

        # footer
        ft = QHBoxLayout()
        ft.setContentsMargins(_MARGIN, 8, _MARGIN, 16)
        ft.addStretch()
        self._btn_copy = QPushButton("  复制译文")
        self._btn_copy.setCursor(Qt.PointingHandCursor)
        self._btn_copy.setFixedHeight(34)
        self._btn_copy.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #8B5CF6, stop:1 #7C3AED);"
            "  border: none; border-radius: 17px;"
            "  padding: 0 20px; font-size: 12px; color: #fff; font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #9B6DF7, stop:1 #8B5CF6);"
            "}"
            "QPushButton:pressed {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #7C3AED, stop:1 #6D28D9);"
            "}"
        )
        self._btn_copy.clicked.connect(self._copy_text)
        ft.addWidget(self._btn_copy)
        layout.addLayout(ft)

        self._card = card
        outer.addWidget(card)

    def _build_sections(self, layout: QVBoxLayout):
        self._add_section(layout, "原文", self._original, is_original=True)

        sections = self._split_sections(self._translated)
        for title, body in sections:
            self._add_section(layout, title, body)

    def _add_section(self, layout: QVBoxLayout, title: str, body: str, is_original: bool = False):
        c1, c2 = _ACCENT.get(title, ("#888", "#aaa"))

        layout.addSpacing(16)

        # title row: icon + accent dot + title
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        # accent dot
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background: qradialgradient(cx:0.4, cy:0.4, radius:0.6,"
            f"  stop:0 {c2}, stop:1 {c1});"
            f"  border: none; border-radius: 4px;"
        )
        title_row.addWidget(dot)

        lbl_title = QLabel(title)
        font = QFont()
        font.setPixelSize(13)
        font.setBold(True)
        lbl_title.setFont(font)
        lbl_title.setStyleSheet(f"color: #334155; background: transparent;")
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        layout.addLayout(title_row)

        layout.addSpacing(10)

        # body
        lbl_body = QLabel(body)
        lbl_body.setWordWrap(True)
        lbl_body.setTextFormat(Qt.PlainText)
        if is_original:
            lbl_body.setStyleSheet(
                "color: #475569; font-size: 14px;"
                "background: #F1F5F9;"
                "border: 1px solid #E2E8F0; border-radius: 8px;"
                "padding: 12px 14px; line-height: 1.8;"
            )
        else:
            lbl_body.setStyleSheet(
                "color: #1E293B; font-size: 14px; background: transparent;"
                "padding: 0 4px; line-height: 1.8;"
            )
        layout.addWidget(lbl_body)

    @staticmethod
    def _split_sections(text: str):
        pattern = r"【(.+?)】\s*"
        parts = re.split(pattern, text)
        result = []
        i = 0
        while i < len(parts):
            chunk = parts[i].strip()
            if not chunk:
                i += 1
                continue
            if i + 1 < len(parts) and not parts[i + 1].strip():
                i += 2
                continue
            if re.match(r'[一-鿿\w]+', chunk) and i + 1 < len(parts):
                result.append((chunk, parts[i + 1].strip()))
                i += 2
            else:
                i += 1
        if not result:
            result.append(("翻译结果", text))
        return result

    def _clamp_size(self, scroll: QScrollArea):
        content = scroll.widget()
        # set scroll area width first so word-wrapped labels compute correct height
        scroll.setFixedWidth(_MAX_WIDTH)
        content.adjustSize()
        ch = content.sizeHint().height() + 8
        bh = min(ch, _MAX_HEIGHT)
        scroll.setFixedHeight(bh)
        scroll.setMaximumHeight(_MAX_HEIGHT)
        self.setFixedWidth(_MAX_WIDTH + 16)

        header_h = 56
        footer_h = 58
        total_h = header_h + bh + footer_h + 16
        self.setFixedHeight(min(total_h, header_h + _MAX_HEIGHT + footer_h + 16))

    # -- actions ---------------------------------------------------------------

    def _copy_text(self):
        pyperclip.copy(self._translated)
        self._btn_copy.setText("  已复制!")
        self._btn_copy.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #34D399, stop:1 #10B981);"
            "  border: none; border-radius: 17px;"
            "  padding: 0 20px; font-size: 12px; color: #fff; font-weight: 600;"
            "}"
        )
        QTimer.singleShot(1500, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self._btn_copy.setText("  复制译文")
        self._btn_copy.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #8B5CF6, stop:1 #7C3AED);"
            "  border: none; border-radius: 17px;"
            "  padding: 0 20px; font-size: 12px; color: #fff; font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #9B6DF7, stop:1 #8B5CF6);"
            "}"
            "QPushButton:pressed {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #7C3AED, stop:1 #6D28D9);"
            "}"
        )

    def follow(self, pet_rect: QRect):
        self._pet_rect = pet_rect
        self._position_near(pet_rect)

    def _position_near(self, pet_rect: QRect):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        bw = self.width()
        bh = self.height()

        x = pet_rect.center().x() - bw // 2
        y = pet_rect.top() - bh - 6

        if x < screen.left() + 4:
            x = screen.left() + 4
        if x + bw > screen.right() - 4:
            x = screen.right() - bw - 4
        if y < screen.top() + 4:
            y = pet_rect.bottom() + 6

        self.move(x, y)
        self._slide_start_y = y

    # -- paint -----------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = QRectF(self.rect()).adjusted(8, 8, -8, -8)

        # outer soft shadow
        shadow1 = QPainterPath()
        shadow1.addRoundedRect(r.translated(0, 4), _RADIUS, _RADIUS)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 22))
        painter.drawPath(shadow1)

        # tighter shadow
        shadow2 = QPainterPath()
        shadow2.addRoundedRect(r.translated(0, 2), _RADIUS, _RADIUS)
        painter.setBrush(QColor(0, 0, 0, 12))
        painter.drawPath(shadow2)

        # card background with subtle gradient
        card_path = QPainterPath()
        card_path.addRoundedRect(r, _RADIUS, _RADIUS)
        card_grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        card_grad.setColorAt(0.0, QColor(255, 252, 255))
        card_grad.setColorAt(1.0, QColor(255, 255, 255))
        painter.setBrush(card_grad)
        painter.setPen(QPen(QColor(0, 0, 0, 10), 1))
        painter.drawPath(card_path)

        # claymorphism inner top highlight
        hl_rect = QRectF(r.left() + 3, r.top() + 2, r.width() - 6, r.height() * 0.3)
        hl_path = QPainterPath()
        hl_path.addRoundedRect(hl_rect, _RADIUS - 2, _RADIUS - 2)
        hl_grad = QLinearGradient(hl_rect.topLeft(), hl_rect.bottomLeft())
        hl_grad.setColorAt(0.0, QColor(255, 255, 255, 100))
        hl_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(hl_grad)
        painter.setPen(Qt.NoPen)
        painter.drawPath(hl_path)
