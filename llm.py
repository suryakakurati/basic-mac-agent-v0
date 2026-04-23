"""
LLM integration module for basic-mac-agent-v0.
Handles queries to Ollama and Gemini backends.
"""

import requests
from config import (
    LLM_BACKEND,
    OLLAMA_MODEL,
    OLLAMA_URL,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_URL,
    SYSTEM_PROMPT,
)


def query_ollama(user_input: str) -> str:
    """Send prompt to local Ollama instance and return response text."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": SYSTEM_PROMPT + "\n\nUser: " + user_input,
        "stream": False,
        "options": {"temperature": 0.1},
        "keep_alive": "2m"
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