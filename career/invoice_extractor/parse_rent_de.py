"""German / English commercial-rent invoice parsing.

Covers landlord layouts seen in NB Germany outlet/mall rent scans:
Mindestmiete / Basismiete / Rental income, Nebenkosten / Service Charge,
Umsatzmiete / turnover rent, plus service periods (Zeitraum).
"""
from __future__ import annotations

import re
from datetime import datetime

from .models import InvoiceRecord

# Prefer thousand-grouped forms; forbid trailing digits so "12,852.00" is not "12,85"
_AMT = (
    r"(-?"
    r"(?:"
    r"[0-9]{1,3}(?:\.[0-9]{3})+,[0-9]{2}"  # 45.881,17
    r"|[0-9]{1,3}(?:,[0-9]{3})+\.[0-9]{2}"  # 10,800.00
    r"|[0-9]{1,3}(?:\.[0-9]{3})+\.[0-9]{2}"  # OCR 21.294.95
    r"|[0-9]+[.,][0-9]{2}"  # 803,52
    r")"
    r")(?![0-9])"
)

_DE_MONTH = {
    "januar": 1, "jan": 1, "january": 1,
    "februar": 2, "feb": 2, "february": 2,
    "maerz": 3, "märz": 3, "marz": 3, "mar": 3, "march": 3, "mär": 3,
    "april": 4, "apr": 4,
    "mai": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12, "december": 12, "dec": 12,
}

_MONTH_ALT = "|".join(sorted(_DE_MONTH.keys(), key=len, reverse=True))

_BASIC_RE = re.compile(
    r"(?i)("
    r"mindestmiete(?:\s*nfl\.?|\s*nebenfl[aä]che)?"
    r"|monatsmiete"
    r"|basismiete"
    r"|basis\s*miete"
    r"|kaltmiete"
    r"|mietrechnung(?:\s*\d+/\d+tel)?"
    r"|miete(?:gew\.?)?(?:\s*hauptfl\.?)?"
    r"|rental\s*income(?:\s*[-–]\s*retail)?"
    r")"
)

_SERVICE_RE = re.compile(
    r"(?i)("
    r"nebenkosten(?:vorauszahlung|pauschale)?"
    r"|nebenkosten\s*vz"
    r"|vz\s*nk"
    r"|pauschale\s*nk"
    r"|nk\s*verm"
    r"|service\s*charge(?:\s*income(?:\s*from\s*tenants)?)?"
    r"|betriebskosten"
    r"|vz\s*abwasser"
    r")"
)

_MARKETING_RE = re.compile(
    r"(?i)("
    r"marketing(?:beitrag|kosten|charge|charges)?"
    r"|werbe(?:kosten|beitrag|umlage)"
    r"|promotion(?:al)?\s*(?:charge|fee|kosten)?"
    r")"
)

_TURNOVER_RE = re.compile(
    r"(?i)(umsatzmiete|turnover\s*rent|percentage\s*rent)"
)

_STORAGE_RE = re.compile(
    r"(?i)(storage(?:\s*(?:income|services|miete))?|lager(?:miete|/container)?|lagercontainer)"
)

_BAD_SUPPLIER = re.compile(
    r"(?i)^(bezeichnung|betrag|beschreibung|position|endbetrag|rechnungsbetrag|"
    r"netto|mwst|ust|gesamt|kategorie|zeitraum|ihr\s*vertrag|new\s*balance|"
    r"rechnung|datum|nummer|summe|steuersatz|steuerpflichtiger)\b"
)


def looks_like_german_rent(text: str) -> bool:
    t = text.lower()
    compact = re.sub(r"\s+", "", t)
    needles = (
        "mindestmiete", "monatsmiete", "basismiete", "nebenkosten",
        "umsatzmiete", "mietrechnung", "dauermietrechnung", "rechnungsbetrag",
        "rentalincome", "servicecharge", "endbetrag", "zeitraum",
        "vermieter", "mietobjekt", "turnoverrent", "umsatzsteuer",
        "nettobetrag", "gesamtbrutto", "gesamtnetto", "lager/", "storage",
        "gutschrift", "rechnungsnummer", "mwst",
    )
    hits = sum(1 for n in needles if n in compact or n in t)
    return hits >= 2


def parse_german_rent_invoice(text: str, source_file: str) -> InvoiceRecord:
    notes: list[str] = []
    cleaned = _normalize(text)

    invoice_number = _extract_invoice_number(cleaned)
    invoice_date = _extract_invoice_date(cleaned)
    supplier = _extract_supplier(cleaned)
    po_number = _extract_po(cleaned)
    contract_number = _extract_contract(cleaned)

    amount_gross, amount_net, vat_amount, vat_rate = _extract_totals(cleaned)
    basic, service, marketing, turnover, storage = _sum_charge_categories(cleaned)
    periods = _extract_periods(cleaned)
    period_str = ";".join(periods) if periods else None
    year = month = None
    if periods:
        try:
            year_s, month_s = periods[0].split("-")
            year, month = int(year_s), int(month_s)
        except ValueError:
            pass

    if year is None or month is None:
        m = re.search(
            rf"(?i)(?:mietrechnung\s*)?f[uü]r\s*({_MONTH_ALT})\s*(\d{{4}})",
            cleaned,
        ) or re.search(rf"(?i)({_MONTH_ALT})(\d{{4}})", cleaned)
        if m:
            month = _month_num(m.group(1))
            year = int(m.group(2))
            if period_str is None and year and month:
                period_str = f"{year:04d}-{month:02d}"

    problems: list[str] = []
    if not invoice_number:
        problems.append("invoice_number missing")
    if not invoice_date:
        problems.append("invoice_date missing")
    if not supplier:
        problems.append("supplier missing")
    if amount_gross is None and amount_net is None:
        problems.append("amount missing")
    if all(v is None for v in (basic, service, marketing, turnover, storage)):
        problems.append("no rent/service line items matched")

    if amount_net is not None and vat_amount is not None and amount_gross is not None:
        expected = round(amount_net + vat_amount, 2)
        if abs(expected - amount_gross) > 0.05:
            problems.append(f"net+VAT ({expected}) != gross ({amount_gross})")

    amount = amount_gross if amount_gross is not None else amount_net

    if basic is not None:
        notes.append(f"basic_rent={basic}")
    if service is not None:
        notes.append(f"service_charges={service}")
    if marketing is not None:
        notes.append(f"marketing_charges={marketing}")
    if turnover is not None:
        notes.append(f"turnover_rent={turnover}")
    if storage is not None:
        notes.append(f"storage_charges={storage}")

    return InvoiceRecord(
        source_file=source_file,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        supplier=supplier,
        amount=amount,
        amount_net=amount_net,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        po_number=po_number,
        contract_number=contract_number,
        currency="EUR",
        basic_rent=basic,
        service_charges=service,
        marketing_charges=marketing,
        turnover_rent=turnover,
        storage_charges=storage,
        service_period=period_str,
        service_year=year,
        service_month=month,
        needs_review=bool(problems),
        validation="; ".join(problems) if problems else None,
        raw_excerpt=cleaned[:500],
        parse_notes="; ".join(notes) if notes else "german_rent",
    )


def _normalize(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u202f", " ")
    # Only unglue a few known OCR joins — do NOT split every camel boundary
    # (that breaks Rechnungsnummer / GmbH / Rechnungsbetrag).
    replacements = [
        (r"(?i)dauermietrechnung(?=ab|g)", "Dauermietrechnung "),
        (r"(?i)mietrechnung(?=fur|für)", "Mietrechnung "),
        (r"(?i)rechnungsnummer", "Rechnungsnummer"),
        (r"(?i)rechnungsbetrag", "Rechnungsbetrag"),
        (r"(?i)rechnungsnr", "Rechnungsnr"),
        (r"(?i)nebenkostenvorauszahlung", "Nebenkostenvorauszahlung"),
        (r"(?i)nebenkostenpauschale", "Nebenkostenpauschale"),
        (r"(?i)basismiete(?=fur|für)", "Basismiete "),
        (r"(?i)gesamtbrutto", "Gesamt Brutto "),
        (r"(?i)gesamtnetto", "Gesamt Netto "),
        (r"(?i)rentalincome", "Rental income"),
        (r"(?i)servicechargeincome", "Service Charge Income"),
        (r"(?i)storageincome", "Storage Income"),
        (r"(?i)mitfreundlichen", "Mit freundlichen "),
    ]
    for pat, repl in replacements:
        text = re.sub(pat, repl, text)
    text = re.sub(r"[ \t]{2,}", "  ", text)
    return text.strip()


def _month_num(raw: str) -> int | None:
    key = raw.lower().strip(".")
    return _DE_MONTH.get(key) or _DE_MONTH.get(key.replace("ä", "ae").replace("ö", "oe"))


def _parse_amount(raw: str) -> float | None:
    s = raw.strip().replace(" ", "").replace("€", "").replace("EUR", "")
    if not s:
        return None
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    # OCR Endbetrag 21.294.95 (dots as thousands + decimal)
    if re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+\.[0-9]{2}", s):
        parts = s.split(".")
        val = float("".join(parts[:-1]) + "." + parts[-1])
        return -val if neg else val
    if re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{3})+,[0-9]{2}", s):
        val = float(s.replace(".", "").replace(",", "."))
        return -val if neg else val
    if re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+\.[0-9]{2}", s):
        val = float(s.replace(",", ""))
        return -val if neg else val
    if re.fullmatch(r"[0-9]+,[0-9]{2}", s):
        val = float(s.replace(",", "."))
        return -val if neg else val
    if re.fullmatch(r"[0-9]+\.[0-9]{2}", s):
        val = float(s)
        return -val if neg else val
    try:
        val = float(s.replace(",", "."))
        return -val if neg else val
    except ValueError:
        return None


def _line_net_amount(amounts: list[float]) -> float:
    """Pick the net figure from a line that may also show VAT% / VAT / gross."""
    if len(amounts) >= 3:
        # net, (rate?), vat, gross  → first is net
        # skip a lone "19.00" rate if present as second value
        if abs(amounts[1]) in (19.0, 19.00) or 18.5 <= abs(amounts[1]) <= 20.0:
            return amounts[0]
        return amounts[0]
    if len(amounts) == 2:
        a, b = amounts
        # vat + net (URW): smaller ~19% of larger
        hi, lo = (a, b) if abs(a) >= abs(b) else (b, a)
        if abs(hi) > 1 and abs(abs(lo / hi) - 0.19) < 0.03:
            return hi
        return b  # EUR/netto often last
    return amounts[0]


def _extract_invoice_number(text: str) -> str | None:
    patterns = [
        r"(?i)rechnungs(?:nummer|nr\.?)\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{1,})",
        r"(?i)rechnung\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)rechnungsnr\.?\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)\bnummer\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)invoice\s*(?:number|no\.?|#)\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
        r"(?i)\brechnung\s*(\d{6,})",
        r"(?i)rechnung\s*s?\s*nummer\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{1,})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip().rstrip(".,;")
    # Glued "Rechnung:GA02INV202600673"
    m = re.search(r"(?i)rechnung\s*:\s*([A-Z]{2,}\d[A-Z0-9\-_/]+)", text)
    if m:
        return m.group(1)
    return None


def _extract_invoice_date(text: str) -> str | None:
    patterns = [
        r"(?i)\bdatum\s*[:：]\s*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
        r"(?i)\bdatum\s*[:：]?\s*(\d{1,2}\.\s*[A-Za-zäöüÄÖÜ]+\s+\d{4})",
        r"(?i)(?:d[uü]sseldorf|berlin|m[uü]nchen|hamburg|frankfurt|metzingen)[,\s]+(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
        r"(?i)datum\s+(\d{1,2}/\d{1,2}/\d{4})",
        r"(?i)\bdatum\s*[:：]?\s*(\d{1,2})\.\s*(" + _MONTH_ALT + r")\s+(\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        if m.lastindex == 3 and not m.group(1)[0].isdigit():
            continue
        if m.lastindex >= 3 and m.group(2) and m.group(2)[0].isalpha():
            mon = _month_num(m.group(2))
            if mon:
                return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
        return _normalize_date(m.group(1))

    m = re.search(rf"(?i)\b(\d{{1,2}})\.\s*({_MONTH_ALT})\s+(\d{{4}})\b", text)
    if m:
        mon = _month_num(m.group(2))
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
    return None


def _normalize_date(raw: str) -> str | None:
    raw = raw.strip()
    m = re.match(rf"(?i)(\d{{1,2}})\.\s*({_MONTH_ALT})\s+(\d{{4}})", raw)
    if m:
        mon = _month_num(m.group(2))
        if mon:
            return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})", raw)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            return None
    return None


def _extract_supplier(text: str) -> str | None:
    # Known landlords (OCR-robust) first
    known = [
        (r"(?i)neue\s*mit+e?\s*oberhausen|projektentwicklung\s*l", "Neue Mitte Oberhausen Projektentwicklung Ltd. & Co. KG"),
        (r"(?i)outletcity", "OUTLETCITY AG"),
        (r"(?i)neumuenster\s*designer\s*outlet|neumünster\s*designer|mcarthurglen", "Neumuenster Designer Outlet GmbH"),
        (r"(?i)frey\s*berlin", "FREY Berlin OpCo GmbH"),
        (r"(?i)m[uü]llmann", "Dr. Rolf und Michaela Müllmann"),
        (r"(?i)zeppelin", "Zeppelin Rental / Zeppelin"),
        (r"(?i)wertheim\s*village", "Wertheim Village"),
        (r"(?i)zweibr[uü]cken\s*fashion\s*outlet|bezug:\s*zweibr", "Zweibrucken Fashion Outlet"),
        (r"(?i)urw\.com|mfi\s*shopping\s*center", "Neue Mitte Oberhausen Projektentwicklung Ltd. & Co. KG"),
    ]
    for pat, name in known:
        if re.search(pat, text):
            return name

    if re.search(r"(?i)gutschrift|special\s*credit", text) and re.search(
        r"(?i)rental\s*income|mcarthurglen|designer\s*outlet", text
    ):
        return "Neumuenster Designer Outlet GmbH"

    patterns = [
        r"(?i)rechnung\s+der\s+([^\n]{3,80})",
        r"(?i)eigent[uü]merin\s*vermieterin\s*:\s*([^\n]{3,80})",
        r"(?i)(?:vermieter(?:in)?|landlord)\s*[:：]\s*([^\n]{3,80})",
        r"(?i)mit\s*freundlichen\s*gr[uü][sß]en\s*\n?\s*([^\n]{3,80})",
        r"(?i)kontoinhaber\s+([^\n]{3,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = _clean_company(m.group(1))
            if name:
                return name

    legal = re.compile(
        r"(?i)\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 &.\-]{2,60}?"
        r"(?:GmbH|Ltd\.?\s*&?\s*Co\.?\s*KG|AG|KG))\b"
    )
    for m in legal.finditer(text):
        name = _clean_company(m.group(1))
        if name:
            return name[:160]
    return None


def _clean_company(name: str) -> str | None:
    name = re.sub(r"(?i)rechnungsnummer\s*:\s*\d+\s*", "", name)
    name = re.sub(r"\s+", " ", name).strip(" ,;:")
    if len(name) < 3 or _BAD_SUPPLIER.search(name):
        return None
    if re.search(r"(?i)new\s*balance|plange|kreditor|beschreibung|bezeichnung", name):
        return None
    return name[:160]


def _extract_po(text: str) -> str | None:
    patterns = [
        r"(?i)bestell(?:nummer|nr\.?|-nr\.?)\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
        r"(?i)po\s*nr\.?\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
        r"(?i)bestell-nr\.\s*:\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
        r"(?i)purchase\s*order\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{2,})",
        r"(?i)po\s*nr\.?\s*[:：]{1,2}\s*([0-9]{5,})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip()
            if len(val) >= 4 and val.lower() not in {"nr", "ponr", "fallig", "fällig"}:
                return val
    return None


def _extract_contract(text: str) -> str | None:
    patterns = [
        r"(?i)vertrags?nr\.?\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)vertrag\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)mietvertrag\s*[:：]\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)lease\s*i[dD]\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
        r"(?i)ihr\s*vertrag\s*[:：]?\s*([A-Z0-9][A-Z0-9\-_/]{3,})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip().rstrip(".,;")
            if val.lower().startswith("vom"):
                continue
            return val
    return None


def _extract_totals(
    text: str,
) -> tuple[float | None, float | None, float | None, float | None]:
    gross = net = vat = rate = None

    for pat in (
        rf"(?i)rechnungsbetrag\s*\(?\s*brutto\s*\)?\s*{_AMT}",
        rf"(?i)endbetrag\s*[:：]?\s*{_AMT}",
        rf"(?i)gesamt\s*brutto\s*(?:EUR)?\s*{_AMT}",
        rf"(?i)gesamt\s*:\s*{_AMT}\s+{_AMT}\s+{_AMT}",
        rf"(?i)rechnungsbetrag\s*(?:\(EUR\))?\s*{_AMT}",
        rf"(?i)gesamt\s*(?:je\s*monat|vertrag)[^\n]{{0,20}}{_AMT}\s+{_AMT}",
        rf"(?i)gesamtbetrag\s*{_AMT}",
    ):
        m = re.search(pat, text)
        if m:
            if m.lastindex and m.lastindex >= 3:
                net = _parse_amount(m.group(1))
                vat = _parse_amount(m.group(2))
                gross = _parse_amount(m.group(3))
            elif m.lastindex == 2 and gross is None and "gesamt" in m.group(0).lower():
                # Gesamtje Monat net brutto
                a, b = _parse_amount(m.group(1)), _parse_amount(m.group(2))
                if a is not None and b is not None:
                    net = min(a, b, key=abs) if False else (a if abs(a) <= abs(b) else b)
                    # smaller abs often net when both positive; for rent net < gross
                    if abs(a) <= abs(b):
                        net, gross = a, b
                    else:
                        net, gross = b, a
            else:
                gross = _parse_amount(m.group(1))
            if gross is not None:
                break

    for pat in (
        rf"(?i)rechnungsbetrag\s*\(?\s*netto\s*\)?\s*{_AMT}",
        rf"(?i)gesamt\s*netto(?:\s*EUR)?\s*{_AMT}",
        rf"(?i)gesamtsumme\s*{_AMT}",
        rf"(?i)summe\s*netto\s*(?:zu\s*[\d.,]+\s*%)?\s*{_AMT}",
        rf"(?i)(?m)^summe\s*:\s*{_AMT}",
    ):
        m = re.search(pat, text)
        if m and net is None:
            net = _parse_amount(m.group(1))
            break

    for pat in (
        rf"(?i)umsatzsteuer\s*@\s*19%\s*{_AMT}",
        rf"(?i)gesamt\s*mwst\s*{_AMT}",
        rf"(?i)[\d.,]+\s*%\s*u(?:st|msatzsteuer)\.?\s*auf\s*EUR\s*{_AMT}\s*:\s*{_AMT}",
        rf"(?i)zzgl\.?\s*19(?:[.,]0+)?\s*%\s*mwst\s*{_AMT}",
        rf"(?i)zzgl\.?\s*19\s*%\s*mwst\s*{_AMT}",
    ):
        m = re.search(pat, text)
        if m:
            vat = _parse_amount(m.group(m.lastindex))
            rate = 19.0
            break

    if rate is None and re.search(r"(?i)19(?:[.,]0+)?\s*%", text):
        rate = 19.0
    if rate is None and net and vat and abs(net) > 0.01:
        rate = round(abs(vat / net) * 100, 2)

    return gross, net, vat, rate


def _sum_charge_categories(
    text: str,
) -> tuple[float | None, float | None, float | None, float | None, float | None]:
    basic = service = marketing = turnover = storage = 0.0
    saw_b = saw_s = saw_m = saw_t = saw_st = False

    # FREY line: "Rentalincome-Retail  13.704,25" may OCR with spaces already fixed
    # Mindestmiete OCR sometimes glues qty+price "1,0045.881,1700" — recover net from last DE amount
    for line in text.splitlines():
        line_n = line.strip()
        if not line_n:
            continue
        if re.search(
            r"(?i)rechnungsbetrag|endbetrag|gesamtsumme|gesamt\s*netto|"
            r"gesamt\s*brutto|gesamt\s*mwst|^gesamt\s*:|gesamt\s*vertrag|gesamt\s*je",
            line_n,
        ):
            continue
        if re.search(r"(?i)^(mwst\s*@|ust\.?\s*auf|zzgl\.)", line_n):
            continue

        # Strip date tokens so "01.03.2026" is not read as amount 1.03
        money_line = re.sub(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", " ", line_n)
        money_line = re.sub(r"\d{1,2}[./]\d{1,2}(?=\s*[-–])", " ", money_line)
        amounts = [_parse_amount(a) for a in re.findall(_AMT, money_line)]
        amounts = [a for a in amounts if a is not None]
        # Drop tiny rate-like values that are clearly 19.00 when other amounts exist
        if len(amounts) >= 2:
            filtered = [a for a in amounts if not (18.5 <= abs(a) <= 20.0 and abs(a) == round(a, 2))]
            # only drop if we still have amounts left
            if filtered:
                # keep 19 only if it's the sole signal — else prefer non-rate
                non_rate = [a for a in amounts if abs(a) < 18.5 or abs(a) > 20.0]
                if non_rate:
                    amounts = non_rate
        if not amounts:
            continue
        value = _line_net_amount(amounts)

        # Glued Mindestmiete "1,0045.881,1700  8.717,42  45.881,17" → take last large DE amount
        if _BASIC_RE.search(line_n) and len(amounts) >= 2:
            de_like = [a for a in amounts if abs(a) >= 50]
            if de_like:
                value = de_like[-1] if abs(de_like[-1]) > abs(de_like[0]) * 0.5 else de_like[0]
                # Prefer the netto column: typically the largest among remaining after removing VAT
                nets = sorted(de_like, key=abs)
                # if we have vat≈0.19*net pair, pick net
                for cand in sorted(de_like, key=abs, reverse=True):
                    for other in de_like:
                        if other is not cand and abs(other) > 1 and abs(abs(other / cand) - 0.19) < 0.05:
                            value = cand
                            break

        if _TURNOVER_RE.search(line_n):
            turnover += value
            saw_t = True
        elif _MARKETING_RE.search(line_n):
            marketing += value
            saw_m = True
        elif _STORAGE_RE.search(line_n) and not _BASIC_RE.search(line_n):
            storage += value
            saw_st = True
        elif _SERVICE_RE.search(line_n):
            service += value
            saw_s = True
        elif _BASIC_RE.search(line_n):
            basic += value
            saw_b = True

    return (
        round(basic, 2) if saw_b else None,
        round(service, 2) if saw_s else None,
        round(marketing, 2) if saw_m else None,
        round(turnover, 2) if saw_t else None,
        round(storage, 2) if saw_st else None,
    )


def _extract_periods_PLACEHOLDER():
    pass


def _extract_periods(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(y: int, m: int) -> None:
        if y < 100:
            y += 2000
        if not (1 <= m <= 12 and 2000 <= y <= 2100):
            return
        key = f"{y:04d}-{m:02d}"
        if key not in seen:
            seen.add(key)
            found.append(key)

    for m in re.finditer(
        r"(?i)(\d{1,2})[./](\d{1,2})[./](\d{2,4})\s*[-–]\s*(\d{1,2})[./](\d{1,2})[./](\d{2,4})",
        text,
    ):
        add(int(m.group(3)), int(m.group(2)))

    for m in re.finditer(
        r"(?i)(\d{2})/(\d{2})/(\d{2})\s*[-–]\s*(\d{2})/(\d{2})/(\d{2})",
        text,
    ):
        add(2000 + int(m.group(3)), int(m.group(2)))

    for m in re.finditer(rf"(?i)(?:f[uü]r|ab)\s*({_MONTH_ALT})\s*(\d{{4}})", text):
        mo = _month_num(m.group(1))
        if mo:
            add(int(m.group(2)), mo)

    for m in re.finditer(rf"(?i)({_MONTH_ALT})\s*(\d{{4}})", text):
        mo = _month_num(m.group(1))
        if mo:
            add(int(m.group(2)), mo)

    # SPECIALCREDIT02/2026
    for m in re.finditer(r"(?i)(?:credit|gutschrift|special)[^\n]{0,20}?(\d{2})/(\d{4})", text):
        add(int(m.group(2)), int(m.group(1)))

    for m in re.finditer(
        r"(?i)(?:ab|g[uü]ltig\s*ab|dauermietrechnung\s*ab)\s*(\d{1,2})[./](\d{1,2})[./](\d{2,4})",
        text,
    ):
        add(int(m.group(3)), int(m.group(2)))

    return found
