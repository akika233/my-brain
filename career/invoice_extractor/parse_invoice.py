from __future__ import annotations

import re
from datetime import date as _Date
from datetime import datetime

from .models import InvoiceRecord

# ══════════════════════════════════════════════════════════════════════════════
# French month-name → int (abbreviated and full forms)
# ══════════════════════════════════════════════════════════════════════════════
_FR_MONTH: dict[str, int] = {
    "jan": 1, "janv": 1, "janvier": 1,
    "fev": 2, "fevr": 2, "fevrier": 2,
    "fév": 2, "févr": 2, "février": 2,
    "mar": 3, "mars": 3,
    "avr": 4, "avril": 4,
    "mai": 5,
    "jun": 6, "juin": 6,
    "jul": 7, "juil": 7, "juillet": 7,
    "aou": 8, "aoû": 8, "aout": 8, "août": 8,
    "sep": 9, "sept": 9, "septembre": 9,
    "oct": 10, "octobre": 10,
    "nov": 11, "novembre": 11,
    "dec": 12, "déc": 12, "decembre": 12, "décembre": 12,
}

# "06 fév. 2026"  /  "31 décembre 2025"  /  "23 févr. 2026"
_DATE_FR_TEXT = re.compile(
    r"(\d{1,2})\s+([a-z\u00c0-\u00ff]+\.?)\s+(\d{4})",
    re.IGNORECASE,
)

# Amount fragment (allows negative for credit notes; space / narrow-space as thousands sep)
_AMT = r"(-?[0-9]{1,3}(?:[ \u202f][0-9]{3})*[.,][0-9]{2}|-?[0-9]+[.,][0-9]{2})"

_CURRENCY_RE = re.compile(r"(€|EUR|USD|\$|GBP|£)")

# ══════════════════════════════════════════════════════════════════════════════
# Invoice number  (tried in priority order)
# ══════════════════════════════════════════════════════════════════════════════

# "Numéro de l'avoir FR554UKABEC"  —  credit notes; apostrophe may be ' or '
_INV_AVOIR = re.compile(
    r"(?i)num[ée]ro\s+de\s+l['\u2019]avoir\s+([A-Z0-9][A-Z0-9\-_/]{2,})"
)
# "Facture: CINVROU0002026000132"
_INV_FACTURE_COLON = re.compile(
    r"(?i)facture\s*:\s*([A-Z0-9][A-Z0-9\-_/]{3,})"
)
# "Facture N° 12345"  inline — value MUST start with a digit (avoids matching column headers)
_INV_FACTURE_N = re.compile(
    r"(?i)facture\s+n[°o.]\s*[:#]?\s*([0-9][A-Z0-9\-_/]{2,})"
)
# "Numéro F-2026-02-5295"  — bare Numéro, value starts with a letter; excludes "de/du/des"
_INV_NUMERO_BARE = re.compile(
    r"(?i)\bnum[ée]ro\s+(?!de\b|du\b|des\b)([A-Z][A-Z0-9\-_/]{2,})"
)
# "Notre référence …"
_INV_NOTRE_REF = re.compile(
    r"(?i)notre\s+r[ée]f[ée]rence\s*[:\-]?\s*(.+?)(?:\n|votre\s+r|$)"
)
# Generic English / Dutch / French labels
_INV_GENERIC = re.compile(
    r"(?i)(?:invoice\s*(?:number|no\.?|#)|factuur(?:nummer|nr\.?)?|"
    r"fact\.?\s*nr\.?|n[°o]\s*(?:de\s+)?facture|num[ée]ro\s+(?:de\s+)?facture)"
    r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/]{2,})"
)
# Tabular: "Facture N°  Date de Facture  …" header, invoice number + date on a later line.
# Uses DOTALL + non-greedy to skip address lines; stops at first NUMBER DATE pair.
_INV_TABLE = re.compile(
    r"(?i)facture\s+n[°o.].{0,400}?([0-9]{5,})\s+\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}",
    re.DOTALL,
)

# ══════════════════════════════════════════════════════════════════════════════
# Date  (tried in priority order)
# ══════════════════════════════════════════════════════════════════════════════

# Date value fragment: numeric DD/MM/YYYY  or textual "DD mois YYYY"
_DV = r"(\d{1,2}\s+[a-z\u00c0-\u00ff]+\.?\s+\d{4}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})"

# "Date d'émission", "Date d 'emission", "Date d'émission de l'avoir"
# Handles space-before-apostrophe PDF artifact via \s* between d and [apos]
_DATE_EMISSION = re.compile(
    r"(?i)date\s+d\s*['\u2019]?\s*[ée]mission"
    r"(?:\s+de\s+l['\u2019]avoir)?\s*[:\-]?\s*" + _DV
)
# "Date de la facture", "Date de facture", "Date Facture"
_DATE_FACTURE_LABEL = re.compile(
    r"(?i)date\s+(?:de\s+(?:la\s+)?)?facture\s*[:\-]?\s*" + _DV
)
# Simple "Date: 23 févr. 2026"  (only bare "Date:" — not "Date d'…" or "Date de…")
_DATE_BARE = re.compile(r"(?i)(?<![a-z])date\s*:\s*" + _DV)
# Tabular: same data line as invoice number
_DATE_TABLE = re.compile(
    r"(?i)facture\s+n[°o.].{0,400}?[0-9]{5,}\s+(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})",
    re.DOTALL,
)
# "Date de paiement" — last resort
_DATE_PAIEMENT = re.compile(
    r"(?i)date\s+de\s+paiement\s*[:\-]?\s*(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})"
)

# ══════════════════════════════════════════════════════════════════════════════
# Supplier
# ══════════════════════════════════════════════════════════════════════════════

# "Émetteur ou Émettrice\nMAKE AND MARK"  — value on the NEXT line
_EMETTEUR_NEXT = re.compile(
    r"(?i)[ée]metteur(?:\s+ou\s+[ée]mettrice)?\s*\n\s*(.+?)(?:\n|$)"
)
# "Émetteur: COMPANY"  — inline
_EMETTEUR_INLINE = re.compile(
    r"(?i)[ée]metteur(?:rice)?\s*[:\-]\s*(.+?)(?:\n|$)"
)
# "Vendu par COMPANY"
_VENDU_PAR = re.compile(r"(?i)vendu\s*par\s*[:\-]?\s*(.+?)(?:\n|$)")
# Company name followed by a legal-form suffix (line-anchored)
_COMPANY = re.compile(
    r"(?m)^([A-ZÁÉÍÓÚÄËÏÖÜÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]"
    r"[A-Za-zÁÉÍÓÚÄËÏÖÜáéíóúäëïöüàâæçéèêëîïôœùûüÿ0-9&.'\- ]{1,80}?"
    r"(?:\s+(?:B\.V\.|B\.V|BV|N\.V\.|N\.V|NV|"
    r"S\.à\.r\.l\.|S\.a\.r\.l\.|SARL|"
    r"Ltd\.?|GmbH|Inc\.?|LLC|VOF|CV|SAS|SA)))"
    r"(?:,\s*Succursale\s+Fran[çc]aise)?",
)

# ══════════════════════════════════════════════════════════════════════════════
# Amount — Total HT
# ══════════════════════════════════════════════════════════════════════════════

# "Montant Total HT 27 317,58"  /  "Total HT 580,00"  — value on SAME line
_TOTAL_HT_INLINE = re.compile(
    r"(?i)(?:montant\s+)?total\s+h\.?\s*t\.?\s*[:\-]?\s*(?:EUR|€)?\s*" + _AMT
)
# "Total HT :\n227,69"  — value on the NEXT line directly
_TOTAL_HT_NEXT = re.compile(
    r"(?i)total\s+h\.?\s*t\.?\s*[:\-]?\s*\n\s*(?:EUR|€)?\s*" + _AMT
)
# "Avoir total -9,98 €"  — credit-note grand total (used as HT fallback)
_AVOIR_TOTAL = re.compile(
    r"(?i)avoir\s+total\s*[:\-]?\s*(?:EUR|€)?\s*" + _AMT
)

# ══════════════════════════════════════════════════════════════════════════════
# Amount — VAT
# ══════════════════════════════════════════════════════════════════════════════

# "Total T.V.A. 5 463,52"  /  "Total TVA 116,00"  — same line
_TVA_INLINE = re.compile(
    r"(?i)total\s+t\.?v\.?a\.?\s*[:\-]?\s*(?:EUR|€)?\s*" + _AMT
)
# "Total TVA :\n45,54"  — next line
_TVA_NEXT = re.compile(
    r"(?i)total\s+t\.?v\.?a\.?\s*[:\-]?\s*\n\s*(?:EUR|€)?\s*" + _AMT
)
# Detail row: "20% TVA_amt HT_base"  or  "20% HT_base TVA_amt" (column order varies).
# We compare the two amounts: the SMALLER absolute value is TVA, the LARGER is HT.
_TVA_DETAIL_ROW = re.compile(
    r"(?i)(\d{1,2}(?:[,.]\d)?)\s*%\s+(?:EUR|€)?\s*"
    r"(-?[0-9]+[.,][0-9]{2})\s*(?:EUR|€)?\s+"
    r"(?:EUR|€)?\s*(-?[0-9]+[.,][0-9]{2})"
)
# Three consecutive standalone decimal lines: HT  /  VAT  /  TTC
# Matches layouts where labeled totals appear in a separate column (Cleaning invoice style)
_TOTALS_BLOCK = re.compile(
    r"(?m)^ *(-?[0-9]+[.,][0-9]{2}) *$\n"
    r"^ *(-?[0-9]+[.,][0-9]{2}) *$\n"
    r"^ *(-?[0-9]+[.,][0-9]{2}) *$"
)
# Generic fallback: bare "TVA" / "T.V.A." followed by amount (not intracom number)
_TVA_FALLBACK = re.compile(
    r"(?i)t\.?v\.?a\.?\b(?!\s*intra)[^\d€EUR\n]{0,30}(?:EUR|€)?\s*" + _AMT
)
_TVA_RATE = re.compile(
    r"(?i)(?:tva|vat|btw|t\.v\.a\.?)\s*(?:@|à\s*)?(\d{1,2}(?:[.,]\d{1,2})?)\s*%"
)

# ══════════════════════════════════════════════════════════════════════════════
# Amount — generic fallback
# ══════════════════════════════════════════════════════════════════════════════

_AMOUNT_GENERIC = re.compile(
    r"(?i)(?:total\s*(?:amount|due|ttc)?|totaal(?:bedrag)?|"
    r"montant\s*total|amount\s*due|grand\s*total|eindbedrag)\s*[:#]?\s*"
    r"(?:EUR|€)?\s*" + _AMT
)

# ══════════════════════════════════════════════════════════════════════════════
# PO number
# ══════════════════════════════════════════════════════════════════════════════

_VOTRE_REF = re.compile(
    r"(?i)votre\s+r[ée]f[ée]rence\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-_/]*)"
)
# "COMMANDE N° PO 20251013"  /  "N° PO XXXX"  /  "purchase order …"
_PO_LABEL = re.compile(
    r"(?i)(?:commande\s+n[°o]?\s+po|n[°o]\s+po|"
    r"(?:purchase\s*)?order(?:\s*number|\s*no\.?|\s*#)?|"
    r"po\s*(?:number|no\.?|#)?|inkooporder(?:nummer|nr\.?)?)"
    r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-_/]{2,})"
)
# "Numéro de commande client Parly II - 20250017"  → trailing numeric code
_PO_CMD_CLIENT = re.compile(
    r"(?i)num[ée]ro\s+de\s+(?:la\s+)?commande\s+client[^\n]*[-\s](\d{6,10})\b"
)
# Bare pattern: "POR12345"  or  year-prefixed "2025XXXXX" (no label required)
_PO_PATTERN = re.compile(r"\b(POR\d{5}|20[2-9]\d{5,6})\b")


# ══════════════════════════════════════════════════════════════════════════════
# Main parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_invoice_text(text: str, source_file: str) -> InvoiceRecord:
    notes: list[str] = []
    cleaned = _normalize(text)

    # ── Invoice number ────────────────────────────────────────────────────────
    invoice_number = (
        _first(_INV_AVOIR, cleaned)            # "Numéro de l'avoir XXXX"
        or _first(_INV_FACTURE_COLON, cleaned) # "Facture: XXXX"
        or _first(_INV_FACTURE_N, cleaned)     # "Facture N° 12345" inline (digit-first)
        or _first(_INV_NUMERO_BARE, cleaned)   # "Numéro F-XXXX"
        or _clean_ref(_first(_INV_NOTRE_REF, cleaned))
        or _first(_INV_GENERIC, cleaned)
        or _first(_INV_TABLE, cleaned)         # tabular multi-line layout
    )

    # ── PO number ─────────────────────────────────────────────────────────────
    po_number = (
        _first(_VOTRE_REF, cleaned)
        or _first(_PO_LABEL, cleaned)
        or _first(_PO_CMD_CLIENT, cleaned)
    )
    if not po_number:
        m = _PO_PATTERN.search(cleaned)
        if m:
            po_number = m.group(1)
            notes.append("po_number from pattern scan")

    # ── Date ──────────────────────────────────────────────────────────────────
    raw_date = (
        _first(_DATE_EMISSION, cleaned)
        or _first(_DATE_FACTURE_LABEL, cleaned)
        or _first(_DATE_BARE, cleaned)
        or _first(_DATE_TABLE, cleaned)
        or _first(_DATE_PAIEMENT, cleaned)
    )
    invoice_date = _parse_date(raw_date)

    # ── Supplier ──────────────────────────────────────────────────────────────
    supplier = _extract_supplier(cleaned)

    # ── Currency ──────────────────────────────────────────────────────────────
    currency = _first(_CURRENCY_RE, cleaned)
    if currency in {"€", "$", "£"}:
        currency = {"€": "EUR", "$": "USD", "£": "GBP"}[currency]
    currency = currency or "EUR"

    # ── Amount (Total HT) + VAT amount ───────────────────────────────────────
    amount: float | None = None
    vat_amount: float | None = None

    # 1. Labeled Total HT on the same line
    amount = _to_float(_first(_TOTAL_HT_INLINE, cleaned))
    if amount is not None:
        notes.append("amount from Total HT (inline)")

    # 2. Labeled Total HT with value on the next line
    if amount is None:
        amount = _to_float(_first(_TOTAL_HT_NEXT, cleaned))
        if amount is not None:
            notes.append("amount from Total HT (next line)")

    # 3. Labeled Total TVA (inline / next line) — try before detail row
    vat_amount = (
        _to_float(_first(_TVA_INLINE, cleaned))
        or _to_float(_first(_TVA_NEXT, cleaned))
    )

    # 4. TVA detail row "20% amt1 amt2" — smaller abs = VAT, larger abs = HT
    if amount is None or vat_amount is None:
        m_row = _TVA_DETAIL_ROW.search(cleaned)
        if m_row:
            a1 = _to_float(m_row.group(2))
            a2 = _to_float(m_row.group(3))
            if a1 is not None and a2 is not None:
                ht_val = a1 if abs(a1) >= abs(a2) else a2
                tv_val = a2 if abs(a1) >= abs(a2) else a1
                if amount is None:
                    amount = ht_val
                    notes.append("amount from TVA detail row (HT base)")
                if vat_amount is None:
                    vat_amount = tv_val
                    notes.append("vat_amount from TVA detail row")

    # 5. Three consecutive standalone decimal lines → HT / VAT / TTC
    if amount is None or vat_amount is None:
        m_block = _TOTALS_BLOCK.search(cleaned)
        if m_block:
            if amount is None:
                amount = _to_float(m_block.group(1))
                notes.append("amount from standalone totals block")
            if vat_amount is None:
                vat_amount = _to_float(m_block.group(2))
                notes.append("vat_amount from standalone totals block")

    # 6. Credit-note "Avoir total" (used as HT fallback)
    if amount is None:
        amount = _to_float(_first(_AVOIR_TOTAL, cleaned))
        if amount is not None:
            notes.append("amount from Avoir total")

    # 7. Generic total label
    if amount is None:
        amount = _to_float(_first(_AMOUNT_GENERIC, cleaned))

    # 8. Last currency figure in document
    if amount is None:
        pairs = re.findall(
            r"(?:EUR|€)\s*(-?[0-9]+[.,][0-9]{2})|(-?[0-9]+[.,][0-9]{2})\s*(?:EUR|€)",
            cleaned, flags=re.I,
        )
        flat = [a or b for a, b in pairs]
        if flat:
            amount = _to_float(flat[-1])
            notes.append("amount inferred from last currency figure")

    # 9. Generic TVA fallback
    if vat_amount is None:
        vat_amount = _to_float(_first(_TVA_FALLBACK, cleaned))

    # ── VAT rate ──────────────────────────────────────────────────────────────
    vat_rate = _to_float(_first(_TVA_RATE, cleaned))
    if vat_rate is None and amount and vat_amount and amount != 0:
        vat_rate = round(abs(vat_amount) / abs(amount) * 100, 2)
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


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

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
    raw = re.split(r"\s{2,}|\t", raw.strip())[0].strip()
    raw = re.sub(r"\s+", " ", raw)
    return raw[:120] if raw else None


def _to_float(raw: str | None) -> float | None:
    if not raw:
        return None
    s = raw.strip().replace(" ", "").replace("\u202f", "")
    negative = s.startswith("-")
    s = s.lstrip("-")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        s = s.replace(",", ".") if len(parts[-1]) == 2 else s.replace(",", "")
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def _parse_date(raw: str | None) -> str | None:
    """Parse a date string that may use French month names or numeric formats."""
    if not raw:
        return None
    raw = raw.strip()

    # Try French textual: "06 fév. 2026", "31 décembre 2025", "23 févr. 2026"
    m = _DATE_FR_TEXT.match(raw) or _DATE_FR_TEXT.search(raw)
    if m:
        day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
        key = month_s.rstrip(".").lower()
        month_num = _FR_MONTH.get(key)
        if month_num:
            try:
                return _Date(int(year_s), month_num, int(day_s)).isoformat()
            except ValueError:
                pass

    # Numeric formats
    for fmt in (
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
    ):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue

    return raw  # return as-is if nothing parses


def _extract_supplier(text: str) -> str | None:
    # "Émetteur ou Émettrice\nCOMPANY NAME"  — value on next line
    m = _EMETTEUR_NEXT.search(text)
    if m:
        val = m.group(1).strip(" ,")
        # Skip if the next line is another label (e.g. "Client ou Cliente")
        if val and not re.match(r"(?i)^(client|cliente|n[°o]|adresse|email|phone|\+)", val):
            return val[:160]

    # "Émetteur: COMPANY"  — inline
    m = _EMETTEUR_INLINE.search(text)
    if m:
        return m.group(1).strip(" ,")[:160]

    # "Vendu par COMPANY"
    m = _VENDU_PAR.search(text)
    if m:
        return m.group(1).strip(" ,")[:160]

    # Heuristic: first company name with a recognized legal-form suffix, excluding New Balance
    companies = [c.group(0).strip().rstrip(",") for c in _COMPANY.finditer(text)]
    companies = [c for c in companies if "new balance" not in c.lower()]
    if companies:
        return companies[0][:160]

    return None
