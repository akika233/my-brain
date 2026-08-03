from __future__ import annotations

import re
from datetime import datetime

from .models import InvoiceRecord

# ── French New Balance invoice labels ─────────────────────────────────
_VENDU_PAR = re.compile(
    r"(?i)vendu\s*par\s*[:\-]?\s*(.+?)(?:\n|$)",
)
_NOTRE_REF = re.compile(
    r"(?i)(?:notre\s+r[ée]f[ée]rence|"
    r"num[ée]ro\s+de\s+commande\s+client|"
    r"n[°o]\s*de\s+commande\s+client)\s*[:\-]?\s*(.+?)(?:\n|votre\s+r|$)",
)
_VOTRE_REF = re.compile(
    r"(?i)votre\s+r[ée]f[ée]rence\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]*)",
)
_DATE_FACTURE = re.compile(
    r"(?i)(?:date\s+de\s+la\s+facture|date\s+d['\u2019][\u00e9e]mission)\s*[:\-]?\s*"
    r"(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})",
)
_DATE_PAIEMENT = re.compile(
    r"(?i)date\s+de\s+paiement\s*[:\-]?\s*"
    r"(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})",
)
_TOTAL_HT = re.compile(
    r"(?i)(?:total\s*h\.?\s*t\.?|avoir\s*total)\b[^\d€EUR]{0,40}"
    r"(?:EUR|€)?\s*([0-9]{1,3}(?:[\s.\u202f][0-9]{3})*[.,][0-9]{2}|[0-9]+[.,][0-9]{2})",
)
_TVA_AMOUNT = re.compile(
    r"(?i)(?:tva|vat)\b(?!\s*intra)[^\d€EUR]{0,40}"
    r"(?:EUR|€)?\s*([0-9]{1,3}(?:[\s.\u202f][0-9]{3})*[.,][0-9]{2}|[0-9]+[.,][0-9]{2})",
)
_TVA_RATE = re.compile(
    r"(?i)(?:tva|vat|btw)\s*(?:à\s*)?(\d{1,2}(?:[.,]\d{1,2})?)\s*%",
)
# Company on left / letterhead (NL + FR legal forms)
_COMPANY = re.compile(
    r"(?m)^([A-ZÁÉÍÓÚÄËÏÖÜÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]"
    r"[A-Za-zÁÉÍÓÚÄËÏÖÜáéíóúäëïöüàâæçéèêëîïôœùûüÿ0-9&.'\- ]{1,80}?"
    r"(?:\s+(?:B\.V\.|B\.V|BV|N\.V\.|N\.V|NV|"
    r"S\.à\.r\.l\.|S\.a\.r\.l\.|SARL|"
    r"Ltd\.?|GmbH|Inc\.?|LLC|VOF|CV|SAS|SA)))"
    r"(?:,\s*Succursale\s+Fran[çc]aise)?",
)

# ── English / Dutch fallbacks ─────────────────────────────────────────
_INV_NO = re.compile(
    r"(?i)(?:invoice\s*(?:number|no\.?|#)|factuur(?:nummer|nr\.?)?|"
    r"fact\.?\s*nr\.?|n[°o]\s*(?:de\s+)?facture|num[ée]ro\s+(?:de\s+)?facture)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
)
_DATE_GENERIC = re.compile(
    r"(?i)(?:invoice\s*date|factuurdatum|datum\s*factuur)\s*[:#]?\s*"
    r"(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
)
_PO = re.compile(
    r"(?i)(?:(?:purchase\s*)?order(?:\s*number|\s*no\.?|\s*#)?|"
    r"po\s*(?:number|no\.?|#)?|inkooporder(?:nummer|nr\.?)?)\s*[:#]?\s*"
    r"([A-Z0-9][A-Z0-9\-_/]{2,})",
)
_AMOUNT_TOTAL = re.compile(
    r"(?i)(?:total\s*(?:amount|due|ttc)?|totaal(?:bedrag)?(?:\s*incl\.?\s*(?:btw|vat))?|"
    r"montant\s*total|amount\s*due|te\s*betalen|grand\s*total|eindbedrag)\s*[:#]?\s*"
    r"(?:EUR|€)?\s*([0-9]{1,3}(?:[.,\s][0-9]{3})*[.,][0-9]{2}|[0-9]+[.,][0-9]{2})",
)
_CURRENCY = re.compile(r"(€|EUR|USD|\$|GBP|£)")


def parse_invoice_text(text: str, source_file: str) -> InvoiceRecord:
    notes: list[str] = []
    cleaned = _normalize(text)

    # Notre référence → invoice_number; Votre référence → po_number
    invoice_number = _clean_ref(_first(_NOTRE_REF, cleaned)) or _first(_INV_NO, cleaned)
    po_number = _first(_VOTRE_REF, cleaned) or _first(_PO, cleaned)

    raw_date = (
        _first(_DATE_FACTURE, cleaned)
        or _first(_DATE_PAIEMENT, cleaned)
        or _first(_DATE_GENERIC, cleaned)
    )
    if _first(_DATE_FACTURE, cleaned):
        notes.append("date from Date de la facture")
    elif _first(_DATE_PAIEMENT, cleaned):
        notes.append("date from Date de Paiement")
    invoice_date = _normalize_date(raw_date)

    supplier = _extract_supplier(cleaned)
    currency = _first(_CURRENCY, cleaned)
    if currency in {"€", "$", "£"}:
        currency = {"€": "EUR", "$": "USD", "£": "GBP"}[currency]
    currency = currency or "EUR"

    amount = _to_float(_first(_TOTAL_HT, cleaned))
    if amount is not None:
        lbl = "Avoir total" if re.search(r"(?i)avoir\s+total", cleaned) else "Total HT"
        notes.append(f"amount from {lbl}")
    else:
        amount = _to_float(_first(_AMOUNT_TOTAL, cleaned))

    vat_amount = _to_float(_first(_TVA_AMOUNT, cleaned))
    vat_rate = _to_float(_first(_TVA_RATE, cleaned))

    if amount is None:
        amounts = re.findall(
            r"(?:EUR|€)\s*([0-9]{1,3}(?:[\s.\u202f][0-9]{3})*[.,][0-9]{2}|[0-9]+[.,][0-9]{2})"
            r"|([0-9]+[.,][0-9]{2})\s*(?:EUR|€)",
            cleaned,
            flags=re.I,
        )
        flat = [a or b for a, b in amounts]
        if flat:
            amount = _to_float(flat[-1])
            notes.append("amount inferred from last currency figure")

    # Worldpack-style: bare decimal near bottom when no Total HT
    if amount is None:
        bare = re.findall(r"(?m)^\s*([0-9]+[.,][0-9]{2})\s*$", cleaned)
        if bare:
            amount = _to_float(bare[-1])
            notes.append("amount from bare total line")

    if vat_rate is None and amount is not None and vat_amount is not None and amount > 0:
        vat_rate = round(vat_amount / amount * 100, 2)
        notes.append("vat_rate derived from TVA / Total HT")

    excerpt = cleaned[:800].replace("\n", " | ")

    return InvoiceRecord(
        source_file=source_file,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        supplier=supplier,
        amount=amount,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        po_number=po_number,
        currency=currency,
        raw_excerpt=excerpt,
        parse_notes="; ".join(notes) if notes else None,
    )


def _normalize(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _clean_ref(raw: str | None) -> str | None:
    if not raw:
        return None
    # Drop trailing French label fragments on same line
    raw = re.split(r"\s{2,}|\t", raw.strip())[0].strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw[:120] if raw else None


def _to_float(raw: str | None) -> float | None:
    if not raw:
        return None
    s = raw.strip().replace(" ", "").replace("\u202f", "")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", ".") if len(parts[-1]) == 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in (
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d.%m.%y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _extract_supplier(text: str) -> str | None:
    # Prefer "Vendu par" (Amazon-style)
    vendu = _first(_VENDU_PAR, text)
    if vendu:
        return vendu.strip(" ,")[:160]

    companies = [m.group(0).strip().rstrip(",") for m in _COMPANY.finditer(text)]
    # Skip New Balance buyer entity if present
    companies = [c for c in companies if "new balance" not in c.lower()]
    if companies:
        return companies[0][:160]
    return None
