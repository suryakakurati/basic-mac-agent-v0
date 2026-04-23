"""
Context awareness module for basic-mac-agent-v0.
Functions to query current macOS state (apps, tabs, Spotify).
"""

import subprocess


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