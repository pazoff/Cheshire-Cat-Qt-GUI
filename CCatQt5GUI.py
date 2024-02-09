import sys
import asyncio
import logging
import json
import time
import cheshire_cat_api as ccat
from cheshire_cat_api.utils import Settings, WebSocketSettings
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, \
    QComboBox, QFileDialog, QCheckBox
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtCore import QObject, pyqtSignal


class CCatConnection(QObject):
    messageReceived = pyqtSignal(str)

    def __init__(self, user_id, out_queue: asyncio.Queue, ccat_url: str = "localhost", ccat_port: int = 1865) -> None:
        super().__init__()
        self.user_id = user_id
        self._out_queue = out_queue
        ws_settings = WebSocketSettings(user_id=user_id)
        ccat_settings = Settings(
            base_url=ccat_url,
            port=ccat_port,
            ws=ws_settings
        )
        self.ccat = ccat.CatClient(
            settings=ccat_settings,
            on_message=self._ccat_message_callback,
            on_open=self._on_open,
            on_close=self._on_close
        )
        self.last_interaction = time.time()

    def _ccat_message_callback(self, message: str):
        message = json.loads(message)
        message_str = json.dumps(message)
        self.messageReceived.emit(message_str)

    def _on_open(self):
        logging.info(f"WS connection with user `{self.user_id}` to CheshireCat opened")

    def _on_close(self, close_status_code: int, msg: str):
        logging.info(f"WS connection `{self.user_id}` to CheshireCat closed")

    def send(self, message: str, **kwargs):
        self.last_interaction = time.time()
        self.ccat.send(message=message, **kwargs)


class CCatQt5Gui(QWidget):
    def __init__(self, ccat_connection):
        super().__init__()
        self.title = "Cheshire Cat PyQt5 GUI"
        self.ccat_connection = ccat_connection
        self.initUI()
        self.ccat_connection.messageReceived.connect(self.update_history_field)
        self.generate_button.clicked.connect(self.disable_send_button)

    def initUI(self):
        self.setWindowTitle(self.title)
        # self.label_model = QLabel("Model:")
        # self.modelSelect = QComboBox()
        # self.modelSelect.addItems(["Google Gemini Pro"])
        self.label_Output = QLabel("History")
        self.label_Input = QLabel("Input")
        self.input_field = QTextEdit()
        self.response_field = QTextEdit()
        self.response_field.setReadOnly(True)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_history)
        self.remove_button = QPushButton("Clear")
        self.remove_button.clicked.connect(self.remove_clicked)
        self.generate_button = QPushButton("Send")
        self.generate_button.clicked.connect(self.generate)
        self.attach_layout = QHBoxLayout()
        self.label_attach = QLabel("File:")
        self.attachName = QLineEdit()
        self.browse_button = QPushButton("Select")
        self.browse_button.clicked.connect(self.open_file_dialog)
        self.attachFile = QCheckBox("Attach")
        self.searchweb = QCheckBox("Search web")
        self.search_web_checkbox = QCheckBox("Search web")
        self.search_web_checkbox.setChecked(False)
        self.attach_layout.addWidget(self.label_attach)
        self.attach_layout.addWidget(self.attachName)
        self.attach_layout.addWidget(self.browse_button)
        self.attach_layout.addWidget(self.attachFile)
        self.preset_layout = QHBoxLayout()
        self.bodyLayout = QVBoxLayout()
        self.bodyLayout.addWidget(self.label_Output)
        self.bodyLayout.addWidget(self.response_field)
        self.bodyLayout.addWidget(self.clear_button)
        self.bodyLayout.addWidget(self.label_Input)
        self.bodyLayout.addWidget(self.input_field)
        self.bodyLayout.addWidget(self.searchweb)
        self.bodyLayout.addWidget(self.remove_button)
        self.bodyLayout.addWidget(self.generate_button)
        self.mainLayout = QVBoxLayout(self)
        # self.mainLayout.addWidget(self.label_model)
        # self.mainLayout.addWidget(self.modelSelect)
        self.mainLayout.addLayout(self.preset_layout)
        self.mainLayout.addLayout(self.bodyLayout)
        self.mainLayout.addLayout(self.attach_layout)

    def clear_history(self):
        self.response_field.clear()

    def remove_clicked(self):
        self.input_field.clear()

    def open_file_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf)", options=options
        )
        if file_name:
            self.attachName.setText(file_name)

    def setPreset(self):
        pass

    def generate(self):
        input_text = self.input_field.toPlainText()
        self.ccat_connection.send(message=input_text)

    def disable_send_button(self):
        self.generate_button.setEnabled(False)

    @pyqtSlot(str)
    def update_history_field(self, message):
        try:
            message_dict = json.loads(message)
            content = message_dict.get("content", "")
            self.response_field.append(content)
            self.generate_button.setEnabled(True)
        except json.JSONDecodeError:
            print("Failed to decode JSON message:", message)


class MyTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(False)
        self.setViewportMargins(0, 0, 0, 0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            self.parent().generate()
        else:
            super().keyPressEvent(event)


def cleanup():
    app.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    out_queue = asyncio.Queue()
    ccat_connection = CCatConnection(user_id="user1", out_queue=out_queue)
    window = CCatQt5Gui(ccat_connection)
    window.show()
    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec_())
