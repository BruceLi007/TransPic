from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap, QPen, QRadialGradient
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget


def _make_icon() -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # body — warm peach rounded rect
    body_grad = QRadialGradient(16, 18, 14)
    body_grad.setColorAt(0.0, QColor(255, 200, 160))
    body_grad.setColorAt(1.0, QColor(255, 175, 130))
    p.setBrush(body_grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(3, 5, 26, 24, 10, 10)

    # ears
    p.setBrush(QColor(255, 185, 140))
    p.drawRoundedRect(4, 1, 8, 9, 4, 4)
    p.drawRoundedRect(20, 1, 8, 9, 4, 4)

    # eyes — white sclera
    p.setBrush(QColor(255, 255, 255))
    p.setPen(QPen(QColor(210, 190, 180), 0.5))
    p.drawEllipse(9, 11, 6, 7)
    p.drawEllipse(19, 11, 6, 7)

    # pupils
    p.setBrush(QColor(55, 40, 30))
    p.setPen(Qt.NoPen)
    p.drawEllipse(11, 13, 3.5, 4)
    p.drawEllipse(21, 13, 3.5, 4)

    # highlights
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(12, 11.5, 1.8, 1.5)
    p.drawEllipse(22, 11.5, 1.8, 1.5)

    # blush
    p.setBrush(QColor(255, 150, 150, 80))
    p.drawEllipse(5, 18, 4, 3)
    p.drawEllipse(23, 18, 4, 3)

    # mouth — small purple accent dot (like a tiny speech indicator)
    p.setBrush(QColor(124, 58, 237, 180))
    p.drawEllipse(14, 21, 4, 3)

    p.end()
    return QIcon(pm)


class TrayManager(QWidget):
    show_settings = Signal()
    exit_app = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(_make_icon(), self)
        self._tray.setToolTip("TransPic - 截图翻译")

        menu = QMenu()
        menu.setStyleSheet(
            "QMenu {"
            "  background: #fff; border: 1px solid #E2E8F0;"
            "  border-radius: 8px; padding: 4px;"
            "}"
            "QMenu::item {"
            "  padding: 6px 24px; border-radius: 4px;"
            "  font-size: 12px; color: #475569;"
            "}"
            "QMenu::item:selected { background: #F1F5F9; color: #1E293B; }"
            "QMenu::separator {"
            "  height: 1px; background: #E2E8F0; margin: 4px 12px;"
            "}"
        )
        action_settings = menu.addAction("设置")
        action_settings.triggered.connect(self.show_settings.emit)
        menu.addSeparator()
        action_exit = menu.addAction("退出")
        action_exit.triggered.connect(self.exit_app.emit)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def show_message(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)
