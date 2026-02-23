"""Procrastination popup using macOS-native osascript (no Tkinter dependency)."""
import subprocess


class ProcrastinationEvent:
    def show_popup(self, ai_message):
        """Native macOS dialog with the heckler message."""
        escaped = ai_message.replace('\\', '\\\\').replace('"', '\\"')
        subprocess.Popen([
            "osascript", "-e",
            f'display dialog "{escaped}" with title "ProctorAI" buttons {{"OK"}} default button "OK" with icon caution giving up after 30'
        ])


if __name__ == "__main__":
    ProcrastinationEvent().show_popup("You are procrastinating. Please focus on your work.")
