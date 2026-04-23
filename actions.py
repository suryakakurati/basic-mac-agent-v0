"""
macOS actions module for basic-mac-agent-v0.
Functions to execute commands via AppleScript and subprocess.
"""

import subprocess
import time


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