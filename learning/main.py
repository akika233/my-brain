"""Dutch B1 learn page + Colette TTS on Vercel."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, File, Form, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from store import get_upload_file, list_uploads, load_progress, save_progress, save_upload, storage_mode

VOICE = "nl-NL-ColetteNeural"
RATE_RE = re.compile(r"^[+-]\d+%$")
VOICE_RE = re.compile(r"^nl-[A-Z]{2}-[A-Za-z]+Neural$")
ROOT = Path(__file__).resolve().parent
HTML = ROOT / "dutch-b1-learn.html"
COOKIE = "dutch_b1"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def site_password() -> str:
    return os.environ.get("DUTCH_B1_PASSWORD") or ""


def cookie_token(password: str) -> str:
    return hmac.new(password.encode("utf-8"), b"ok", hashlib.sha256).hexdigest()


def is_authed(request: Request) -> bool:
    password = site_password()
    if not password:
        return False
    got = request.cookies.get(COOKIE) or ""
    expected = cookie_token(password)
    if len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


def login_page(error: str = "") -> HTMLResponse:
    msg = f'<p class="err">{error}</p>' if error else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Dutch B1 · Sign in</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Manrope:wght@400;600;700&display=swap" rel="stylesheet"/>
<style>
:root{{--ink:#1a2332;--muted:#5a6678;--paper:#f7f3eb;--card:#fffdf8;--line:#e2d9cb;--accent:#c45c26;--sea:#2f6f6a}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;font-family:Manrope,system-ui,sans-serif;color:var(--ink);background:var(--paper);display:grid;place-items:center;padding:1.5rem}}
.card{{width:min(420px,100%);background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1.6rem 1.5rem;box-shadow:0 12px 40px rgba(26,35,50,.08)}}
h1{{font-family:Fraunces,serif;font-size:1.6rem;margin:0 0 .35rem}}
p{{color:var(--muted);margin:0 0 1rem}}
label{{display:block;font-size:.8rem;font-weight:700;margin-bottom:.35rem}}
input{{width:100%;padding:.7rem .8rem;border:1px solid var(--line);border-radius:12px;font:inherit}}
button{{margin-top:1rem;width:100%;border:0;border-radius:999px;padding:.75rem 1rem;font:inherit;font-weight:700;color:#fff;background:var(--sea);cursor:pointer}}
.err{{color:#c0392b;font-weight:700}}
</style>
</head>
<body>
<form class="card" method="post" action="/login">
  <h1>Dutch B1</h1>
  <p>Private study site. Enter the password to continue.</p>
  {msg}
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required autofocus/>
  <button type="submit">Open</button>
</form>
</body>
</html>"""
    return HTMLResponse(html, status_code=401 if error else 200, headers={"Cache-Control": "private, no-store"})


def json_error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


@app.middleware("http")
async def require_password(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or path in ("/login", "/logout"):
        return await call_next(request)
    if not site_password():
        return JSONResponse({"error": "password is not configured"}, status_code=503)
    if is_authed(request):
        return await call_next(request)
    if path.startswith("/api/"):
        return json_error(401, "unauthorized")
    return RedirectResponse("/login", status_code=303)


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


@app.get("/login", response_model=None)
def login_get() -> HTMLResponse:
    return login_page()


@app.post("/login", response_model=None)
async def login_post(request: Request) -> Response:
    password = site_password()
    if not password:
        return JSONResponse({"error": "password is not configured"}, status_code=503)
    raw = (await request.body()).decode("utf-8", "replace")
    submitted = (parse_qs(raw).get("password") or [""])[0]
    submitted_h = hashlib.sha256(submitted.encode("utf-8")).digest()
    expected_h = hashlib.sha256(password.encode("utf-8")).digest()
    if not hmac.compare_digest(submitted_h, expected_h):
        return login_page("Wrong password.")
    res = RedirectResponse("/", status_code=303)
    res.set_cookie(
        COOKIE,
        cookie_token(password),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return res


@app.get("/logout")
def logout() -> Response:
    res = RedirectResponse("/login", status_code=303)
    res.delete_cookie(COOKIE, path="/")
    return res


@app.get("/")
@app.get("/dutch-b1-learn.html")
def learn_page() -> FileResponse:
    return FileResponse(
        HTML,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "private, no-store"},
    )


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
        headers={"Cache-Control": "private, max-age=3600"},
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


@app.get("/api/progress")
async def progress_get() -> JSONResponse:
    data = await load_progress()
    data["storage"] = storage_mode()
    return JSONResponse(data, headers={"Cache-Control": "private, no-store"})


@app.put("/api/progress")
async def progress_put(request: Request) -> JSONResponse:
    n = int(request.headers.get("content-length") or 0)
    if n > 200_000:
        return json_error(413, "payload too large")
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return json_error(400, "invalid json")
    if not isinstance(payload, dict):
        return json_error(400, "invalid json")
    try:
        data = await save_progress(payload)
    except ValueError as e:
        return json_error(413, str(e))
    except Exception as e:
        return json_error(502, str(e))
    data["storage"] = storage_mode()
    return JSONResponse(data, headers={"Cache-Control": "private, no-store"})


@app.get("/api/uploads")
async def uploads_list(chapter: str = "", kind: str = "") -> JSONResponse:
    items = await list_uploads(chapter or None, kind or None)
    return JSONResponse(
        {"items": items, "storage": storage_mode()},
        headers={"Cache-Control": "private, no-store"},
    )


@app.post("/api/uploads")
async def uploads_post(
    file: UploadFile = File(...),
    kind: str = Form("speaking"),
    chapter: str = Form(""),
    slot: str = Form("0"),
    transcript: str = Form(""),
) -> JSONResponse:
    data = await file.read()
    try:
        item = await save_upload(
            data=data,
            mime=file.content_type or "application/octet-stream",
            kind=kind,
            chapter=chapter,
            slot=slot,
            transcript=transcript,
        )
    except ValueError as e:
        return json_error(400, str(e))
    except Exception as e:
        return json_error(502, str(e))
    return JSONResponse(item, headers={"Cache-Control": "private, no-store"})


@app.get("/api/uploads/{upload_id}/file")
async def uploads_file(upload_id: str) -> Response:
    found = await get_upload_file(upload_id)
    if not found:
        return json_error(404, "not found")
    body, mime = found
    return Response(
        content=body,
        media_type=mime,
        headers={"Cache-Control": "private, max-age=3600"},
    )
