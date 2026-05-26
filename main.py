import sys

import keyboard
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import QApplication

from utils.config import load_config, save_config
from app.pet_widget import PetWidget
from app.screenshot_overlay import ScreenshotOverlay
from app.bubble_widget import BubbleWidget
from app.llm_client import LLMClient
from app.settings_dialog import SettingsDialog
from app.tray_manager import TrayManager


# -- hotkey bridge (keyboard callback → Qt signal) ---------------------------

class HotkeyBridge(QObject):
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self._hotkey = ""

    def start(self, hotkey: str):
        self._hotkey = hotkey
        keyboard.add_hotkey(hotkey, self.triggered.emit)

    def update(self, new_hotkey: str):
        keyboard.remove_hotkey(self._hotkey)
        self._hotkey = new_hotkey
        keyboard.add_hotkey(new_hotkey, self.triggered.emit)


# -- translation worker (background thread) -----------------------------------

class TranslationWorker(QThread):
    finished = Signal(str, str)   # original_text, translated_text
    error = Signal(str)

    def __init__(self, client: LLMClient, image, parent=None):
        super().__init__(parent)
        self.client = client
        self.image = image

    def run(self):
        try:
            raw = self.client.translate(self.image)
            orig, trans = self._parse(raw)
            self.finished.emit(orig, trans)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.image = None

    @staticmethod
    def _parse(raw: str):
        if "【原文】" in raw and "【标准中文翻译】" in raw:
            after_orig = raw.split("【原文】", 1)[1]
            if "【标准中文翻译】" in after_orig:
                parts = after_orig.split("【标准中文翻译】", 1)
                orig = parts[0].strip()
                rest = "【标准中文翻译】" + parts[1]
                return orig, rest.strip()
        if "【原文】" in raw and "【译文】" in raw:
            parts = raw.split("【译文】", 1)
            orig_part = parts[0].replace("【原文】", "").strip()
            trans_part = parts[1].strip()
            return orig_part, trans_part
        if "原文：" in raw and "译文：" in raw:
            parts = raw.split("译文：", 1)
            orig_part = parts[0].replace("原文：", "").strip()
            trans_part = parts[1].strip()
            return orig_part, trans_part
        return raw, "（模型未按指定格式返回，请重试截图翻译）\n\n原始响应:\n" + raw


# -- main controller ---------------------------------------------------------

class AppController(QObject):
    def __init__(self):
        super().__init__()
        self.config = load_config()

        # widgets
        self.pet = PetWidget()
        self.tray = TrayManager()
        self._overlay: ScreenshotOverlay | None = None
        self._bubble: BubbleWidget | None = None
        self._thread: TranslationWorker | None = None
        self._client: LLMClient | None = None

        # hotkey
        self._hotkey = HotkeyBridge()
        self._hotkey.triggered.connect(self.start_screenshot)

        self._build_client()
        self._connect_signals()
        self._restore_position()

        self.pet.show()
        self._hotkey.start(self.config.hotkey)

    # -- setup helpers -------------------------------------------------------

    def _build_client(self):
        self._client = LLMClient(
            endpoint=self.config.api_endpoint,
            api_key=self.config.api_key,
            model=self.config.model,
            target_language=self.config.target_language,
        )

    def _connect_signals(self):
        self.pet.clicked.connect(self.start_screenshot)
        self.tray.show_settings.connect(self.open_settings)
        self.tray.exit_app.connect(self.quit)

    def _restore_position(self):
        self.pet.move(self.config.window_x, self.config.window_y)

    # -- screenshot flow -----------------------------------------------------

    def start_screenshot(self):
        if self._overlay:
            return
        self.pet.hide()
        self._close_bubble()
        self._overlay = ScreenshotOverlay()
        self._overlay.region_selected.connect(self._on_region_selected)
        self._overlay.cancelled.connect(self._cancel_screenshot)
        self._overlay.show()
        self._overlay.activateWindow()
        self._overlay.raise_()

    def _on_region_selected(self, pil_image):
        self._cleanup_overlay()
        self.pet.set_thinking(True)
        self.pet.show()

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        self._thread = TranslationWorker(self._client, pil_image)
        self._thread.finished.connect(self._show_result)
        self._thread.error.connect(self._show_error)
        self._thread.start()

    def _cancel_screenshot(self):
        self._cleanup_overlay()
        self.pet.show()

    def _cleanup_overlay(self):
        if self._overlay:
            self._overlay.close()
            self._overlay.deleteLater()
            self._overlay = None

    # -- results -------------------------------------------------------------

    def _show_result(self, original: str, translated: str):
        self.pet.set_thinking(False)
        self._bubble = BubbleWidget(
            self.pet.geometry(), original, translated
        )
        self.pet.set_move_callback(self._bubble.follow)
        self._bubble.closed.connect(self._close_bubble)
        self._bubble.show()

    def _show_error(self, msg: str):
        self.pet.set_thinking(False)
        self.tray.show_message("翻译失败", msg)

    def _close_bubble(self):
        if self._bubble:
            self.pet.set_move_callback(None)
            self._bubble.close()
            self._bubble.deleteLater()
            self._bubble = None

    # -- settings ------------------------------------------------------------

    def open_settings(self):
        dlg = SettingsDialog(self.config)
        if dlg.exec() == SettingsDialog.Accepted and dlg.result_config:
            self.config = dlg.result_config
            save_config(self.config)
            self._build_client()
            self._hotkey.update(self.config.hotkey)
            self.tray.show_message("设置已保存", f"目标语言: {self.config.target_language}")

    # -- quit ----------------------------------------------------------------

    def quit(self):
        # save position
        pos = self.pet.pos()
        self.config.window_x = pos.x()
        self.config.window_y = pos.y()
        save_config(self.config)

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctrl = AppController()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
