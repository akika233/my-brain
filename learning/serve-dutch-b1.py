#!/usr/bin/env python3
"""Local practice server for Dutch B1 + Contact! 2 materials.

Serves the HTML site from learning/ and mounts your Desktop materials
at /materials/ (PDFs + MP3s stay on disk — not copied into git).

Usage:
  python learning/serve-dutch-b1.py
  → http://127.0.0.1:8765/
"""

from __future__ import annotations

import json
import mimetypes
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SITE = ROOT / "dutch-b1-planner.html"
MATERIALS = Path(r"C:\Users\akika\OneDrive\Desktop\Contact 2 (B1)")
HOST = "0.0.0.0"  # allow phone / other devices on same Wi‑Fi
PORT = 8765


def lan_urls() -> list[str]:
    """Best-effort local network URLs for phone access."""
    urls = [f"http://127.0.0.1:{PORT}/"]
    try:
        import socket

        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                urls.append(f"http://{ip}:{PORT}/")
    except Exception:
        pass
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def build_index() -> dict:
    pdfs = sorted(p.name for p in MATERIALS.glob("*.pdf"))
    audio = []
    if MATERIALS.exists():
        for folder in sorted(MATERIALS.iterdir()):
            if not folder.is_dir():
                continue
            tracks = sorted(p.name for p in folder.glob("*.mp3"))
            if tracks:
                audio.append({"folder": folder.name, "tracks": tracks, "count": len(tracks)})
    return {
        "materials_root": str(MATERIALS),
        "exists": MATERIALS.exists(),
        "pdfs": pdfs,
        "audio": audio,
    }


def safe_materials_path(rel: str) -> Path | None:
    """Resolve path under MATERIALS; reject .. traversal."""
    rel = unquote(rel).lstrip("/").replace("\\", "/")
    if not rel or ".." in rel.split("/"):
        return None
    target = (MATERIALS / rel).resolve()
    try:
        target.relative_to(MATERIALS.resolve())
    except ValueError:
        return None
    if not target.is_file():
        return None
    return target


class Handler(BaseHTTPRequestHandler):
    server_version = "DutchB1Server/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        ctype = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        size = path.stat().st_size
        range_header = self.headers.get("Range")
        start = 0
        end = size - 1
        status = 200

        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                start_s, end_s = m.groups()
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206

        length = end - start + 1
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()

            with path.open("rb") as f:
                f.seek(start)
                remaining = length
                chunk_size = 1024 * 256
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            # Browser cancelled (common with large PDFs) — ignore
            return

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path in ("/", "/index.html", "/dutch-b1-planner.html"):
            if not SITE.exists():
                self._send(404, b"Site HTML missing", "text/plain")
                return
            self._send_file(SITE, "text/html; charset=utf-8")
            return

        if path == "/api/index":
            body = json.dumps(build_index(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return

        if path.startswith("/materials/"):
            rel = path[len("/materials/") :]
            target = safe_materials_path(rel)
            if not target:
                self._send(404, b"Not found", "text/plain")
                return
            self._send_file(target)
            return

        # Allow reading contact2-index.json fallback from learning/
        if path == "/contact2-index.json":
            fallback = ROOT / "contact2-index.json"
            if fallback.exists():
                self._send_file(fallback, "application/json; charset=utf-8")
                return

        self._send(404, b"Not found", "text/plain")


def main() -> None:
    if not MATERIALS.exists():
        print(f"WARNING: materials folder not found:\n  {MATERIALS}")
    else:
        idx = build_index()
        print(f"Materials OK — {len(idx['pdfs'])} PDFs, {sum(a['count'] for a in idx['audio'])} tracks")

    if not SITE.exists():
        raise SystemExit(f"Missing site file: {SITE}")

    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Dutch B1 practice server listening on port {PORT}")
    print("Open on this PC or your phone (same Wi-Fi):")
    for u in lan_urls():
        print(f"  {u}")
    print("Keep this window open. Press Ctrl+C to stop.")
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
