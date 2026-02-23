"""Procrastination popup using macOS-native osascript (no Tkinter dependency)."""
import subprocess
import time


class ProcrastinationEvent:
    def show_popup(self, ai_message):
        """Full-screen-ish native macOS dialog with the heckler message."""
        escaped = ai_message.replace('\\', '\\\\').replace('"', '\\"')
        subprocess.Popen([
            "osascript", "-e",
            f'display dialog "{escaped}" with title "ProctorAI" buttons {{"OK"}} default button "OK" with icon caution giving up after 30'
        ])

    def play_countdown(self, count, brief_message="Get back to work!"):
        """Show a macOS notification with countdown, then a final alert."""
        subprocess.run([
            "terminal-notifier",
            "-title", "ProctorAI",
            "-message", f"{brief_message} — {count}s",
            "-sound", "Sosumi",
        ], capture_output=True)


if __name__ == "__main__":
    p = ProcrastinationEvent()
    p.show_popup("You are procrastinating. Please focus on your work.")
    p.play_countdown(10)
