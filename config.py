"""
Configuration module for basic-mac-agent-v0.
Contains all configurable settings and constants.
"""

from pynput import keyboard

# ── CONFIG ────────────────────────────────────────────────────────────────────

# LLM backend: "ollama" | "gemini"
LLM_BACKEND = "ollama"

# Ollama settings (local, unlimited, no API key needed)
# OLLAMA_MODEL    = "llama3.2"
OLLAMA_MODEL = "qwen2.5:7b-instruct"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Gemini settings (cloud, free tier with rate limits)
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Audio / transcription settings
WHISPER_MODEL = "mlx-community/whisper-base.en-mlx"
SAMPLE_RATE = 16000  # Hz, required by Whisper

# Input settings
HOLD_KEY = keyboard.Key.shift_r  # hold to record

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