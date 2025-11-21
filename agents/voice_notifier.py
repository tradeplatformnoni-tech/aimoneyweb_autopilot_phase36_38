#!/usr/bin/env python3
import os
import platform
import subprocess
import sys
import tempfile

from gtts import gTTS
from playsound3 import playsound


def speak(text: str):
    """Speak a short text message via system voice or gTTS."""
    try:
        # Fast native voice (macOS)
        if platform.system() == "Darwin":
            subprocess.run(["say", text], check=False)
            return
        # Fallback to gTTS + playsound3
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        gTTS(text=text).save(tmp.name)
        playsound(tmp.name)
        os.unlink(tmp.name)
    except Exception as e:
        print(f"[voice] WARN: {e}", file=sys.stderr)


if __name__ == "__main__":
    speak("NeoLight voice notifier active and ready.")
