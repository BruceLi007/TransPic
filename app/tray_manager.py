from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QWidget


def _make_icon() -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(255, 180, 130))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(4, 4, 24, 24, 8, 8)
    p.setBrush(Qt.white)
    p.drawEllipse(10, 10, 5, 6)
    p.drawEllipse(19, 10, 5, 6)
    p.setBrush(QColor(50, 50, 50))
    p.drawEllipse(10, 11, 3, 4)
    p.drawEllipse(19, 11, 3, 4)
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
        action_settings = menu.addAction("设置")
        action_settings.triggered.connect(self.show_settings.emit)
        menu.addSeparator()
        action_exit = menu.addAction("退出")
        action_exit.triggered.connect(self.exit_app.emit)

        self._tray.setContextMenu(menu)
        self._tray.show()

    def show_message(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)
