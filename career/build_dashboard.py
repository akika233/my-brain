#!/usr/bin/env python3
"""
Supplier Management Dashboard — built from a real Aurora AP log export.

Reads the AP_LG_NF open-items extract, normalises it (Aurora exports the same
column in several incompatible shapes — see `_parse_date` and `GL_CORRUPT_HINT`),
and writes a formula-driven Excel workbook.

Sheets:
  Dashboard     KPI tiles, aging profile, top overdue suppliers, exception queue
  AP_Log        the extract plus calculated columns (Excel table `AP_Data`)
  Suppliers     per-supplier exposure and concentration
  Data_Quality  the export faults that have to be fixed at source
  _Calc         hidden chart/spill helpers

Every KPI is an Excel formula over `AP_Data`, so refreshing the extract in place
recalculates the whole workbook. Re-run this script when the supplier population
changes, since the Suppliers sheet is materialised at build time.

Usage:  python career/build_dashboard.py --input "path/to/AP_LG_NF.CSV"
Output: career/supplier_dashboard.xlsx
"""
from __future__ import annotations

import argparse
import csv
import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# Excel's day zero. Aurora sometimes emits dates already converted to serials.
EXCEL_EPOCH = datetime.date(1899, 12, 30)

# A 12-digit account rounded to three significant figures still parses as a
# number, so the scientific-notation text is the only reliable tell.
GL_CORRUPT_HINT = "E+"

PO_PREFIX = "POR"

# ── colour tokens ─────────────────────────────────────────────────────
C = dict(
    dark="1A2332",
    accent="C45C26",
    sea="2F6F6A",
    warn="B8860B",
    ok="2D6A4F",
    muted="5A6678",
    red="C0392B",
    blue="2471A3",
    white="FFFFFF",
    line="E2D9CB",
    light="F8F5F0",
    card="FFFDF8",
    red_bg="FFF5F5",
)


def _fill(h):
    return PatternFill("solid", fgColor=h)


def _font(size=10, bold=False, color="1A2332", italic=False):
    return Font(name="Calibri", size=size, bold=bold, color=color, italic=italic)


def _align(h="left", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)


def _border(style="thin", color="E2D9CB"):
    s = Side(style=style, color=color)
    return Border(left=s, right=s, top=s, bottom=s)


# ─────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────
@dataclass
class APLine:
    supplier_code: str
    supplier_name: str
    entry_type: str
    lref: str
    supplier_ref: str
    po_ref: str
    doc_date: datetime.date | None
    due_date: datetime.date | None
    period: str
    currency: str
    doc_amount: float
    open_amount: float
    gl_account: str
    pay_method: str
    pay_category: str
    ledger_code: str
    quality_notes: list[str] = field(default_factory=list)


def _parse_date(raw: str, notes: list[str], label: str) -> datetime.date | None:
    """Aurora emits dd/mm/yy, a bare Excel serial, or 00/00/00 for 'none'."""
    raw = (raw or "").strip()
    if not raw or raw == "00/00/00":
        return None
    if raw.isdigit():
        notes.append(f"{label} exported as Excel serial number")
        return EXCEL_EPOCH + datetime.timedelta(days=int(raw))
    try:
        return datetime.datetime.strptime(raw, "%d/%m/%y").date()
    except ValueError:
        notes.append(f"{label} unparseable ({raw!r})")
        return None


def _parse_amount(raw: str) -> float:
    raw = (raw or "").strip().replace(",", "")
    return float(raw) if raw else 0.0


def _parse_period(raw: str) -> str:
    """Aurora period 2606 means 2026 period 06."""
    raw = (raw or "").strip()
    if re.fullmatch(r"\d{4}", raw):
        return f"20{raw[:2]}-{raw[2:]}"
    return raw


def load_ap_log(path: Path) -> list[APLine]:
    lines: list[APLine] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("SUPN15") or "").strip():
                continue
            notes: list[str] = []
            gl = (row.get("GLAC17") or "").strip()
            if GL_CORRUPT_HINT in gl.upper():
                notes.append("GL account truncated to scientific notation on export")
            doc_amount = _parse_amount(row.get("BTMT17"))
            open_amount = _parse_amount(row.get("PTMT17"))
            if doc_amount != open_amount:
                notes.append("Document amount differs from open amount")
            lines.append(
                APLine(
                    supplier_code=(row.get("SUPN15") or "").strip(),
                    supplier_name=(row.get("SNAM05") or "").strip(),
                    entry_type=(row.get("ETYP15") or "").strip(),
                    lref=(row.get("LREF15") or "").strip(),
                    supplier_ref=(row.get("SREF15") or "").strip(),
                    po_ref=(row.get("SOPN15") or "").strip(),
                    doc_date=_parse_date(row.get("DATE"), notes, "Document date"),
                    due_date=_parse_date(row.get("PDUE"), notes, "Due date"),
                    period=_parse_period(row.get("PERIOD")),
                    currency=(row.get("CURN15") or "").strip(),
                    doc_amount=doc_amount,
                    open_amount=open_amount,
                    gl_account=gl,
                    pay_method=(row.get("PMTH05") or "").strip(),
                    pay_category=(row.get("PCAT05") or "").strip(),
                    ledger_code=(row.get("LCOD15") or "").strip(),
                    quality_notes=notes,
                )
            )
    return lines


# ─────────────────────────────────────────────────────────────────────
# SHEET: AP_LOG
# ─────────────────────────────────────────────────────────────────────
# (header, width, alignment, number_format, formula or None for source data)
AP_COLS: list[tuple[str, int, str, str | None, str | None]] = [
    ("Supplier Code", 14, "center", None, None),
    ("Supplier Name", 22, "left", None, None),
    ("Type", 8, "center", None, None),
    ("LREF", 12, "center", None, None),
    ("Supplier Ref", 22, "left", None, None),
    ("PO Ref", 14, "center", None, None),
    ("Doc Date", 12, "center", "DD-MMM-YY", None),
    ("Due Date", 12, "center", "DD-MMM-YY", None),
    ("Period", 10, "center", None, None),
    ("Currency", 9, "center", None, None),
    ("Doc Amount", 13, "right", "#,##0.00", None),
    ("Open Amount", 13, "right", "#,##0.00", None),
    ("GL Account", 16, "center", None, None),
    ("Pay Method", 12, "center", None, None),
    ("Pay Cat", 9, "center", None, None),
    ("Ledger", 9, "center", None, None),
    (
        "Terms Days",
        11,
        "center",
        "0",
        '=IF(OR([@[Due Date]]="",[@[Doc Date]]=""),"",[@[Due Date]]-[@[Doc Date]])',
    ),
    (
        "Days Past Due",
        13,
        "center",
        "0",
        '=IF([@[Due Date]]="","",MAX(0,TODAY()-[@[Due Date]]))',
    ),
    (
        "Status",
        12,
        "center",
        None,
        '=IF([@Type]="CR","Credit",'
        'IF([@[Due Date]]="","No Due Date",'
        'IF([@[Days Past Due]]>0,"Overdue","Open")))',
    ),
    (
        "Aging Bucket",
        13,
        "center",
        None,
        '=IF([@[Days Past Due]]="","n/a",'
        'IF([@[Days Past Due]]=0,"Current",'
        'IF([@[Days Past Due]]<=30,"1-30",'
        'IF([@[Days Past Due]]<=60,"31-60",'
        'IF([@[Days Past Due]]<=90,"61-90","90+")))))',
    ),
    (
        "Exception Reason",
        30,
        "left",
        None,
        # Priority order: the reason that blocks payment outranks the reason
        # that merely makes the line look odd.
        '=IFS('
        '[@Type]="CR","Unapplied credit",'
        'ISNUMBER(SEARCH("E+",[@[GL Account]]&"")),"GL account corrupted on export",'
        '[@[PO Ref]]="","No PO reference",'
        '[@[Terms Days]]<0,"Due date before invoice date",'
        'AND([@[Terms Days]]<>"",[@[Terms Days]]<=1),"Payment terms 1 day or less",'
        '[@[Doc Amount]]<>[@[Open Amount]],"Partial payment / amount mismatch",'
        'LEFT([@[PO Ref]],3)<>"POR","Non-standard PO format",'
        '[@[Days Past Due]]>90,"Over 90 days past due",'
        'TRUE,"")',
    ),
]

AP_FIRST_FORMULA_COL = next(i for i, c in enumerate(AP_COLS) if c[4] is not None)


def build_ap_log(ws, lines: list[APLine]) -> None:
    ws.sheet_properties.tabColor = C["sea"]
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    for j, (header, width, _, _, _) in enumerate(AP_COLS, 1):
        ws.column_dimensions[get_column_letter(j)].width = width
        c = ws.cell(1, j)
        c.value, c.font, c.fill, c.alignment = (
            header,
            _font(9, bold=True, color=C["white"]),
            _fill(C["sea"]),
            _align("center", wrap=True),
        )
    ws.row_dimensions[1].height = 28

    for i, ln in enumerate(lines, 2):
        source = [
            ln.supplier_code, ln.supplier_name, ln.entry_type, ln.lref,
            ln.supplier_ref, ln.po_ref, ln.doc_date, ln.due_date, ln.period,
            ln.currency, ln.doc_amount, ln.open_amount, ln.gl_account,
            ln.pay_method, ln.pay_category, ln.ledger_code,
        ]
        ws.row_dimensions[i].height = 15
        for j, (_, _, al, fmt, formula) in enumerate(AP_COLS, 1):
            c = ws.cell(i, j)
            c.value = formula if formula else source[j - 1]
            c.alignment = _align(al, "center")
            c.font = _font(9, color=C["dark"])
            if fmt:
                c.number_format = fmt
            if formula:
                c.fill = _fill(C["light"])

    tbl = Table(
        displayName="AP_Data",
        ref=f"A1:{get_column_letter(len(AP_COLS))}{1 + len(lines)}",
    )
    tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(tbl)


# ─────────────────────────────────────────────────────────────────────
# SHEET: SUPPLIERS
# ─────────────────────────────────────────────────────────────────────
SUP_COLS = [
    ("Supplier Code", 14, "center", None),
    ("Supplier Name", 24, "left", None),
    ("Open Items", 11, "center", "0"),
    ("Open Amount", 15, "right", "#,##0.00"),
    ("Overdue Amount", 15, "right", "#,##0.00"),
    ("Over 90 Days", 15, "right", "#,##0.00"),
    ("Max Days Past Due", 17, "center", "0"),
    ("Exceptions", 12, "center", "0"),
    ("% of Open AP", 13, "center", "0.0%"),
]


def build_suppliers(ws, lines: list[APLine]) -> list[str]:
    ws.sheet_properties.tabColor = C["warn"]
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    seen: dict[str, str] = {}
    for ln in lines:
        seen.setdefault(ln.supplier_code, ln.supplier_name)
    codes = sorted(seen)

    for j, (header, width, _, _) in enumerate(SUP_COLS, 1):
        ws.column_dimensions[get_column_letter(j)].width = width
        c = ws.cell(1, j)
        c.value, c.font, c.fill, c.alignment = (
            header,
            _font(9, bold=True, color=C["white"]),
            _fill(C["warn"]),
            _align("center", wrap=True),
        )
    ws.row_dimensions[1].height = 28

    for i, code in enumerate(codes, 2):
        ws.row_dimensions[i].height = 16
        values = [
            code,
            seen[code],
            f'=COUNTIF(AP_Data[Supplier Code],$A{i})',
            f'=SUMIF(AP_Data[Supplier Code],$A{i},AP_Data[Open Amount])',
            f'=SUMIFS(AP_Data[Open Amount],AP_Data[Supplier Code],$A{i},'
            f'AP_Data[Status],"Overdue")',
            f'=SUMIFS(AP_Data[Open Amount],AP_Data[Supplier Code],$A{i},'
            f'AP_Data[Aging Bucket],"90+")',
            f'=IFERROR(MAXIFS(AP_Data[Days Past Due],AP_Data[Supplier Code],$A{i}),0)',
            f'=COUNTIFS(AP_Data[Supplier Code],$A{i},AP_Data[Exception Reason],"?*")',
            f'=IFERROR($D{i}/SUM(AP_Data[Open Amount]),0)',
        ]
        for j, (value, (_, _, al, fmt)) in enumerate(zip(values, SUP_COLS), 1):
            c = ws.cell(i, j)
            c.value, c.alignment, c.font = value, _align(al, "center"), _font(9)
            if fmt:
                c.number_format = fmt

    tbl = Table(
        displayName="Supplier_Data",
        ref=f"A1:{get_column_letter(len(SUP_COLS))}{1 + len(codes)}",
    )
    tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium3", showRowStripes=True)
    ws.add_table(tbl)
    return codes


# ─────────────────────────────────────────────────────────────────────
# SHEET: DATA QUALITY
# ─────────────────────────────────────────────────────────────────────
# (issue, count formula, why it matters, fix at source?)
DQ_ISSUES = [
    (
        "GL account corrupted on export",
        '=SUMPRODUCT(--ISNUMBER(SEARCH("E+",AP_Data[GL Account]&"")))',
        "Account rounded to 3 significant figures — line cannot be mapped to P&L",
        "Yes — export GLAC17 as text",
    ),
    (
        "Missing PO reference",
        '=COUNTIFS(AP_Data[PO Ref],"",AP_Data[Type],"IN")',
        "Nothing to three-way match against; invoice stalls indefinitely",
        "No — purchasing process",
    ),
    (
        "Non-standard PO format",
        '=SUMPRODUCT((AP_Data[PO Ref]<>"")*(LEFT(AP_Data[PO Ref],3)<>"POR"))',
        "Breaks automated PO matching",
        "No — purchasing process",
    ),
    (
        "Due date before invoice date",
        '=COUNTIF(AP_Data[Terms Days],"<0")',
        "Aging is meaningless; invoice is born overdue",
        "No — vendor master terms",
    ),
    (
        "Payment terms 1 day or less",
        '=SUMPRODUCT((AP_Data[Terms Days]<>"")*(AP_Data[Terms Days]<=1)'
        '*(AP_Data[Terms Days]>=0))',
        "Vendor master terms missing, so every invoice lands overdue",
        "No — vendor master terms",
    ),
    (
        "Unapplied credit note",
        '=COUNTIF(AP_Data[Type],"CR")',
        "Gross invoice gets paid and the credit never nets off",
        "No — AP process",
    ),
    (
        "Partial payment / amount mismatch",
        '=SUMPRODUCT(--(AP_Data[Doc Amount]<>AP_Data[Open Amount]))',
        "Document and open amounts disagree — check for short payment",
        "No — AP process",
    ),
    (
        "Missing due date",
        '=COUNTIF(AP_Data[Due Date],"")',
        "Excluded from aging entirely, so it is invisible to chasing",
        "Yes — PDUE should never be 00/00/00",
    ),
]

DQ_COLS = [
    ("Export / data issue", 34, "left", None),
    ("Lines", 8, "center", "0"),
    ("% of lines", 11, "center", "0.0%"),
    ("Why it matters", 54, "left", None),
    ("Fix at source?", 24, "left", None),
    ("Owner", 16, "left", None),
    ("Target date", 13, "center", "DD-MMM-YY"),
]


def build_data_quality(ws, serial_date_lines: int) -> None:
    ws.sheet_properties.tabColor = C["red"]
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    for j, (header, width, _, _) in enumerate(DQ_COLS, 1):
        ws.column_dimensions[get_column_letter(j)].width = width
        c = ws.cell(1, j)
        c.value, c.font, c.fill, c.alignment = (
            header,
            _font(9, bold=True, color=C["white"]),
            _fill(C["red"]),
            _align("center", wrap=True),
        )
    ws.row_dimensions[1].height = 28

    rows = list(DQ_ISSUES)
    # Detected while parsing: once a serial reaches Excel it is a valid date,
    # so this one cannot be recomputed by a worksheet formula.
    rows.append((
        "Date exported as Excel serial",
        serial_date_lines,
        "Mixed date formats in one column silently mis-bucket the aging",
        "Yes — export DATE/PDUE as text",
    ))

    for i, (issue, count, why, fix) in enumerate(rows, 2):
        ws.row_dimensions[i].height = 30
        values = [issue, count, f'=IFERROR($B{i}/COUNTA(AP_Data[Supplier Code]),0)',
                  why, fix, "", ""]
        for j, (value, (_, _, al, fmt)) in enumerate(zip(values, DQ_COLS), 1):
            c = ws.cell(i, j)
            c.value = value
            c.alignment = _align(al, "top", wrap=True)
            c.font = _font(9, bold=(j == 1))
            c.border = _border("thin", C["line"])
            if fmt:
                c.number_format = fmt

    note = ws.cell(len(rows) + 3, 1)
    note.value = (
        "Owner and target date are for you to fill in. Everything marked "
        '"Fix at source" has to be corrected in the Aurora export itself — '
        "no amount of downstream cleaning recovers a GL account that was "
        "already rounded to three significant figures."
    )
    note.font = _font(9, italic=True, color=C["muted"])
    ws.merge_cells(start_row=len(rows) + 3, start_column=1, end_row=len(rows) + 3, end_column=5)


# ─────────────────────────────────────────────────────────────────────
# SHEET: _CALC  (chart sources + exception spill)
# ─────────────────────────────────────────────────────────────────────
AGING_BUCKETS = ["Current", "1-30", "31-60", "61-90", "90+"]
EXCEPTION_REASONS = [
    "Unapplied credit",
    "GL account corrupted on export",
    "No PO reference",
    "Due date before invoice date",
    "Payment terms 1 day or less",
    "Partial payment / amount mismatch",
    "Non-standard PO format",
    "Over 90 days past due",
]
EXC_SPILL_ROW = 30
EXC_DETAIL_ROWS = 20


def build_calc(ws, supplier_count: int) -> None:
    ws.sheet_state = "hidden"

    # A:B — aging profile (bar chart source)
    ws["A1"], ws["B1"] = "Bucket", "Open Amount"
    for i, bucket in enumerate(AGING_BUCKETS, 2):
        ws.cell(i, 1).value = bucket
        ws.cell(i, 2).value = f'=SUMIF(AP_Data[Aging Bucket],$A{i},AP_Data[Open Amount])'
        ws.cell(i, 2).number_format = "#,##0"

    # D:E — top 5 overdue suppliers (bar chart source)
    last = supplier_count + 1
    ws["D1"], ws["E1"] = "Supplier", "Overdue Amount"
    for k in range(1, 6):
        i = k + 1
        ws.cell(i, 4).value = (
            f'=IFERROR(INDEX(Suppliers!$B$2:$B${last},'
            f'MATCH(LARGE(Suppliers!$E$2:$E${last},{k}),'
            f'Suppliers!$E$2:$E${last},0)),"")'
        )
        ws.cell(i, 5).value = f'=IFERROR(LARGE(Suppliers!$E$2:$E${last},{k}),0)'
        ws.cell(i, 5).number_format = "#,##0"

    # G:H — exception mix (bar chart source)
    ws["G1"], ws["H1"] = "Reason", "Lines"
    for i, reason in enumerate(EXCEPTION_REASONS, 2):
        ws.cell(i, 7).value = reason
        ws.cell(i, 8).value = f'=COUNTIF(AP_Data[Exception Reason],$G{i})'

    # Exception queue, highest open amount first. Spills down and right.
    # Columns: Supplier | LREF | Supplier Ref | Due Date | Days Past Due |
    #          Open Amount | Exception Reason
    ws.cell(EXC_SPILL_ROW, 1).value = (
        "=IFERROR(SORT(FILTER(CHOOSE({1,2,3,4,5,6,7},"
        "AP_Data[Supplier Name],"
        "AP_Data[LREF],"
        "AP_Data[Supplier Ref],"
        "AP_Data[Due Date],"
        "AP_Data[Days Past Due],"
        "AP_Data[Open Amount],"
        "AP_Data[Exception Reason]),"
        'AP_Data[Exception Reason]<>""),'
        '6,-1),"")'
    )


# ─────────────────────────────────────────────────────────────────────
# SHEET: DASHBOARD
# ─────────────────────────────────────────────────────────────────────
# (label, value formula, number format, subtitle formula, colour)
KPI_ROW_1 = [
    ("Open AP (net)",
     "=SUM(AP_Data[Open Amount])",
     '"EUR "#,##0',
     '=COUNTA(AP_Data[Supplier Code])&" open items"',
     "blue"),
    ("Overdue Value",
     '=SUMIF(AP_Data[Status],"Overdue",AP_Data[Open Amount])',
     '"EUR "#,##0',
     '=COUNTIF(AP_Data[Status],"Overdue")&" invoices past due"',
     "red"),
    ("Overdue % of AP",
     '=IFERROR(SUMIF(AP_Data[Status],"Overdue",AP_Data[Open Amount])'
     "/SUM(AP_Data[Open Amount]),0)",
     "0.0%",
     '="of EUR "&TEXT(SUM(AP_Data[Open Amount]),"#,##0")&" open"',
     "warn"),
    ("Over 90 Days",
     '=SUMIF(AP_Data[Aging Bucket],"90+",AP_Data[Open Amount])',
     '"EUR "#,##0',
     '=COUNTIF(AP_Data[Aging Bucket],"90+")&" items stuck, not just late"',
     "red"),
]

KPI_ROW_2 = [
    ("Lines with Exceptions",
     '=COUNTIF(AP_Data[Exception Reason],"?*")',
     "0",
     '=TEXT(IFERROR(COUNTIF(AP_Data[Exception Reason],"?*")'
     '/COUNTA(AP_Data[Supplier Code]),0),"0%")&" of all open lines"',
     "accent"),
    ("Lines Without PO",
     '=COUNTIFS(AP_Data[PO Ref],"",AP_Data[Type],"IN")',
     "0",
     '="EUR "&TEXT(SUMIFS(AP_Data[Open Amount],AP_Data[PO Ref],"",'
     'AP_Data[Type],"IN"),"#,##0")&" cannot be matched"',
     "accent"),
    ("Unapplied Credits",
     '=SUMIF(AP_Data[Type],"CR",AP_Data[Open Amount])',
     '"EUR "#,##0',
     '=COUNTIF(AP_Data[Type],"CR")&" credit notes not netted off"',
     "sea"),
    ("Top Supplier Share",
     "=IFERROR(MAX(Supplier_Data[% of Open AP]),0)",
     "0.0%",
     '="concentration across "&COUNTA(Supplier_Data[Supplier Code])&" suppliers"',
     "sea"),
]

DETAIL_COLS = [
    ("Supplier", "left", None),
    ("LREF", "center", None),
    ("Supplier Ref", "left", None),
    ("Due Date", "center", "DD-MMM-YY"),
    ("Days Past Due", "center", "0"),
    ("Open Amount", "right", "#,##0.00"),
    ("Exception Reason", "left", None),
]


def _kpi_block(ws, top_row: int, defs) -> None:
    """Four tiles across columns B:I, occupying seven rows from `top_row`."""
    rows = range(top_row, top_row + 7)
    for r, h in zip(rows, [10, 18, 34, 26, 10, 6, 6]):
        ws.row_dimensions[r].height = h

    for (cs, ce), (label, val_f, val_fmt, sub_f, colour_key) in zip(
        [(2, 3), (4, 5), (6, 7), (8, 9)], defs
    ):
        colour = C[colour_key]
        csl, cel = get_column_letter(cs), get_column_letter(ce)
        for r in rows:
            for col in range(cs, ce + 1):
                cell = ws.cell(r, col)
                cell.fill = _fill(C["light"])
                cell.border = Border(
                    left=Side(style="thick", color=colour) if col == cs else Side(style="none"),
                    right=Side(style="thin", color=C["line"]) if col == ce else Side(style="none"),
                    top=Side(style="thin", color=C["line"]) if r == top_row else Side(style="none"),
                    bottom=Side(style="thin", color=C["line"]) if r == rows[-1] else Side(style="none"),
                )
            ws.merge_cells(f"{csl}{r}:{cel}{r}")

        c = ws.cell(top_row + 1, cs)
        c.value, c.font, c.alignment = label, _font(8, bold=True, color="888888"), _align("center")

        c = ws.cell(top_row + 2, cs)
        c.value, c.number_format = val_f, val_fmt
        c.font, c.alignment = _font(18, bold=True, color=colour), _align("center", "center")

        c = ws.cell(top_row + 3, cs)
        c.value = sub_f
        c.font, c.alignment = _font(8, italic=True, color=C["muted"]), _align("center", "top", wrap=True)


def _section_header(ws, row: int, spans: list[tuple[str, str, str]]) -> None:
    ws.row_dimensions[row].height = 22
    for start, end, title in spans:
        ws.merge_cells(f"{start}{row}:{end}{row}")
        c = ws[f"{start}{row}"]
        c.value, c.font, c.alignment = title, _font(11, bold=True), _align("left", "center")


def _bar(ws_calc, cat_col: int, val_col: int, max_row: int, colour: str,
         horizontal: bool, num_fmt: str) -> BarChart:
    chart = BarChart()
    chart.type = "bar" if horizontal else "col"
    chart.style = 10
    chart.title = None
    chart.legend = None
    chart.y_axis.numFmt = num_fmt
    chart.width, chart.height = 14.5, 9
    chart.add_data(Reference(ws_calc, min_col=val_col, min_row=1, max_row=max_row),
                   titles_from_data=True)
    chart.set_categories(Reference(ws_calc, min_col=cat_col, min_row=2, max_row=max_row))
    if chart.series:
        chart.series[0].graphicalProperties.solidFill = colour
        chart.series[0].graphicalProperties.line.solidFill = colour
    return chart


def build_dashboard(ws, ws_calc, source_name: str) -> None:
    ws.sheet_properties.tabColor = C["accent"]
    ws.sheet_view.showGridLines = False

    for col, w in zip(range(1, 11), [2, 20, 16, 20, 16, 20, 16, 20, 16, 2]):
        ws.column_dimensions[get_column_letter(col)].width = w

    # header banner
    for r in range(1, 5):
        for col in range(1, 11):
            ws.cell(r, col).fill = _fill(C["dark"])
    for r, h in zip(range(1, 5), [8, 38, 18, 8]):
        ws.row_dimensions[r].height = h

    ws.merge_cells("B2:I2")
    c = ws["B2"]
    c.value, c.font, c.alignment = (
        "Supplier Management Dashboard",
        _font(20, bold=True, color=C["white"]),
        _align("left", "center"),
    )

    ws.merge_cells("B3:I3")
    c = ws["B3"]
    c.value = (
        '="As of "&TEXT(TODAY(),"DD MMMM YYYY")'
        f'&"   ·   Source: Aurora AP open items ({source_name})"'
    )
    c.font, c.alignment = _font(9, color="AAAAAA"), _align("left", "center")

    _kpi_block(ws, 5, KPI_ROW_1)
    _kpi_block(ws, 13, KPI_ROW_2)

    _section_header(ws, 21, [("B", "E", "Aging Profile"),
                             ("F", "I", "Top 5 Overdue Suppliers")])
    ws.add_chart(_bar(ws_calc, 1, 2, 1 + len(AGING_BUCKETS), C["accent"],
                      horizontal=False, num_fmt='"EUR "#,##0'), "B22")
    ws.add_chart(_bar(ws_calc, 4, 5, 6, C["red"],
                      horizontal=True, num_fmt='"EUR "#,##0'), "F22")

    _section_header(ws, 41, [("B", "E", "Exception Mix"), ("F", "I", "")])
    ws.add_chart(_bar(ws_calc, 7, 8, 1 + len(EXCEPTION_REASONS), C["sea"],
                      horizontal=True, num_fmt="0"), "B42")

    ws.merge_cells("F42:I50")
    c = ws["F42"]
    c.value = (
        "How to read this\n\n"
        "• Aging answers whether we pay late. The 90+ bucket is different in kind — "
        "those items are blocked, not slow, and paying faster will not clear them.\n\n"
        "• Exception Mix answers why an item is blocked. Work it top down: the "
        "biggest bar is the process to fix, not the invoice.\n\n"
        "• Anything flagged \"corrupted on export\" is an Aurora extract problem. "
        "It cannot be fixed in this workbook."
    )
    c.font, c.alignment = _font(9, color=C["muted"]), _align("left", "top", wrap=True)

    # exception queue
    _section_header(ws, 62, [("B", "I", "Exception Queue  (largest open amount first)")])
    hdr = 63
    ws.row_dimensions[hdr].height = 22
    # Column widths stay on the dashboard grid so the KPI tiles keep equal
    # spans; the reason text overflows into the empty column J instead.
    for j, (header, _, _) in enumerate(DETAIL_COLS, 2):
        c = ws.cell(hdr, j)
        c.value, c.font, c.fill, c.alignment = (
            header, _font(9, bold=True, color=C["white"]), _fill(C["dark"]), _align("center")
        )
        c.border = _border("thin", C["muted"])

    for i in range(EXC_DETAIL_ROWS):
        row = hdr + 1 + i
        calc_row = EXC_SPILL_ROW + i
        ws.row_dimensions[row].height = 16
        for j, (_, al, fmt) in enumerate(DETAIL_COLS, 2):
            calc_col = get_column_letter(j - 1)
            c = ws.cell(row, j)
            c.value = f'=IFERROR(IF(_Calc!${calc_col}${calc_row}=0,"",_Calc!${calc_col}${calc_row}),"")'
            c.fill = _fill(C["red_bg"] if i % 2 == 0 else C["card"])
            c.border = _border("thin", C["line"])
            c.alignment = _align(al, "center")
            c.font = _font(9, color=C["dark"])
            if fmt:
                c.number_format = fmt

    footer = hdr + EXC_DETAIL_ROWS + 2
    ws.merge_cells(f"B{footer}:I{footer}")
    c = ws.cell(footer, 2)
    c.value = (
        '=COUNTIF(AP_Data[Status],"Overdue")&" overdue  |  "'
        '&COUNTIF(AP_Data[Status],"Open")&" open  |  "'
        '&COUNTIF(AP_Data[Exception Reason],"?*")&" exceptions  |  "'
        '&"Exception queue needs Excel 365 (FILTER/SORT); "'
        '&"otherwise filter AP_Log on Exception Reason."'
    )
    c.font, c.alignment = _font(9, italic=True, color=C["muted"]), _align("left", "center")


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main() -> int:
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=here / "ap_log.csv",
                    help="Aurora AP_LG_NF CSV export (default: career/ap_log.csv)")
    ap.add_argument("--output", type=Path, default=here / "supplier_dashboard.xlsx",
                    help="output workbook (default: career/supplier_dashboard.xlsx)")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"AP log not found: {args.input}")
        print("Pass the export explicitly, e.g.:")
        print('  python career/build_dashboard.py --input "C:\\path\\to\\AP_LG_NF.CSV"')
        return 1

    lines = load_ap_log(args.input)
    if not lines:
        print(f"No AP lines found in {args.input} — check the column headers.")
        return 1

    wb = Workbook()
    ws_dash = wb.active
    ws_dash.title = "Dashboard"
    ws_ap = wb.create_sheet("AP_Log")
    ws_sup = wb.create_sheet("Suppliers")
    ws_dq = wb.create_sheet("Data_Quality")
    ws_calc = wb.create_sheet("_Calc")

    build_ap_log(ws_ap, lines)
    codes = build_suppliers(ws_sup, lines)
    serial_dates = sum(1 for ln in lines
                       if any("serial" in n for n in ln.quality_notes))
    build_data_quality(ws_dq, serial_dates)
    build_calc(ws_calc, len(codes))
    build_dashboard(ws_dash, ws_calc, args.input.name)

    wb.save(args.output)

    flagged = sum(1 for ln in lines if ln.quality_notes)
    print(f"Saved: {args.output}")
    print(f"  AP lines:  {len(lines)}")
    print(f"  Suppliers: {len(codes)}")
    print(f"  Lines with a parsing/export fault: {flagged}")
    for ln in lines:
        for note in ln.quality_notes:
            print(f"    {ln.supplier_code} LREF {ln.lref}: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
