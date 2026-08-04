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

PROMPT = """You are a Dutch B1 tutor. Listen carefully to this Dutch audio (Contact! NT2 style).

Return ONLY JSON:
{
  "title": "short title",
  "sentences": [
    {
      "nl": "full Dutch sentence exactly as spoken (include all words)",
      "en": "natural English translation",
      "tokens": [
        {"text": "word", "role": "subject|verb|object|complement|conjunction|determiner|preposition|adverb|particle|other"}
      ]
    }
  ]
}

STRICT rules:
1. Transcribe the FULL audio — every spoken sentence / speaker turn. Do not summarize or skip lines.
2. tokens MUST cover EVERY word and punctuation chunk in "nl" in order. Joining tokens with spaces (then fixing punctuation spacing) must reconstruct the Dutch sentence with no missing words.
3. Never leave articles/possessives/prepositions/particles untagged as invisible filler — assign a real role:
   - subject = onderwerp (Ik, jij, mijn broer, ...)
   - verb = persoonsvorm and verb cluster pieces (weet, wordt, heb, wil, worden, bent, ...)
   - object = lijdend/meewerkend voorwerp (voornemens, Wat, ...)
   - complement = predicatives / adjective modifiers that complete meaning (zeker, rijk, goede, nieuwe, groot, stinkend, ...)
   - conjunction = dat, als, omdat, maar, en, ...
   - determiner = de, het, een, mijn, jouw, die, deze, ...
   - preposition = voor, in, op, met, naar, ...
   - adverb = nou, later, hier, erg, ...
   - particle = separable verb particles / discourse bits if needed
   - other = ONLY true leftovers (rare)
4. English must match the full Dutch sentence.
5. If it is a dialogue, keep speaker turns as separate sentences in order.
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


_DETERMINERS = {
    "de", "het", "een", "mijn", "jouw", "haar", "ons", "onze", "jullie", "hun",
    "die", "deze", "dit", "elk", "elke", "geen",
}
_PREPS = {
    "voor", "in", "op", "met", "naar", "van", "aan", "bij", "over", "onder",
    "tussen", "tegen", "door", "tot", "uit",
}
_CONJS = {"en", "maar", "of", "want", "omdat", "terwijl", "dat", "als", "dus", "toch"}
_ADVERBS = {
    "nou", "later", "hier", "daar", "nu", "nog", "al", "erg", "heel", "zeker",
    "misschien", "graag", "ook",
}


def _guess_role(word: str) -> str:
    w = re.sub(r'[.,!?;:"“”‘’\']+', "", word.lower())
    if w in _CONJS:
        return "conjunction"
    if w in _DETERMINERS:
        return "determiner"
    if w in _PREPS:
        return "preposition"
    if w in _ADVERBS:
        return "adverb"
    return "other"


def complete_tokens(sentence: dict) -> dict:
    """Ensure every word in nl has a token with a useful role."""
    nl = (sentence.get("nl") or "").strip()
    words = re.findall(r"\S+", nl)
    raw = sentence.get("tokens") or []
    role_by_norm: dict[str, str] = {}
    for t in raw:
        text = str(t.get("text") or "")
        role = (t.get("role") or "other").lower()
        if text:
            role_by_norm[text.lower()] = role
    if not words:
        return sentence
    needs_rebuild = len(raw) < len(words) or any(
        not (t.get("role") or "").strip() or (t.get("role") or "").lower() == "other"
        for t in raw
    )
    if needs_rebuild:
        tokens = []
        for w in words:
            existing = role_by_norm.get(w.lower())
            role = existing if existing and existing != "other" else _guess_role(w)
            tokens.append({"text": w, "role": role})
    else:
        tokens = [
            {
                "text": t.get("text"),
                "role": (
                    t.get("role")
                    if (t.get("role") or "").lower() not in ("", "other")
                    else _guess_role(str(t.get("text") or ""))
                ),
            }
            for t in raw
        ]
    out = dict(sentence)
    out["tokens"] = tokens
    return out


def complete_script(data: dict) -> dict:
    sentences = [complete_tokens(s) for s in (data.get("sentences") or [])]
    out = dict(data)
    out["sentences"] = sentences
    return out


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
                return complete_script(data_obj)
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f"Gemini transcript failed: {last_err}")


def analyze_file(path: Path, folder: str, track: str, use_cache: bool = True) -> dict:
    if use_cache:
        cached = load_cached(folder, track)
        if cached:
            completed = complete_script(cached)
            completed["_cached"] = True
            return completed
    result = analyze_audio_bytes(path.read_bytes(), "audio/mpeg")
    result["_cached"] = False
    save_cached(folder, track, result)
    return result
