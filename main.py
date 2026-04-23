#!/usr/bin/env python3
"""
Basic Mac Agent V0 - Voice Activated Mac Assistant
Hold right shift → speak → release → Whisper transcribes → LLM → macOS actions

Architecture:
  - Audio recording via sounddevice
  - Transcription via local Whisper model
  - Context awareness via AppleScript (apps, tabs, Spotify)
  - Intent parsing via Ollama (local) or Gemini API (cloud)
  - macOS automation via AppleScript / subprocess
"""

import threading
from pynput import keyboard
from AppKit import (
    NSApplication, NSApp,
    NSApplicationActivationPolicyAccessory
)
from Foundation import NSObject
from config import HOLD_KEY
from audio import request_recording_start, request_recording_stop

# ── KEYBOARD LISTENER ─────────────────────────────────────────────────────────

def on_key_press(key):
    if key == HOLD_KEY:
        request_recording_start()


def on_key_release(key):
    if key == HOLD_KEY:
        request_recording_stop()


_kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)


# ── APP DELEGATE ──────────────────────────────────────────────────────────────

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        NSApp.activateIgnoringOtherApps_(True)


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _kb_listener.start()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()