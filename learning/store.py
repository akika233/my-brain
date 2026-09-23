"""Persist Dutch B1 progress + user uploads.

On Vercel: Blob store (BLOB_READ_WRITE_TOKEN).
On a PC: learning/.data/
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
LOCAL_DIR = ROOT / ".data"
PREFIX = "dutch-b1"
PROGRESS_PATH = f"{PREFIX}/progress.json"
UPLOADS_PATH = f"{PREFIX}/uploads.json"
BLOB_API = "https://vercel.com/api/blob"
API_VERSION = "7"
MAX_UPLOAD_BYTES = 3_500_000
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def _token() -> str:
    return (os.environ.get("BLOB_READ_WRITE_TOKEN") or "").strip()


def storage_mode() -> str:
    if _token():
        return "blob"
    if os.environ.get("VERCEL"):
        return "ephemeral"
    return "local"


def _data_dir() -> Path:
    if os.environ.get("VERCEL") and not _token():
        return Path("/tmp/dutch-b1-data")
    return LOCAL_DIR


def _empty_progress() -> dict[str, Any]:
    return {
        "known": {},
        "writing": {},
        "tests": {},
        "currentChIdx": 0,
        "updatedAt": 0,
    }


def _empty_uploads() -> list[dict[str, Any]]:
    return []


def _http(method: str, url: str, headers: dict[str, str], body: bytes | None = None) -> tuple[int, bytes]:
    req = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(req, timeout=45) as resp:
            return resp.status, resp.read()
    except HTTPError as e:
        return e.code, e.read() if e.fp else b""


async def _http_async(method: str, url: str, headers: dict[str, str], body: bytes | None = None) -> tuple[int, bytes]:
    return await asyncio.to_thread(_http, method, url, headers, body)


def _blob_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {_token()}",
        "x-api-version": API_VERSION,
    }
    if extra:
        headers.update(extra)
    return headers


async def _blob_put(pathname: str, data: bytes, content_type: str, overwrite: bool = True) -> dict[str, Any]:
    qs = urlencode({"pathname": pathname})
    status, raw = await _http_async(
        "PUT",
        f"{BLOB_API}?{qs}",
        _blob_headers(
            {
                "x-content-type": content_type,
                "x-add-random-suffix": "0",
                "x-allow-overwrite": "1" if overwrite else "0",
            }
        ),
        data,
    )
    if status >= 400:
        raise RuntimeError(f"blob put {status}: {raw[:240]!r}")
    return json.loads(raw.decode("utf-8"))


async def _blob_get(url_or_pathname: str) -> bytes | None:
    url = url_or_pathname
    if not url.startswith("http"):
        url = f"{BLOB_API}?{urlencode({'pathname': url_or_pathname})}"
    status, raw = await _http_async("GET", url, _blob_headers())
    if status == 404:
        return None
    if status >= 400:
        raise RuntimeError(f"blob get {status}: {raw[:240]!r}")
    return raw


def _local_file(pathname: str) -> Path:
    folder = _data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return folder / pathname.replace("/", "__")


async def _put(pathname: str, data: bytes, content_type: str) -> dict[str, Any]:
    if storage_mode() == "blob":
        return await _blob_put(pathname, data, content_type)
    path = _local_file(pathname)
    await asyncio.to_thread(path.write_bytes, data)
    return {"pathname": pathname, "url": "", "contentType": content_type}


async def _get(pathname: str) -> bytes | None:
    if storage_mode() == "blob":
        return await _blob_get(pathname)
    path = _local_file(pathname)
    if not path.exists():
        return None
    return await asyncio.to_thread(path.read_bytes)


async def load_progress() -> dict[str, Any]:
    raw = await _get(PROGRESS_PATH)
    if not raw:
        return _empty_progress()
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return _empty_progress()
    if not isinstance(data, dict):
        return _empty_progress()
    out = _empty_progress()
    out.update({k: data[k] for k in out if k in data})
    if not isinstance(out["known"], dict):
        out["known"] = {}
    if not isinstance(out["writing"], dict):
        out["writing"] = {}
    if not isinstance(out["tests"], dict):
        out["tests"] = {}
    return out


async def save_progress(payload: dict[str, Any]) -> dict[str, Any]:
    current = await load_progress()
    known = payload.get("known") if isinstance(payload.get("known"), dict) else current["known"]
    writing = payload.get("writing") if isinstance(payload.get("writing"), dict) else current["writing"]
    tests = payload.get("tests") if isinstance(payload.get("tests"), dict) else current["tests"]
    try:
        current_ch = int(payload.get("currentChIdx", current.get("currentChIdx") or 0))
    except (TypeError, ValueError):
        current_ch = 0
    cleaned_known: dict[str, list[str]] = {}
    for key, words in known.items():
        if isinstance(words, list):
            cleaned_known[str(key)] = [str(w) for w in words][:80]
    cleaned_writing: dict[str, str] = {}
    for key, text in writing.items():
        cleaned_writing[str(key)] = str(text)[:20000]
    data = {
        "known": cleaned_known,
        "writing": cleaned_writing,
        "tests": tests,
        "currentChIdx": max(0, min(7, current_ch)),
        "updatedAt": int(datetime.now(timezone.utc).timestamp() * 1000),
    }
    blob = json.dumps(data, ensure_ascii=False).encode("utf-8")
    if len(blob) > 200_000:
        raise ValueError("progress too large")
    await _put(PROGRESS_PATH, blob, "application/json")
    return data


async def load_uploads() -> list[dict[str, Any]]:
    raw = await _get(UPLOADS_PATH)
    if not raw:
        return _empty_uploads()
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return _empty_uploads()
    if not isinstance(data, list):
        return _empty_uploads()
    return [item for item in data if isinstance(item, dict)]


async def _save_uploads(items: list[dict[str, Any]]) -> None:
    blob = json.dumps(items, ensure_ascii=False).encode("utf-8")
    await _put(UPLOADS_PATH, blob, "application/json")


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "kind": item.get("kind"),
        "chapter": item.get("chapter"),
        "slot": item.get("slot"),
        "mime": item.get("mime"),
        "bytes": item.get("bytes"),
        "created": item.get("created"),
        "transcript": item.get("transcript") or "",
    }


async def list_uploads(chapter: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    items = await load_uploads()
    out = []
    for item in items:
        if chapter and str(item.get("chapter")) != str(chapter):
            continue
        if kind and item.get("kind") != kind:
            continue
        out.append(_public_item(item))
    out.sort(key=lambda x: x.get("created") or "", reverse=True)
    return out


async def save_upload(
    *,
    data: bytes,
    mime: str,
    kind: str,
    chapter: str,
    slot: str,
    transcript: str = "",
) -> dict[str, Any]:
    if not data:
        raise ValueError("empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("file too large")
    kind = re.sub(r"[^a-z]", "", (kind or "speaking").lower()) or "speaking"
    chapter = re.sub(r"[^0-9]", "", str(chapter) or "")[:2] or "0"
    slot = re.sub(r"[^a-zA-Z0-9_-]", "", str(slot) or "0")[:24] or "0"
    mime = (mime or "application/octet-stream")[:80]
    transcript = (transcript or "")[:2000]
    ext = "webm"
    if "mp4" in mime:
        ext = "mp4"
    elif "mpeg" in mime or "mp3" in mime:
        ext = "mp3"
    elif mime.startswith("text/"):
        ext = "txt"
    items = await load_uploads()
    existing = next(
        (i for i in items if str(i.get("chapter")) == chapter and str(i.get("slot")) == slot and i.get("kind") == kind),
        None,
    )
    upload_id = existing["id"] if existing and SAFE_ID.match(str(existing.get("id") or "")) else uuid.uuid4().hex
    pathname = f"{PREFIX}/uploads/{upload_id}.{ext}"
    await _put(pathname, data, mime)
    record = {
        "id": upload_id,
        "kind": kind,
        "chapter": chapter,
        "slot": slot,
        "mime": mime,
        "bytes": len(data),
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "transcript": transcript,
        "pathname": pathname,
    }
    items = [i for i in items if i.get("id") != upload_id]
    items.append(record)
    await _save_uploads(items)
    return _public_item(record)


async def get_upload_file(upload_id: str) -> tuple[bytes, str] | None:
    if not SAFE_ID.match(upload_id):
        return None
    items = await load_uploads()
    item = next((i for i in items if i.get("id") == upload_id), None)
    if not item:
        return None
    raw = await _get(str(item.get("pathname") or ""))
    if raw is None:
        return None
    return raw, str(item.get("mime") or "application/octet-stream")
