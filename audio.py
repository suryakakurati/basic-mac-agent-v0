"""
Audio recording and transcription module for basic-mac-agent-v0.
Handles microphone input, Whisper transcription, and processing.
"""

import numpy as np
import sounddevice as sd
import mlx_whisper as whisper
import threading
from config import WHISPER_MODEL, SAMPLE_RATE
from llm import query_llm
from parser import filter_redundant_commands, parse_and_execute

# ── WHISPER SETUP ─────────────────────────────────────────────────────────────

print("Loading Whisper model...")
# _whisper_model = whisper.load_model(WHISPER_MODEL)
print("Whisper ready.")

# ── AUDIO RECORDING ───────────────────────────────────────────────────────────

_recording = False
_audio_chunks = []
_stream = None


def _audio_callback(indata, frames, time_info, status):
    """sounddevice callback — appends incoming audio to buffer."""
    if _recording:
        _audio_chunks.append(indata.copy())


def start_recording():
    """Begin capturing microphone audio."""
    global _recording, _audio_chunks, _stream
    _recording = True
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
        result = whisper.transcribe(audio, path_or_hf_repo=WHISPER_MODEL)
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


def is_recording() -> bool:
    """Check if currently recording."""
    return _recording


def request_recording_start():
    """Request to start recording. Returns True if started, False if already recording."""
    global _recording
    if not _recording:
        _recording = True
        start_recording()
        return True
    return False


def request_recording_stop():
    """Request to stop recording and process. Returns True if stopped, False if not recording."""
    global _recording
    if _recording:
        stop_recording_and_process()
        return True
    return False