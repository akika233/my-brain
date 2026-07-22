"""Transcribe Contact 2 audio + English gloss + sentence structure via Gemini."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CACHE = ROOT / "transcripts-cache"

load_dotenv(REPO / ".env")
load_dotenv(REPO / "telegram-bot" / ".env")

PROMPT = """You are a Dutch B1 tutor. Listen to this Dutch audio (Contact! NT2 style dialogue/exercise).

Return ONLY JSON with this shape:
{
  "title": "short title",
  "sentences": [
    {
      "nl": "full Dutch sentence",
      "en": "natural English translation",
      "tokens": [
        {"text": "word or multiword chunk", "role": "subject|verb|object|complement|conjunction|other"}
      ]
    }
  ]
}

Rules:
- Split into clear sentences (or speaker turns if dialogue).
- tokens must reconstruct the Dutch sentence when joined with spaces (keep punctuation attached to tokens).
- role meanings:
  - subject = onderwerp
  - verb = finite verb / personal form (and separable verb particles with the verb if helpful)
  - object = lijdend/meewerkend voorwerp
  - complement = predicative / prepositional phrases / adverbs that complete meaning
  - conjunction = linking words (en, maar, omdat, dat, die, ...)
  - other = rest
- English should be accurate and simple.
- If audio is only sounds/minimal speech, still return best-effort sentences.
"""


def _gemini_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def _models() -> list[str]:
    preferred = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"
    out = []
    for m in [preferred, "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-2.0-flash"]:
        if m not in out:
            out.append(m)
    return out


def cache_path(folder: str, track: str) -> Path:
    safe_folder = re.sub(r"[^\w\- ]+", "_", folder).strip() or "audio"
    safe_track = re.sub(r"[^\w\- .]+", "_", track).strip() or "track"
    return CACHE / safe_folder / (safe_track + ".json")


def load_cached(folder: str, track: str) -> dict | None:
    path = cache_path(folder, track)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_cached(folder: str, track: str, data: dict) -> None:
    path = cache_path(folder, track)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def analyze_audio_bytes(data: bytes, mime: str = "audio/mpeg") -> dict:
    api_key = _gemini_key()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in .env / telegram-bot/.env")

    b64 = base64.standard_b64encode(data).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    last_err: Exception | None = None
    with httpx.Client(timeout=120.0) as client:
        for model in _models():
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={api_key}"
            )
            try:
                r = client.post(url, json=payload)
                if r.status_code in (404, 429, 503):
                    last_err = RuntimeError(f"{model} -> {r.status_code}")
                    continue
                r.raise_for_status()
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                data_obj = _parse_json(text)
                if "sentences" not in data_obj:
                    raise RuntimeError("Bad JSON shape")
                return data_obj
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f"Gemini transcript failed: {last_err}")


def analyze_file(path: Path, folder: str, track: str, use_cache: bool = True) -> dict:
    if use_cache:
        cached = load_cached(folder, track)
        if cached:
            cached["_cached"] = True
            return cached
    result = analyze_audio_bytes(path.read_bytes(), "audio/mpeg")
    result["_cached"] = False
    save_cached(folder, track, result)
    return result
