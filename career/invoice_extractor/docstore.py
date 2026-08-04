from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote, urljoin

import requests


class DocstoreClient(ABC):
    """Fetch invoice PDFs from a document store."""

    @abstractmethod
    def list_pdfs(self) -> list[str]:
        ...

    @abstractmethod
    def download(self, doc_id: str, dest_dir: Path) -> Path:
        ...

    def close(self) -> None:
        return None


class LocalFolderDocstore(DocstoreClient):
    """Read PDFs already on disk (no login)."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise NotADirectoryError(self.folder)

    def list_pdfs(self) -> list[str]:
        return sorted(p.name for p in self.folder.glob("*.pdf"))

    def download(self, doc_id: str, dest_dir: Path) -> Path:
        src = self.folder / doc_id
        if not src.is_file():
            raise FileNotFoundError(src)
        return src


class HttpSessionDocstore(DocstoreClient):
    """Generic form-login HTTP docstore."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        login_path: str = "/login",
        list_path: str = "/api/documents",
        download_path_template: str = "/api/documents/{id}/download",
        username_field: str = "username",
        password_field: str = "password",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.login_path = login_path
        self.list_path = list_path
        self.download_path_template = download_path_template
        self.username_field = username_field
        self.password_field = password_field
        self.session = requests.Session()
        self._login(username, password)

    def _login(self, username: str, password: str) -> None:
        url = f"{self.base_url}{self.login_path}"
        resp = self.session.post(
            url,
            data={self.username_field: username, self.password_field: password},
            timeout=60,
        )
        resp.raise_for_status()

    def list_pdfs(self) -> list[str]:
        url = f"{self.base_url}{self.list_path}"
        resp = self.session.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("documents", data) if isinstance(data, dict) else data
        names: list[str] = []
        for doc in docs:
            if isinstance(doc, dict):
                name = doc.get("name") or doc.get("filename") or doc.get("id")
                names.append(str(doc.get("id") or name))
            else:
                names.append(str(doc))
        return names

    def download(self, doc_id: str, dest_dir: Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path_tmpl = self.download_path_template.replace(
            "{id}", quote(doc_id, safe="")
        )
        url = f"{self.base_url}{path_tmpl}"
        resp = self.session.get(url, timeout=120)
        resp.raise_for_status()
        filename = doc_id if str(doc_id).lower().endswith(".pdf") else f"{doc_id}.pdf"
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            filename = cd.split("filename=")[-1].strip().strip("\"'")
        out = dest_dir / Path(filename).name
        out.write_bytes(resp.content)
        return out

    def close(self) -> None:
        self.session.close()


class NFDocstore(DocstoreClient):
    """
    New Balance NF Docstore on bosuka1.

    Document URL pattern:
      http://bosuka1:6400/docStore/store/NF%20Docstore/document/?L[LREF]=79954

    Download tries the document page + common binary/download query flags.
    Provide LREFs via DOCSTORE_LREFS (comma-separated) or CLI --lref.
    """

    def __init__(
        self,
        base_url: str = "http://bosuka1:6400",
        store_name: str = "NF Docstore",
        username: str | None = None,
        password: str | None = None,
        login_path: str = "/docStore/login",
        lrefs: list[str] | None = None,
        auth_mode: str = "form",  # form | basic | none
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.store_name = store_name
        self.login_path = login_path
        self.lrefs = [str(x).strip() for x in (lrefs or []) if str(x).strip()]
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "NB-InvoiceExtractor/0.1",
                "Accept": "*/*",
            }
        )
        if username and auth_mode == "basic":
            self.session.auth = (username, password or "")
        elif username and auth_mode == "form":
            self._form_login(username, password or "")

    def _form_login(self, username: str, password: str) -> None:
        url = urljoin(self.base_url + "/", self.login_path.lstrip("/"))
        # Try common field names used by enterprise portals
        for user_field, pass_field in (
            ("username", "password"),
            ("user", "password"),
            ("j_username", "j_password"),
            ("login", "password"),
        ):
            resp = self.session.post(
                url,
                data={user_field: username, pass_field: password},
                timeout=60,
                allow_redirects=True,
            )
            if resp.status_code < 500:
                return
        resp.raise_for_status()

    def document_url(self, lref: str) -> str:
        store = quote(self.store_name, safe="")
        # Keep L[LREF] literal — server expects that query key
        return f"{self.base_url}/docStore/store/{store}/document/?L[LREF]={quote(str(lref), safe='')}"

    def list_pdfs(self) -> list[str]:
        if not self.lrefs:
            raise ValueError(
                "No LREFs configured. Set DOCSTORE_LREFS=79954,79955 "
                "or pass --lref 79954"
            )
        return list(self.lrefs)

    def download(self, doc_id: str, dest_dir: Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        lref = str(doc_id).strip()

        candidates = [
            self.document_url(lref),
            self.document_url(lref) + "&download=1",
            self.document_url(lref) + "&action=download",
            f"{self.base_url}/docStore/store/{quote(self.store_name, safe='')}/document/content/?L[LREF]={quote(lref, safe='')}",
        ]

        last_err: Exception | None = None
        for url in candidates:
            try:
                resp = self.session.get(url, timeout=120, allow_redirects=True)
                resp.raise_for_status()
                ctype = (resp.headers.get("Content-Type") or "").lower()
                content = resp.content
                if not content:
                    continue
                # Accept PDF bytes even if content-type is wrong
                is_pdf = content[:4] == b"%PDF" or "pdf" in ctype
                if not is_pdf and "html" in ctype:
                    # Maybe the HTML page embeds a download link
                    pdf_link = self._find_pdf_link(resp.text, lref)
                    if pdf_link:
                        resp = self.session.get(pdf_link, timeout=120)
                        resp.raise_for_status()
                        content = resp.content
                        is_pdf = content[:4] == b"%PDF"
                if not is_pdf:
                    continue

                filename = self._filename_from_response(resp, lref)
                out = dest_dir / filename
                out.write_bytes(content)
                return out
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                continue

        raise RuntimeError(
            f"Could not download PDF for LREF={lref}. "
            f"Last error: {last_err}. "
            "Open the document in a browser while logged in and share "
            "the real download URL if this keeps failing."
        )

    def _find_pdf_link(self, html: str, lref: str) -> str | None:
        patterns = [
            rf'href=["\']([^"\']*L\[LREF\]={re.escape(lref)}[^"\']*download[^"\']*)["\']',
            rf'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            rf'href=["\']([^"\']*content[^"\']*L\[LREF\]={re.escape(lref)}[^"\']*)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, flags=re.I)
            if m:
                href = m.group(1)
                if href.startswith("http"):
                    return href
                return urljoin(self.base_url + "/", href.lstrip("/"))
        return None

    @staticmethod
    def _filename_from_response(resp: requests.Response, lref: str) -> str:
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            name = cd.split("filename=")[-1].strip().strip("\"'")
            if name:
                return Path(name).name
        return f"LREF_{lref}.pdf"

    def close(self) -> None:
        self.session.close()


def default_invoice_folder() -> Path:
    """Prefer the NB OneDrive Invoice folder when present."""
    configured = os.getenv("INVOICE_DOWNLOAD_DIR") or os.getenv("DOCSTORE_LOCAL_FOLDER")
    if configured:
        return Path(configured)

    candidates = [
        Path(r"C:\Users\shjiang\OneDrive - New Balance Athletics, Inc\Documents\Invoice"),
        Path.home()
        / "OneDrive - New Balance Athletics, Inc"
        / "Documents"
        / "Invoice",
        Path("career/invoice_pdfs"),
    ]
    for path in candidates:
        if path.is_dir():
            return path
    # Default target even if it does not exist yet (download will create)
    return candidates[0]


def build_docstore_from_env(extra_lrefs: list[str] | None = None) -> DocstoreClient:
    """Build client from environment variables."""
    mode = os.getenv("DOCSTORE_MODE", "local").lower()
    if mode == "local":
        return LocalFolderDocstore(default_invoice_folder())

    if mode in {"nf", "nfdocstore", "bosuka"}:
        lrefs_env = os.getenv("DOCSTORE_LREFS", "")
        lrefs = [x.strip() for x in lrefs_env.split(",") if x.strip()]
        if extra_lrefs:
            lrefs.extend(extra_lrefs)
        return NFDocstore(
            base_url=os.getenv("DOCSTORE_BASE_URL", "http://bosuka1:6400"),
            store_name=os.getenv("DOCSTORE_STORE_NAME", "NF Docstore"),
            username=os.getenv("DOCSTORE_USERNAME") or None,
            password=os.getenv("DOCSTORE_PASSWORD") or None,
            login_path=os.getenv("DOCSTORE_LOGIN_PATH", "/docStore/login"),
            lrefs=lrefs,
            auth_mode=os.getenv("DOCSTORE_AUTH_MODE", "form"),
        )

    if mode == "http":
        base = os.getenv("DOCSTORE_BASE_URL", "")
        user = os.getenv("DOCSTORE_USERNAME", "")
        password = os.getenv("DOCSTORE_PASSWORD", "")
        if not base or not user:
            raise ValueError(
                "DOCSTORE_MODE=http requires DOCSTORE_BASE_URL and DOCSTORE_USERNAME"
            )
        return HttpSessionDocstore(
            base_url=base,
            username=user,
            password=password,
            login_path=os.getenv("DOCSTORE_LOGIN_PATH", "/login"),
            list_path=os.getenv("DOCSTORE_LIST_PATH", "/api/documents"),
            download_path_template=os.getenv(
                "DOCSTORE_DOWNLOAD_PATH", "/api/documents/{id}/download"
            ),
            username_field=os.getenv("DOCSTORE_USERNAME_FIELD", "username"),
            password_field=os.getenv("DOCSTORE_PASSWORD_FIELD", "password"),
        )

    raise ValueError(
        f"Unknown DOCSTORE_MODE={mode!r} (use local, nf, or http)"
    )
