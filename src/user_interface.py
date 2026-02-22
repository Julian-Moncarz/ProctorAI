import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtWidgets import QDialog, QFormLayout, QCheckBox, QSpinBox, QComboBox, QShortcut
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QTime, QTimer, Qt, QProcess
from PyQt5.QtGui import QColor, QTextCursor, QTextCharFormat, QKeySequence
import json
import os


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.layout = QFormLayout(self)

        # tts flag
        self.tts_checkbox = QCheckBox("Enable text-to-speech")
        self.layout.addRow("TTS", self.tts_checkbox)

        # voice flag
        self.voice_combobox = QComboBox()
        self.voice_combobox.addItems(["Adam", "Arnold", "Emily", "Harry", "Josh", "Patrick"])
        self.layout.addRow("Voice", self.voice_combobox)

        # delay_time flag
        self.delay_time_spinbox = QSpinBox()
        self.delay_time_spinbox.setRange(0, 100000)
        self.layout.addRow("Delay Time", self.delay_time_spinbox)

        # countdown_time flag
        self.countdown_time_spinbox = QSpinBox()
        self.countdown_time_spinbox.setRange(0, 100)
        self.layout.addRow("Countdown Time", self.countdown_time_spinbox)

        # user_name flag
        self.user_name_lineedit = QLineEdit()
        self.user_name_lineedit.setText("Procrastinator")
        self.layout.addRow("User Name", self.user_name_lineedit)

        # OK and Cancel buttons
        self.buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addWidget(self.ok_button)
        self.buttons_layout.addWidget(self.cancel_button)

        self.layout.addRow(self.buttons_layout)

    def get_settings(self):
        return {
            "tts": self.tts_checkbox.isChecked(),
            "voice": self.voice_combobox.currentText(),
            "delay_time": self.delay_time_spinbox.value(),
            "countdown_time": self.countdown_time_spinbox.value(),
            "user_name": self.user_name_lineedit.text(),
        }


class ProcrastinationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.cur_dir = os.path.dirname(__file__)
        self.initUI()
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.process = None
        self.settings = load_settings()
        self.settings_dialog = SettingsDialog(self)
        self.apply_settings()

    def initUI(self):
        self.setWindowTitle('ProctorAI')
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()

        # Prompt label
        title = 'What are you looking to get done today?'
        self.prompt_label = QLabel(title, self)
        self.prompt_label.setFont(QFont('Arial', 24, QFont.Bold))

        self.prompt_input = QTextEdit(self)
        self.prompt_input.setFont(QFont('Arial', 16))
        self.prompt_input.setLineWrapMode(QTextEdit.WidgetWidth)
        self.prompt_input.setPlaceholderText("Type your task description here...")
        self.prompt_input.setFixedHeight(100)

        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.start_task)
        self.start_button.setFont(QFont('Arial', 16))

        # Create a shortcut for Command+Enter
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.start_button.click)

        self.settings_button = QPushButton('Settings', self)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setFont(QFont('Arial', 16))

        settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        settings_shortcut.activated.connect(self.settings_button.click)

        prompt_layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        prompt_layout.addWidget(self.prompt_label)
        prompt_layout.addWidget(self.prompt_input)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.settings_button)

        self.layout.addLayout(prompt_layout)
        self.layout.addLayout(button_layout)

        # Running screen elements (hidden initially)
        self.running_label = QLabel('Task in progress: ', self)
        self.running_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.running_label.setWordWrap(True)
        self.timer_label = QLabel('Time Elapsed: 00:00:00', self)
        self.timer_label.setFont(QFont('Arial', 16))
        self.output_display = QTextEdit(self)
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont('Arial', 14))

        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_task)

        self.layout.addWidget(self.running_label)
        self.layout.addWidget(self.timer_label)
        self.layout.addWidget(self.output_display)
        self.layout.addWidget(self.stop_button)

        self.running_label.hide()
        self.timer_label.hide()
        self.output_display.hide()
        self.stop_button.hide()

        self.setLayout(self.layout)
        self.show()

    def start_task(self, task_description=None):
        if not task_description:
            task_description = self.prompt_input.toPlainText()
        if task_description:
            if self.process:
                self.process.terminate()
                self.process.waitForFinished()

            self.running_label.setText(f"Task in progress: {task_description}")

            self.process = QProcess(self)
            arguments = ["-u", os.path.dirname(__file__) + "/main.py"]

            if self.settings["tts"]:
                arguments.append("--tts")
            arguments.extend([
                "--voice", self.settings["voice"],
                "--delay_time", str(self.settings["delay_time"]),
                "--countdown_time", str(self.settings["countdown_time"]),
                "--user_name", self.settings["user_name"],
            ])

            self.process.setProgram(sys.executable)
            self.process.setArguments(arguments)
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.start()
            self.process.write(task_description.encode() + b'\n')
            self.process.closeWriteChannel()

            if self.start_time is None:
                self.start_time = QTime.currentTime()
                self.timer.start(1000)

            # Switch to running screen
            if not self.running_label.isVisible():
                self.prompt_label.hide()
                self.prompt_input.hide()
                self.start_button.hide()
                self.settings_button.hide()
                self.running_label.show()
                self.timer_label.show()
                self.output_display.show()
                self.stop_button.show()

    def handle_stdout(self):
        output = self.process.readAllStandardOutput().data().decode()
        elapsed_time = QTime(0, 0).addSecs(self.start_time.secsTo(QTime.currentTime())).toString('hh:mm:ss')
        timestamped_output = f"{elapsed_time} - {output}"

        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        if "procrastinating" in output.lower():
            fmt.setForeground(QColor("red"))
        else:
            fmt.setForeground(QColor("green"))

        cursor.insertText(timestamped_output, fmt)
        self.output_display.setTextCursor(cursor)

    def update_timer(self):
        if self.start_time:
            elapsed_time = QTime(0, 0).secsTo(QTime.currentTime()) - QTime(0, 0).secsTo(self.start_time)
            self.timer_label.setText('Time Elapsed: ' + QTime(0, 0).addSecs(elapsed_time).toString('hh:mm:ss'))

    def stop_task(self):
        self.timer.stop()
        if self.process:
            self.process.terminate()
            self.process.waitForFinished()
        print("Stopping task")
        self.close()

    def open_settings(self):
        if self.settings_dialog.exec_():
            self.settings = self.settings_dialog.get_settings()
            save_settings(self.settings)
            print("Settings updated:", self.settings)

    def apply_settings(self):
        self.settings_dialog.tts_checkbox.setChecked(self.settings["tts"])
        self.settings_dialog.voice_combobox.setCurrentText(self.settings["voice"])
        self.settings_dialog.delay_time_spinbox.setValue(self.settings["delay_time"])
        self.settings_dialog.countdown_time_spinbox.setValue(self.settings["countdown_time"])
        self.settings_dialog.user_name_lineedit.setText(self.settings["user_name"])


def load_settings():
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    if os.path.exists(settings_file):
        with open(settings_file, "r") as file:
            return json.load(file)
    else:
        return {
            "tts": False,
            "voice": "Patrick",
            "delay_time": 0,
            "countdown_time": 15,
            "user_name": "Procrastinator",
        }


def save_settings(settings):
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    with open(settings_file, "w") as file:
        json.dump(settings, file)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.dirname(os.path.dirname(__file__)) + '/assets/icon_rounded.png'))
    app.setApplicationName('ProctorAI')
    ex = ProcrastinationApp()
    sys.exit(app.exec_())
