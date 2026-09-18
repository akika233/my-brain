"""Dutch B1 learn page + Colette TTS on Vercel."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

VOICE = "nl-NL-ColetteNeural"
RATE_RE = re.compile(r"^[+-]\d+%$")
VOICE_RE = re.compile(r"^nl-[A-Z]{2}-[A-Za-z]+Neural$")
ROOT = Path(__file__).resolve().parent
HTML = ROOT / "dutch-b1-learn.html"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def json_error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def synthesize(text: str, voice: str, rate: str) -> bytes:
    import edge_tts

    if not RATE_RE.match(rate or ""):
        rate = "+0%"
    if not voice or not VOICE_RE.match(voice):
        voice = VOICE
    comm = edge_tts.Communicate(text, voice, rate=rate)
    parts: list[bytes] = []
    async for msg in comm.stream():
        if msg["type"] == "audio":
            parts.append(msg["data"])
    audio = b"".join(parts)
    if not audio:
        raise RuntimeError("Edge TTS returned no audio")
    return audio


@app.get("/")
@app.get("/dutch-b1-learn.html")
def learn_page() -> FileResponse:
    return FileResponse(HTML, media_type="text/html; charset=utf-8")


async def tts_from_payload(text: str, rate: str, voice: str) -> Response:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return json_error(400, "text required")
    if len(text) > 8000:
        return json_error(413, "text too long")
    try:
        audio = await synthesize(text, voice, rate)
    except ModuleNotFoundError:
        return json_error(501, "edge-tts missing")
    except Exception as e:
        return json_error(502, str(e))
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/tts")
async def tts_get(text: str = "", rate: str = "+0%", voice: str = VOICE) -> Response:
    return await tts_from_payload(text, rate, voice)


@app.post("/api/tts")
async def tts_post(request: Request) -> Response:
    n = int(request.headers.get("content-length") or 0)
    if n > 24_000:
        return json_error(413, "payload too large")
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return json_error(400, "invalid json")
    if not isinstance(payload, dict):
        return json_error(400, "invalid json")
    return await tts_from_payload(
        str(payload.get("text") or ""),
        str(payload.get("rate") or "+0%"),
        str(payload.get("voice") or VOICE),
    )
