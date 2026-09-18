from __future__ import annotations

from pathlib import Path

# Words whose vertical positions differ by less than this (points) are on the same visual row.
_ROW_TOLERANCE = 3.0

# A horizontal gap wider than this (points) is treated as a column break and rendered
# as a double space, so downstream parsing can tell "label   value" from "two words".
_MIN_COLUMN_GAP = 8.0

# ── Letterhead OCR ────────────────────────────────────────────────────────────
# Fraction of page height treated as the letterhead band.
_LETTERHEAD_BAND = 0.22
# Keep only text at least this tall relative to the tallest text in the band. Brand names
# are set noticeably larger than address/legal lines, so this isolates them.
_PROMINENT_HEIGHT_RATIO = 0.30
_MIN_OCR_CONFIDENCE = 0.5
_MAX_BRAND_LINES = 3
_OCR_RESOLUTION = 300

_ocr_engine = None


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}


def _make_paddle_ocr():
    """Build a PaddleOCR engine. 3.x and 2.x take different constructor kwargs."""
    import os

    # Skip the slow hoster ping. Disable oneDNN: PaddlePaddle 3.3.x CPU + PIR crashes
    # with ConvertPirAttribute2RuntimeAttribute on Windows.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    from paddleocr import PaddleOCR

    attempts = (
        dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        ),
        dict(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        ),
        dict(
            lang="french",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        ),
        dict(use_angle_cls=True, lang="en", show_log=False, enable_mkldnn=False),
        dict(use_angle_cls=True, lang="en", show_log=False),
        dict(lang="en"),
        dict(),
    )
    last_error: Exception | None = None
    for kwargs in attempts:
        try:
            return PaddleOCR(**kwargs)
        except (TypeError, ValueError) as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return PaddleOCR()


def _ensure_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = _make_paddle_ocr()
    return _ocr_engine


def _to_bgr(image):
    """PaddleOCR expects OpenCV-style BGR arrays."""
    import numpy as np

    arr = np.asarray(image)
    if arr.ndim == 3 and arr.shape[2] == 3:
        return arr[:, :, ::-1].copy()
    return arr


def _run_ocr(image):
    engine = _ensure_ocr_engine()
    if hasattr(engine, "predict"):
        try:
            return engine.predict(image)
        except TypeError:
            pass
    ocr = getattr(engine, "ocr", None)
    if callable(ocr):
        try:
            return ocr(image, cls=True)
        except TypeError:
            return ocr(image)
    raise RuntimeError("PaddleOCR engine has no predict/ocr method")


def _paddle3_page(page) -> dict | None:
    """Normalize a PaddleOCR 3.x page result to rec_texts / rec_scores / rec_polys."""
    if page is None:
        return None
    if isinstance(page, dict):
        data = page.get("res", page)
        if isinstance(data, dict) and (
            "rec_texts" in data or "rec_text" in data or "dt_polys" in data
        ):
            return data
        return None
    rec_texts = getattr(page, "rec_texts", None)
    if rec_texts is not None:
        polys = getattr(page, "rec_polys", None)
        if polys is None:
            polys = getattr(page, "dt_polys", None)
        return {
            "rec_texts": rec_texts,
            "rec_scores": getattr(page, "rec_scores", None),
            "rec_polys": polys,
        }
    for meth in ("to_dict", "json"):
        fn = getattr(page, meth, None)
        if not callable(fn):
            continue
        try:
            data = fn()
        except Exception:  # noqa: BLE001
            continue
        if isinstance(data, dict):
            data = data.get("res", data)
            if isinstance(data, dict) and "rec_texts" in data:
                return data
    try:
        texts = page["rec_texts"]
    except Exception:  # noqa: BLE001
        return None
    scores = None
    polys = None
    try:
        scores = page["rec_scores"]
    except Exception:  # noqa: BLE001
        pass
    try:
        polys = page["rec_polys"]
    except Exception:  # noqa: BLE001
        try:
            polys = page["dt_polys"]
        except Exception:  # noqa: BLE001
            pass
    return {"rec_texts": texts, "rec_scores": scores, "rec_polys": polys}


def _as_seq(value):
    if value is None:
        return []
    if isinstance(value, (str, int, float)):
        return [value]
    return value


def _ocr_items(raw):
    """Yield (box, text, confidence) from PaddleOCR 3.x or 2.x output."""
    if raw is None:
        return
    pages = raw if isinstance(raw, list) else [raw]
    for page in pages:
        mapped = _paddle3_page(page)
        if mapped is not None:
            texts = _as_seq(mapped.get("rec_texts", mapped.get("rec_text")))
            scores = _as_seq(mapped.get("rec_scores", mapped.get("rec_score")))
            polys = mapped.get("rec_polys")
            if polys is None:
                polys = mapped.get("dt_polys")
            polys = _as_seq(polys)
            for i, text in enumerate(texts):
                score = scores[i] if i < len(scores) else 1.0
                box = polys[i] if i < len(polys) else None
                yield box, text, float(score if score is not None else 0.0)
            continue
        if page is None:
            continue
        # PaddleOCR 2.x: [[box, (text, conf)], ...]
        for line in page:
            if not line:
                continue
            box, payload = line[0], line[1]
            if isinstance(payload, (list, tuple)):
                text, confidence = payload[0], payload[1]
            else:
                text, confidence = payload, 1.0
            yield box, text, float(confidence)


def extract_text(pdf_path: Path) -> str:
    """Extract text from a PDF or invoice image.

    PDFs: layout-aware pdfplumber, then flat pdfplumber/pypdf.
    Images (.jpg/.png/…): full-page PaddleOCR (these GE rent samples are scans).
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    if path.suffix.lower() in _IMAGE_SUFFIXES:
        text = ocr_image(path)
        if text and text.strip():
            return text
        raise ValueError(f"OCR produced no text for image {path.name}")

    for extractor in (_try_pdfplumber_layout, _try_pdfplumber, _try_pypdf):
        text = extractor(path)
        if text and text.strip():
            return text

    # Scanned PDF with no text layer — OCR full first page
    text = ocr_pdf_page(path)
    if text and text.strip():
        return text

    raise ValueError(
        f"No extractable text in {path.name}. "
        "Install paddleocr (and paddlepaddle) for scanned invoices."
    )


def ocr_image(path: Path) -> str:
    """OCR a full invoice image into approximate reading-order text."""
    try:
        from PIL import Image

        img = Image.open(path).convert("RGB")
        # Upscale small phone/email crops so glyphs are readable
        longest = max(img.size)
        if longest < 1600:
            scale = 1600 / longest
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        return _ocr_result_to_text(_run_ocr(_to_bgr(img)))
    except Exception:  # noqa: BLE001
        return ""


def ocr_pdf_page(path: Path, page_index: int = 0) -> str:
    """Rasterise one PDF page and OCR it (for scan-only PDFs)."""
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            if page_index >= len(pdf.pages):
                return ""
            image = pdf.pages[page_index].to_image(resolution=_OCR_RESOLUTION).original
        return _ocr_result_to_text(_run_ocr(_to_bgr(image)))
    except Exception:  # noqa: BLE001
        return ""


def _ocr_result_to_text(result) -> str:
    rows: list[tuple[float, list[tuple[float, str]]]] = []
    for box, text, confidence in _ocr_items(result):
        if box is None or confidence < _MIN_OCR_CONFIDENCE:
            continue
        text = (text or "").strip()
        if not text:
            continue
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        y, x = min(ys), min(xs)
        if rows and abs(y - rows[-1][0]) < 18:
            rows[-1][1].append((x, text))
        else:
            rows.append((y, [(x, text)]))
    lines: list[str] = []
    for _, cells in rows:
        cells.sort()
        lines.append("  ".join(t for _, t in cells))
    return "\n".join(lines)


def _try_pdfplumber_layout(path: Path) -> str:
    """Rebuild page text from word coordinates instead of pdfplumber's flat reading order.

    Flat extraction collapses a 2D page into a 1D string, which merges unrelated columns
    and separates labels from the values printed beside them. Grouping words by their
    vertical position restores the visual rows a human sees.
    """
    try:
        import pdfplumber
    except ImportError:
        return ""

    parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
                if not words:
                    parts.append(page.extract_text() or "")
                    continue
                parts.append(_words_to_rows(words))
    except Exception:  # noqa: BLE001 - fall back to flat extraction
        return ""
    return "\n".join(parts)


def _words_to_rows(words: list[dict]) -> str:
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= _ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    lines: list[str] = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        line = row[0]["text"]
        for prev, cur in zip(row, row[1:]):
            gap = cur["x0"] - prev["x1"]
            line += ("  " if gap > _MIN_COLUMN_GAP else " ") + cur["text"]
        lines.append(line)
    return "\n".join(lines)


def _try_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _try_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def ocr_letterhead(pdf_path: Path) -> str | None:
    """Read the supplier brand out of a letterhead image via OCR.

    Some invoices carry a full text layer for the data but print the supplier's name only
    as a logo bitmap, so no amount of text parsing can recover it. This renders the top
    band of page 1 and keeps the visually prominent text, which is the brand: address and
    legal lines are set much smaller and get filtered out by height.

    Returns None if OCR is unavailable or nothing prominent was found.
    """
    lines = _ocr_band(pdf_path)
    if not lines:
        return None

    tallest = max(height for _, height, _ in lines)
    if tallest <= 0:
        return None

    prominent = sorted(
        (y, text)
        for y, height, text in lines
        if height / tallest >= _PROMINENT_HEIGHT_RATIO
    )
    name = " ".join(text for _, text in prominent[:_MAX_BRAND_LINES]).strip()
    return name[:160] or None


def _ocr_band(pdf_path: Path) -> list[tuple[float, float, str]]:
    """OCR the letterhead band, returning (y, text_height, text) per detection."""
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return []
            page = pdf.pages[0]
            band = (0, 0, page.width, page.height * _LETTERHEAD_BAND)
            image = page.crop(band).to_image(resolution=_OCR_RESOLUTION).original
        result = _run_ocr(_to_bgr(image))
    except Exception:  # noqa: BLE001 - OCR is best-effort
        return []

    lines: list[tuple[float, float, str]] = []
    for box, text, confidence in _ocr_items(result):
        if box is None or confidence < _MIN_OCR_CONFIDENCE:
            continue
        text = (text or "").strip()
        if not text:
            continue
        ys = [point[1] for point in box]
        lines.append((min(ys), max(ys) - min(ys), text))
    return lines
