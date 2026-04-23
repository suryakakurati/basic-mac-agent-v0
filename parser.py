"""
Command parser module for basic-mac-agent-v0.
Handles filtering redundant commands and executing parsed output.
"""

import time
from context import get_running_apps, get_open_tabs, get_spotify_track
from actions import open_app, open_browser_tab, play_spotify, open_folder, run_terminal_command, close_app, set_volume


def filter_redundant_commands(llm_output: str) -> str:
    """
    Remove commands that are redundant given the current Mac state.
    - Skips apps already running from Open App lines
    - Skips tabs already open from Open Tab lines
    - Skips Play command if Spotify is already playing
    Falls back gracefully if context gathering fails.
    """
    try:
        running_apps = [a.lower() for a in get_running_apps()]
        open_tabs = [t.lower() for t in get_open_tabs()]
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