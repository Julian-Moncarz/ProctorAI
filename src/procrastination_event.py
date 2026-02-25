"""Procrastination popup using macOS-native osascript (no Tkinter dependency)."""
import os
import subprocess

# Comma-separated phone numbers, e.g. "+18259944773,+11234567890"
SHAME_CONTACTS = [n.strip() for n in os.environ.get("PROCTOR_SHAME_CONTACTS", "").split(",") if n.strip()]


class ProcrastinationEvent:
    def show_popup(self, ai_message):
        """Native macOS dialog with the heckler message."""
        escaped = ai_message.replace('\\', '\\\\').replace('"', '\\"')
        subprocess.Popen([
            "osascript", "-e",
            f'display dialog "{escaped}" with title "ProctorAI" buttons {{"OK"}} default button "OK" with icon caution giving up after 30'
        ])
        self._send_shame_texts(ai_message)

    def _send_shame_texts(self, ai_message):
        """Send iMessage to shame contacts via osascript."""
        if not SHAME_CONTACTS:
            return
        msg = f"🚨 ProctorAI caught me procrastinating: {ai_message}"
        escaped = msg.replace('\\', '\\\\').replace('"', '\\"')
        for number in SHAME_CONTACTS:
            try:
                result = subprocess.run([
                    "osascript", "-e",
                    f'''tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "{number}" of targetService
    send "{escaped}" to targetBuddy
end tell'''
                ], capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    print(f"Warning: shame-text to {number} failed: {result.stderr.strip()}")
            except Exception as e:
                print(f"Warning: shame-text to {number} error: {e}")


if __name__ == "__main__":
    ProcrastinationEvent().show_popup("You are procrastinating. Please focus on your work.")
