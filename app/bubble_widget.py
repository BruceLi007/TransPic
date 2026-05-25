import re

import pyperclip
from PySide6.QtCore import Qt, QRect, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QGuiApplication, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy,
)

_MAX_WIDTH = 500
_MAX_HEIGHT = 480
_MARGIN = 18
_RADIUS = 12

# accent colors for left bar
_ACCENT = {
    "原文": "#c0c0c0",
    "标准中文翻译": "#4a6cf7",
    "考研重点词汇解析": "#f59e0b",
    "翻译结果": "#4a6cf7",
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

        self._setup_ui()
        self._position_near(pet_rect)

    # -- layout ----------------------------------------------------------------

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("card")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header — title + close button
        hdr = QHBoxLayout()
        hdr.setContentsMargins(_MARGIN, 14, _MARGIN - 4, 10)
        title = QLabel("TransPic")
        title.setStyleSheet("color: #999; font-size: 11px; font-weight: bold; letter-spacing: 1px; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #999; font-size: 16px; }"
            "QPushButton:hover { color: #333; }"
        )
        btn_close.clicked.connect(self.closed.emit)
        hdr.addWidget(btn_close)
        layout.addLayout(hdr)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 5px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical { background: #d0d0d0; border-radius: 2px; min-height: 24px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        body = QFrame()
        body.setStyleSheet("background: transparent; border: none;")
        inner = QVBoxLayout(body)
        inner.setContentsMargins(_MARGIN, 0, _MARGIN, _MARGIN)
        inner.setSpacing(0)

        self._build_sections(inner)

        scroll.setWidget(body)
        layout.addWidget(scroll)

        self._clamp_size(scroll)

        # footer — copy button
        ft = QHBoxLayout()
        ft.setContentsMargins(_MARGIN, 6, _MARGIN, 14)
        ft.addStretch()
        btn_copy = QPushButton("复制译文")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setFixedHeight(30)
        btn_copy.setStyleSheet(
            "QPushButton {"
            "  background: #f0f3ff; border: 1px solid #d4dafc; border-radius: 6px;"
            "  padding: 0 16px; font-size: 12px; color: #4a6cf7;"
            "}"
            "QPushButton:hover { background: #e4e9fe; }"
        )
        btn_copy.clicked.connect(self._copy_text)
        ft.addWidget(btn_copy)
        layout.addLayout(ft)

        # card styling via paintEvent now
        self._card = card

        outer.addWidget(card)

    def _build_sections(self, layout: QVBoxLayout):
        # 【原文】
        self._add_section(layout, "原文", self._original, is_original=True)

        sections = self._split_sections(self._translated)
        for title, body in sections:
            self._add_section(layout, title, body)

    def _add_section(self, layout: QVBoxLayout, title: str, body: str, is_original: bool = False):
        accent = _ACCENT.get(title, "#888")

        # section row: accent bar + title
        layout.addSpacing(14)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        bar = QFrame()
        bar.setFixedSize(3, 16)
        bar.setStyleSheet(f"background: {accent}; border: none; border-radius: 1px;")
        title_row.addWidget(bar)

        lbl_title = QLabel(title)
        font = QFont()
        font.setPixelSize(13)
        font.setBold(True)
        lbl_title.setFont(font)
        lbl_title.setStyleSheet(f"color: #333; background: transparent;")
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        layout.addLayout(title_row)

        layout.addSpacing(8)

        # body
        lbl_body = QLabel(body)
        lbl_body.setWordWrap(True)
        lbl_body.setTextFormat(Qt.PlainText)
        if is_original:
            lbl_body.setStyleSheet(
                "color: #666; font-size: 13px; background: #f5f5f5;"
                "border: none; border-radius: 6px; padding: 10px 12px;"
                "line-height: 1.7;"
            )
        else:
            lbl_body.setStyleSheet(
                "color: #1a1a1a; font-size: 13px; background: transparent;"
                "padding: 0 4px; line-height: 1.7;"
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
        content.adjustSize()
        cw = content.sizeHint().width() + 4
        ch = content.sizeHint().height() + 4
        bw = min(cw, _MAX_WIDTH)
        bh = min(ch, _MAX_HEIGHT)
        scroll.setMinimumWidth(bw)
        scroll.setMaximumWidth(_MAX_WIDTH)
        scroll.setMinimumHeight(min(bh, _MAX_HEIGHT))
        scroll.setMaximumHeight(_MAX_HEIGHT)
        self.setFixedWidth(bw + 12)

        # total height = card height + shadow margin
        header_h = 52
        footer_h = 50
        self.setMaximumHeight(header_h + bh + footer_h + 12)

    # -- actions ---------------------------------------------------------------

    def _copy_text(self):
        pyperclip.copy(self._translated)

    def follow(self, pet_rect: QRect):
        self._pet_rect = pet_rect
        self._position_near(pet_rect)

    def _position_near(self, pet_rect: QRect):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        bw = self.width()
        bh = self.height()

        x = pet_rect.center().x() - bw // 2
        y = pet_rect.top() - bh + 2

        if x < screen.left():
            x = screen.left() + 4
        if x + bw > screen.right():
            x = screen.right() - bw - 4
        if y < screen.top():
            y = pet_rect.bottom() + 4

        self.move(x, y)

    # -- paint -----------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)

        # shadow
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(r.translated(0, 2), _RADIUS, _RADIUS)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 18))
        painter.drawPath(shadow_path)

        # card background
        card_path = QPainterPath()
        card_path.addRoundedRect(r, _RADIUS, _RADIUS)
        painter.setBrush(QColor(255, 255, 255, 250))
        painter.setPen(QPen(QColor(0, 0, 0, 15), 1))
        painter.drawPath(card_path)
