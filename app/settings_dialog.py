from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QLabel, QFrame,
)

from utils.config import AppConfig


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TransPic 设置")
        self.setFixedSize(480, 420)
        self.setStyleSheet("QDialog { background: #fff; }")
        self._config = config
        self._result_config = None
        self._setup_ui()
        self._load_config()

    def _input_style(self):
        return (
            "QLineEdit {"
            "  border: 1px solid #E2E8F0; border-radius: 8px;"
            "  padding: 10px 14px; font-size: 13px;"
            "  background: #F8FAFC; color: #1E293B;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #A78BFA; background: #fff;"
            "  box-shadow: 0 0 0 3px rgba(124,58,237,0.1);"
            "}"
        )

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(0)

        # title
        title = QLabel("TransPic 设置")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #1E293B;"
            "padding-bottom: 4px;"
        )
        layout.addWidget(title)

        subtitle = QLabel("配置 API 连接和快捷键")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 12px; padding-bottom: 18px;")
        layout.addWidget(subtitle)

        # separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #E2E8F0; border: none; max-height: 1px;")
        layout.addWidget(sep)
        layout.addSpacing(20)

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setContentsMargins(0, 0, 0, 0)

        label_style = "color: #475569; font-size: 13px; font-weight: 500;"

        # API Endpoint
        self._endpoint = QLineEdit()
        self._endpoint.setPlaceholderText("https://api.openai.com/v1")
        self._endpoint.setStyleSheet(self._input_style())
        lbl = QLabel("Endpoint")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self._endpoint)

        # API Key
        self._api_key = QLineEdit()
        self._api_key.setPlaceholderText("sk-...")
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setStyleSheet(self._input_style())
        lbl = QLabel("API Key")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self._api_key)

        # Model
        self._model = QLineEdit()
        self._model.setPlaceholderText("gpt-4o / Qwen/Qwen3-VL-8B-Instruct")
        self._model.setStyleSheet(self._input_style())
        lbl = QLabel("Model")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self._model)

        # Hotkey
        self._hotkey = QLineEdit()
        self._hotkey.setPlaceholderText("alt+shift+t")
        self._hotkey.setStyleSheet(self._input_style())
        lbl = QLabel("快捷键")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self._hotkey)

        layout.addLayout(form)
        layout.addSpacing(22)

        # hint
        hint = QLabel("支持所有 OpenAI 兼容接口 (OpenAI / DeepSeek / 硅基流动 / 通义千问 等)")
        hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addStretch()

        # buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedSize(96, 36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton {"
            "  background: #fff; border: 1px solid #E2E8F0;"
            "  border-radius: 8px; font-size: 13px; color: #64748B;"
            "}"
            "QPushButton:hover {"
            "  background: #F8FAFC; border-color: #CBD5E1; color: #475569;"
            "}"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("保存")
        btn_save.setFixedSize(96, 36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #8B5CF6, stop:1 #7C3AED);"
            "  border: none; border-radius: 8px;"
            "  font-size: 13px; color: #fff; font-weight: 600;"
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
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _load_config(self):
        self._endpoint.setText(self._config.api_endpoint)
        self._api_key.setText(self._config.api_key)
        self._model.setText(self._config.model)
        self._hotkey.setText(self._config.hotkey)

    def _on_save(self):
        endpoint = self._endpoint.text().strip().replace("\n", "")
        api_key = self._api_key.text().strip().replace("\n", "")
        model = self._model.text().strip().replace("\n", "")
        hotkey = self._hotkey.text().strip().replace("\n", "")

        if not endpoint:
            QMessageBox.warning(self, "提示", "请输入 API Endpoint")
            return
        if not api_key:
            QMessageBox.warning(self, "提示", "请输入 API Key")
            return
        if not model:
            QMessageBox.warning(self, "提示", "请输入模型名称")
            return
        if not hotkey:
            QMessageBox.warning(self, "提示", "请输入全局热键")
            return

        self._result_config = AppConfig(
            api_endpoint=endpoint,
            api_key=api_key,
            model=model,
            target_language="中文",
            hotkey=hotkey,
            window_x=self._config.window_x,
            window_y=self._config.window_y,
        )
        self.accept()

    @property
    def result_config(self) -> AppConfig | None:
        return self._result_config
