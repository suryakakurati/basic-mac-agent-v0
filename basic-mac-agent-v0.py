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

import subprocess
import threading
import requests
import time
import numpy as np
import sounddevice as sd
import whisper

from pynput import keyboard
from AppKit import (
    NSApplication, NSApp,
    NSApplicationActivationPolicyAccessory
)
from Foundation import NSObject
# from objc import super as objc_super  # unused import


# ── CONFIG ────────────────────────────────────────────────────────────────────

# LLM backend: "ollama" | "gemini"
LLM_BACKEND     = "ollama"

# Ollama settings (local, unlimited, no API key needed)
# OLLAMA_MODEL    = "llama3.2"
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_URL      = "http://localhost:11434/api/generate"

# Gemini settings (cloud, free tier with rate limits)
GEMINI_API_KEY  = "YOUR_GEMINI_API_KEY_HERE"
GEMINI_MODEL    = "gemini-3.1-flash-lite-preview"
GEMINI_URL      = "https://generativelanguage.googleapis.com/v1beta/models"

# Audio / transcription settings
WHISPER_MODEL   = "base"        # tiny | base | small
SAMPLE_RATE     = 16000         # Hz, required by Whisper

# Input settings
HOLD_KEY        = keyboard.Key.shift_r  # hold to record

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a command parser for a personal Mac assistant.
Convert the user's request into ONLY the exact commands needed. Do exactly what is asked — nothing more.

Available command types:
Open App: <AppName1>, <AppName2>
Open Tab: <url1>, <url2>
Play: <playlist or song name>
Open Folder: <path>
Run Terminal: <shell command>
Close App: <AppName>
Set Volume: <0-100>

Rules:
1. Output ONLY command lines, nothing else — no explanations, no markdown, no extra text
2. Use EXACT format shown above
3. For the browser always use "Opera GX"
4. For VS Code use "Visual Studio Code"
5. If the user gives a direct command like "open X" or "close X", do ONLY that — nothing extra.
6. If the user gives a vague or contextual request like "I want to study" or "help me learn X", infer the most useful set of commands to help them.
7. Only use Play: if the user explicitly asks to play something.

Example input: open Spotify
Example output:
Open App: Spotify

Example input: open youtube in browser
Example output:
Open App: Opera GX
Open Tab: youtube.com

Example input: I want to study
Example output:
Open App: Opera GX, Spotify
Play: Lofi Study Playlist
Open Tab: claude.ai, chatgpt.com, webcourses.ucf.edu

Example input: coding time
Example output:
Open App: Visual Studio Code, Spotify
Play: Coding Focus Playlist
Open Tab: github.com, stackoverflow.com

Example input: I need help learning AC Circuits in Physics
Example output:
Open App: Opera GX
Open Tab: claude.ai, https://www.youtube.com/results?search_query=AC+Circuits

Example input: close Spotify
Example output:
Close App: Spotify"""


# ── WHISPER SETUP ─────────────────────────────────────────────────────────────

print("Loading Whisper model...")
_whisper_model = whisper.load_model(WHISPER_MODEL)
print("Whisper ready.")


# ── CONTEXT AWARENESS ────────────────────────────────────────────────────────

def get_running_apps() -> list[str]:
    """Return names of all currently running macOS applications."""
    script = 'tell application "System Events" to get name of every process whose background only is false'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [a.strip() for a in result.stdout.strip().split(",") if a.strip()]


def get_open_tabs() -> list[str]:
    """Return URLs of all open tabs in Opera GX, or empty list if not running."""
    script = '''
        tell application "System Events"
            if exists process "Opera GX" then
                tell application "Opera GX"
                    set tabList to {}
                    repeat with w in windows
                        repeat with t in tabs of w
                            set end of tabList to URL of t
                        end repeat
                    end repeat
                    return tabList
                end tell
            end if
        end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return [u.strip() for u in result.stdout.strip().split(",") if u.strip()]


def get_spotify_track() -> str:
    """Return currently playing Spotify track as 'Artist - Track', or empty string."""
    script = '''
        tell application "System Events"
            if exists process "Spotify" then
                tell application "Spotify"
                    if player state is playing then
                        return artist of current track & " - " & name of current track
                    end if
                end tell
            end if
        end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


# ── LLM BACKENDS ─────────────────────────────────────────────────────────────

def query_ollama(user_input: str) -> str:
    """Send prompt to local Ollama instance and return response text."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + "\n\nUser: " + user_input,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=30)
        data = res.json()
        return data["response"].strip()
    except Exception as e:
        return f"ERROR: {e}"


def query_gemini(user_input: str) -> str:
    """Send prompt to Gemini API and return response text."""
    url = f"{GEMINI_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\nUser: " + user_input}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 300}
    }
    try:
        res = requests.post(url, json=payload, timeout=30)
        data = res.json()

        if "error" in data:
            print(f"Gemini API error: {data['error']['message']}")
            return f"ERROR: {data['error']['message']}"

        if "candidates" not in data or not data["candidates"]:
            print("Gemini: no candidates returned (safety filter or empty response)")
            return "ERROR: No candidates returned."

        candidate = data["candidates"][0]
        if "content" in candidate and "parts" in candidate["content"]:
            parts = candidate["content"]["parts"]
            text = next((p["text"] for p in parts if "text" in p and "thoughtSignature" not in p), "")
            return text.strip()

        return "ERROR: Unexpected response format."

    except Exception as e:
        return f"ERROR: {e}"


def query_llm(user_input: str) -> str:
    """Route to the configured LLM backend."""
    if LLM_BACKEND == "ollama":
        return query_ollama(user_input)
    elif LLM_BACKEND == "gemini":
        return query_gemini(user_input)
    else:
        return f"ERROR: Unknown LLM backend '{LLM_BACKEND}'"


# ── MACOS ACTIONS ─────────────────────────────────────────────────────────────

def run_apple_script(script: str):
    """Execute an AppleScript string."""
    subprocess.run(["osascript", "-e", script])


def open_app(app_name: str):
    """Bring a macOS application to the foreground."""
    run_apple_script(f'tell application "{app_name}" to activate')


def open_browser_tab(url: str):
    """Open a URL in a new Opera GX tab."""
    if not url.startswith("http"):
        url = "https://" + url
    run_apple_script('tell application "Opera GX" to activate')
    time.sleep(0.5)
    run_apple_script(f'''
        tell application "Opera GX"
            tell front window
                set newTab to make new tab
                set URL of newTab to "{url}"
            end tell
        end tell
    ''')


def play_spotify(query: str):
    """Search for a track or playlist in Spotify."""
    run_apple_script('tell application "Spotify" to activate')
    time.sleep(1)
    search_query = query.replace(" ", "%20")
    subprocess.run(["open", f"spotify:search:{search_query}"], capture_output=True)


def open_folder(path: str):
    """Open a folder in Finder."""
    subprocess.run(["open", path], capture_output=True)


def run_terminal_command(command: str):
    """Open Terminal and run a shell command."""
    run_apple_script(f'''
        tell application "Terminal"
            activate
            do script "{command}"
        end tell
    ''')


def close_app(app_name: str):
    """Quit a macOS application."""
    run_apple_script(f'tell application "{app_name}" to quit')


def set_volume(level: str):
    """Set system output volume (0–100)."""
    try:
        vol = max(0, min(100, int(level.strip())))
        run_apple_script(f"set volume output volume {vol}")
    except ValueError:
        pass


# ── COMMAND PARSER ────────────────────────────────────────────────────────────

def filter_redundant_commands(llm_output: str) -> str:
    """
    Remove commands that are redundant given the current Mac state.
    - Skips apps already running from Open App lines
    - Skips tabs already open from Open Tab lines
    - Skips Play command if Spotify is already playing
    Falls back gracefully if context gathering fails.
    """
    try:
        running_apps  = [a.lower() for a in get_running_apps()]
        open_tabs     = [t.lower() for t in get_open_tabs()]
        current_track = get_spotify_track()
    except Exception:
        return llm_output

    filtered_lines = []

    for line in llm_output.strip().splitlines():
        stripped = line.strip()

        if stripped.startswith("Open App:"):
            remaining = [
                app for app in stripped[len("Open App:"):].split(",")
                if app.strip().lower() not in running_apps
            ]
            if remaining:
                filtered_lines.append("Open App: " + ", ".join(a.strip() for a in remaining))
            else:
                print(f"CONTEXT FILTER: skipped '{stripped}' — all apps already open")

        elif stripped.startswith("Open Tab:"):
            remaining = [
                url for url in stripped[len("Open Tab:"):].split(",")
                if not any(url.strip().lower().replace("https://", "").replace("http://", "") in t for t in open_tabs)
            ]
            if remaining:
                filtered_lines.append("Open Tab: " + ", ".join(u.strip() for u in remaining))
            else:
                print(f"CONTEXT FILTER: skipped '{stripped}' — all tabs already open")

        elif stripped.startswith("Play:"):
            if current_track:
                print(f"CONTEXT FILTER: skipped '{stripped}' — Spotify already playing: {current_track}")
            else:
                filtered_lines.append(stripped)

        else:
            filtered_lines.append(stripped)

    return "\n".join(filtered_lines)


def parse_and_execute(llm_output: str):
    """
    Parse structured LLM output and dispatch to macOS action handlers.
    Each line must match one of the defined command prefixes.
    """
    print("LLM OUTPUT:", llm_output)
    lines = llm_output.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Open App:"):
            apps = line[len("Open App:"):].split(",")
            for app in apps:
                open_app(app.strip())

        elif line.startswith("Open Tab:"):
            open_app("Opera GX")
            time.sleep(6)
            urls = line[len("Open Tab:"):].split(",")
            for url in urls:
                open_browser_tab(url.strip())
                time.sleep(0.5)

        elif line.startswith("Play:"):
            query = line[len("Play:"):].strip()
            play_spotify(query)

        elif line.startswith("Open Folder:"):
            path = line[len("Open Folder:"):].strip()
            open_folder(path)

        elif line.startswith("Run Terminal:"):
            # command = line[len("Run Terminal:"):].strip()
            # run_terminal_command(command) 
            # no safe handling implemented here. will come in later version.
            return

        elif line.startswith("Close App:"):
            apps = line[len("Close App:"):].split(",")
            for app in apps:
                close_app(app.strip())

        elif line.startswith("Set Volume:"):
            level = line[len("Set Volume:"):].strip()
            set_volume(level)


# ── AUDIO RECORDING ───────────────────────────────────────────────────────────

_recording    = False
_audio_chunks = []
_stream       = None


def _audio_callback(indata, frames, time_info, status):
    """sounddevice callback — appends incoming audio to buffer."""
    if _recording:
        _audio_chunks.append(indata.copy())


def start_recording():
    """Begin capturing microphone audio."""
    global _recording, _audio_chunks, _stream
    _recording    = True
    _audio_chunks = []
    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        callback=_audio_callback
    )
    _stream.start()
    print("Recording...")

    # Safety timeout — auto stop after 10 seconds if key release is missed
    def _timeout():
        if _recording:
            print("Recording timeout — auto stopping")
            stop_recording_and_process()
    threading.Timer(10.0, _timeout).start()


def stop_recording_and_process():
    """
    Stop microphone capture, transcribe audio with Whisper,
    send transcript to LLM, then execute returned commands.
    """
    global _recording, _stream
    _recording = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None

    if not _audio_chunks:
        return

    audio = np.concatenate(_audio_chunks, axis=0).flatten()

    def process():
        # Step 1: transcribe
        result = _whisper_model.transcribe(audio, fp16=False)
        transcript = result["text"].strip()
        print("HEARD:", transcript)

        if not transcript:
            return

        # Step 2: parse intent
        llm_output = query_llm(transcript)
        print("GOT OUTPUT:", llm_output)

        if llm_output.startswith("ERROR:"):
            return

        # Step 3: filter redundant commands using current context
        llm_output = filter_redundant_commands(llm_output)

        # Step 4: execute commands
        parse_and_execute(llm_output)

    threading.Thread(target=process, daemon=True).start()


# ── KEYBOARD LISTENER ─────────────────────────────────────────────────────────

def on_key_press(key):
    global _recording
    if key == HOLD_KEY and not _recording:
        _recording = True
        start_recording()


def on_key_release(key):
    if key == HOLD_KEY and _recording:
        stop_recording_and_process()


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