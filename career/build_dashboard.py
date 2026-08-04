#!/usr/bin/env python3
"""
Supplier Management Dashboard — FORMULA-DRIVEN Excel template.

Run once to lay out the file with sample data.
All KPI tiles, chart pivot data, and the overdue detail table are
built with Excel formulas (SUMIF / COUNTIF / SUMPRODUCT / LARGE /
INDEX / MATCH / FILTER / SORT).

When you paste your real data into GL_Listing, VENDMAST, and
Retail_Team, every number on the Dashboard recalculates
automatically — no Python needed again.

Requirements:
  KPI tiles, bar / line charts  — all Excel versions
  Overdue detail table          — Excel 365 (FILTER + SORT)

Usage:  python career/build_dashboard.py
Output: career/supplier_dashboard.xlsx
"""
from __future__ import annotations

import calendar
import datetime
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

TODAY = datetime.date(2026, 7, 26)
random.seed(42)

# ── colour tokens ─────────────────────────────────────────────────────
C = dict(
    dark     = "1A2332",
    accent   = "C45C26",
    sea      = "2F6F6A",
    warn     = "B8860B",
    ok       = "2D6A4F",
    muted    = "5A6678",
    red      = "C0392B",
    blue     = "2471A3",
    white    = "FFFFFF",
    line     = "E2D9CB",
    light    = "F8F5F0",
    card     = "FFFDF8",
    red_bg   = "FFF5F5",
    green_bg = "F0FFF4",
)


def _fill(h):  return PatternFill("solid", fgColor=h)
def _font(size=10, bold=False, color="1A2332", italic=False):
    return Font(name="Calibri", size=size, bold=bold, color=color, italic=italic)
def _align(h="left", v="center", wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
def _border(style="thin", color="E2D9CB"):
    s = Side(style=style, color=color)
    return Border(left=s, right=s, top=s, bottom=s)


# ─────────────────────────────────────────────────────────────────────
# SAMPLE DATA  (replace rows in the three source sheets with real data)
# ─────────────────────────────────────────────────────────────────────
SUPPLIERS = [
    ("SUP001", "Acme Logistics BV",       "EUR", "Bank Transfer", 30),
    ("SUP002", "TechParts Solutions",     "EUR", "Bank Transfer", 45),
    ("SUP003", "Global Freight NL",       "EUR", "SEPA",          30),
    ("SUP004", "OfficePlus Nederland",    "EUR", "Bank Transfer", 60),
    ("SUP005", "CleanServ BV",            "EUR", "Direct Debit",  30),
    ("SUP006", "ITware Group",            "EUR", "Bank Transfer", 30),
    ("SUP007", "Alpha Consulting",        "EUR", "Bank Transfer", 45),
    ("SUP008", "Prime Maintenance Co",   "EUR", "SEPA",          30),
    ("SUP009", "Retail Display Systems", "EUR", "Bank Transfer", 60),
    ("SUP010", "HR Partners BV",         "EUR", "Bank Transfer", 30),
]

CATEGORIES = ["Logistics", "IT", "Facilities", "Consulting",
               "HR", "Marketing", "Office", "Maintenance"]
GL_CODES   = {c: str(6100 + i * 100) for i, c in enumerate(CATEGORIES)}


def _rdate(yr, mo):
    _, last = calendar.monthrange(yr, mo)
    return datetime.date(yr, mo, random.randint(1, last))


GL_ROWS: list[dict] = []
inv = 1000
for sup_code, sup_name, curr, _, terms in SUPPLIERS:
    cat = random.choice(CATEGORIES)
    for mo in range(1, 8):
        for _ in range(random.randint(1, 3)):
            inv_date = _rdate(2026, mo)
            due_date = inv_date + datetime.timedelta(days=terms + random.randint(-5, 10))
            amount   = round(random.uniform(1_500, 45_000), 2)
            po_num   = f"PO-2026-{inv:04d}"
            status   = ("Overdue" if random.random() < .55 else "Paid") if due_date < TODAY else "Open"
            GL_ROWS.append(dict(
                journal_desc  = random.choice([sup_name, po_num]),
                supplier_code = sup_code,
                supplier_name = sup_name,
                amount        = amount,
                currency      = curr,
                invoice_date  = inv_date,
                due_date      = due_date,
                category      = cat,
                gl_code       = GL_CODES.get(cat, "6999"),
                po_number     = po_num,
                status        = status,
            ))
            inv += 1

RETAIL_ROWS: list[dict] = []
for _, sup_name, _, _, _ in SUPPLIERS:
    cat = random.choice(CATEGORIES)
    for mo in range(1, 8):
        RETAIL_ROWS.append(dict(
            period        = f"2026-{mo:02d}",
            supplier_name = sup_name,
            category      = cat,
            gl_code       = GL_CODES.get(cat, "6999"),
            po_number     = f"PO-2026-{random.randint(1000,9999)}",
            budget        = round(random.uniform(20_000, 150_000), 2),
        ))

vend_ap: dict[str, float] = {}
for r in GL_ROWS:
    if r["status"] != "Paid":
        vend_ap[r["supplier_code"]] = vend_ap.get(r["supplier_code"], 0) + r["amount"]


# ─────────────────────────────────────────────────────────────────────
# WORKBOOK
# ─────────────────────────────────────────────────────────────────────
wb        = Workbook()
ws_dash   = wb.active;  ws_dash.title = "Dashboard"
ws_gl     = wb.create_sheet("GL_Listing")
ws_vend   = wb.create_sheet("VENDMAST")
ws_retail = wb.create_sheet("Retail_Team")
ws_calc   = wb.create_sheet("_Calc")


# ─────────────────────────────────────────────────────────────────────
# _CALC  — all formulas; sheet is hidden
# ─────────────────────────────────────────────────────────────────────
ws_calc.sheet_state = "hidden"

# A:B  All-supplier overdue amounts (rows 1-11)
ws_calc["A1"] = "Supplier"
ws_calc["B1"] = "Overdue (EUR)"
for i in range(2, 12):          # 10 suppliers
    ws_calc.cell(i, 1).value = f'=IFERROR(INDEX(VENDMAST_Data[Supplier Name],{i-1}),"")'
    ws_calc.cell(i, 2).value = (
        f'=IF(A{i}="","",SUMIFS(GL_Data[Amount (EUR)],'
        f'GL_Data[Supplier Name],A{i},'
        f'GL_Data[Status],"Overdue"))'
    )

# D:E  Top-5 overdue by supplier — bar chart source (rows 1-6)
ws_calc["D1"] = "Supplier"
ws_calc["E1"] = "Overdue (EUR)"
for i in range(2, 7):
    k = i - 1
    ws_calc.cell(i, 4).value = (
        f'=IFERROR(INDEX($A$2:$A$11,'
        f'MATCH(LARGE($B$2:$B$11,{k}),$B$2:$B$11,0)),"")'
    )
    ws_calc.cell(i, 5).value = f'=IFERROR(LARGE($B$2:$B$11,{k}),0)'
    ws_calc.cell(i, 5).number_format = '#,##0'

# G:H  Monthly invoiced trend — line chart source (rows 1-8)
ws_calc["G1"] = "Month"
ws_calc["H1"] = "Invoiced (EUR)"
ws_calc["G2"].value          = "=DATE(2026,1,1)"
ws_calc["G2"].number_format  = "mmm-yy"
for i in range(3, 9):
    ws_calc.cell(i, 7).value         = f"=EDATE(G{i-1},1)"
    ws_calc.cell(i, 7).number_format = "mmm-yy"
for i in range(2, 9):
    ws_calc.cell(i, 8).value = (
        f"=SUMPRODUCT("
        f"(YEAR(GL_Data[Invoice Date])=YEAR(G{i}))*"
        f"(MONTH(GL_Data[Invoice Date])=MONTH(G{i}))*"
        f"GL_Data[Amount (EUR)])"
    )
    ws_calc.cell(i, 8).number_format = '#,##0'

# A15  Sorted overdue detail — FILTER + SORT (Excel 365 required).
# Spills into A15:G15+n where n = count of overdue invoices.
# Columns: Supplier Name | Category | Invoice Date | Due Date |
#          Days Past Due | Amount (EUR) | Status
ws_calc["A15"].value = (
    "=SORT("
    "FILTER("
    "CHOOSE({1,2,3,4,5,6,7},"
    "GL_Data[Supplier Name],"
    "GL_Data[Category],"
    "GL_Data[Invoice Date],"
    "GL_Data[Due Date],"
    "GL_Data[Days Past Due],"
    "GL_Data[Amount (EUR)],"
    "GL_Data[Status]),"
    'GL_Data[Status]="Overdue"),'
    "5,-1)"
)


# ─────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────
ws_dash.sheet_properties.tabColor  = "C45C26"
ws_dash.freeze_panes               = "B5"
ws_dash.sheet_view.showGridLines   = False

for col, w in zip(range(1, 11), [2, 18, 16, 18, 16, 18, 16, 18, 16, 2]):
    ws_dash.column_dimensions[get_column_letter(col)].width = w

# ── header banner (rows 1-4) ──────────────────────────────────────────
for r in range(1, 5):
    for col in range(1, 11):
        ws_dash.cell(r, col).fill = _fill(C["dark"])

for r, h in zip(range(1, 5), [8, 40, 20, 8]):
    ws_dash.row_dimensions[r].height = h

ws_dash.merge_cells("B2:I2")
c = ws_dash["B2"]
c.value, c.font, c.alignment = (
    "Supplier Management Dashboard",
    _font(20, bold=True, color=C["white"]),
    _align("left", "center"),
)

ws_dash.merge_cells("B3:I3")
c = ws_dash["B3"]
c.value = (
    '="As of "&TEXT(TODAY(),"DD MMMM YYYY")'
    '&"   ·   Sources: GL Listing  ·  VENDMAST  ·  Retail Budget"'
)
c.font, c.alignment = _font(9, color="AAAAAA"), _align("left", "center")

# ── KPI tiles (rows 5-11) ─────────────────────────────────────────────
for r, h in zip(range(5, 12), [10, 18, 38, 18, 14, 10, 10]):
    ws_dash.row_dimensions[r].height = h

# (value_formula, number_format, subtitle_formula, accent_colour)
KPI_DEFS = [
    ('=SUMIF(GL_Data[Status],"<>Paid",GL_Data[Amount (EUR)])',
     '"EUR "#,##0',
     '=COUNTIF(GL_Data[Status],"<>Paid")&" open invoices"',
     C["blue"]),
    ('=SUMIF(GL_Data[Status],"Overdue",GL_Data[Amount (EUR)])',
     '"EUR "#,##0',
     '=COUNTIF(GL_Data[Status],"Overdue")&" invoices past due"',
     C["red"]),
    ('=COUNTIF(GL_Data[Status],"Overdue")',
     '0',
     '="out of "&COUNTA(GL_Data[Status])&" total invoices"',
     C["warn"]),
    ('=IFERROR(COUNTIF(GL_Data[Status],"Paid")/COUNTA(GL_Data[Status]),0)',
     '0.0%',
     '=COUNTIF(GL_Data[Status],"Paid")&" invoices paid on time"',
     C["ok"]),
]

KPI_COLS = [(2, 3), (4, 5), (6, 7), (8, 9)]   # col start / end (1-indexed)

for (cs, ce), (val_f, val_fmt, sub_f, color) in zip(KPI_COLS, KPI_DEFS):
    csl, cel = get_column_letter(cs), get_column_letter(ce)
    # background + borders for all cells in tile
    for row in range(5, 12):
        for col in range(cs, ce + 1):
            cell  = ws_dash.cell(row, col)
            cell.fill = _fill(C["light"])
            left   = Side(style="thick", color=color)    if col == cs else Side(style="none")
            right  = Side(style="thin",  color=C["line"]) if col == ce else Side(style="none")
            top    = Side(style="thin",  color=C["line"]) if row == 5  else Side(style="none")
            bottom = Side(style="thin",  color=C["line"]) if row == 11 else Side(style="none")
            cell.border = Border(left=left, right=right, top=top, bottom=bottom)
    # merge each row span
    for row in range(5, 12):
        ws_dash.merge_cells(f"{csl}{row}:{cel}{row}")
    # label (row 6)
    c = ws_dash.cell(6, cs)
    c.value, c.font, c.alignment = (
        "Total Outstanding" if cs == 2 else
        "Overdue Amount"    if cs == 4 else
        "Overdue Invoices"  if cs == 6 else "On-Time Payment",
        _font(8, bold=True, color="888888"),
        _align("center"),
    )
    # big value (row 7)
    c = ws_dash.cell(7, cs)
    c.value, c.number_format = val_f, val_fmt
    c.font, c.alignment = _font(20, bold=True, color=color), _align("center", "center")
    # subtitle (row 8)
    c = ws_dash.cell(8, cs)
    c.value, c.font, c.alignment = sub_f, _font(8, italic=True, color=C["muted"]), _align("center")

# ── section headers (rows 12-13) ──────────────────────────────────────
for r, h in zip(range(12, 14), [10, 22]):
    ws_dash.row_dimensions[r].height = h

ws_dash.merge_cells("B13:E13")
c = ws_dash["B13"]
c.value, c.font, c.alignment = "Top 5 Overdue Suppliers", _font(11, bold=True), _align("left", "center")

ws_dash.merge_cells("F13:I13")
c = ws_dash["F13"]
c.value, c.font, c.alignment = "Monthly Invoiced Amount Trend", _font(11, bold=True), _align("left", "center")

# ── bar chart: Top 5 overdue ──────────────────────────────────────────
bar = BarChart()
bar.type = "bar";  bar.style = 10;  bar.title = None;  bar.legend = None
bar.y_axis.numFmt = '"EUR "#,##0'
bar.width, bar.height = 14.5, 10

bar.add_data(Reference(ws_calc, min_col=5, min_row=1, max_row=6), titles_from_data=True)
bar.set_categories(Reference(ws_calc, min_col=4, min_row=2, max_row=6))
if bar.series:
    bar.series[0].graphicalProperties.solidFill      = "C45C26"
    bar.series[0].graphicalProperties.line.solidFill = "C45C26"
ws_dash.add_chart(bar, "B14")

# ── line chart: monthly trend ─────────────────────────────────────────
line = LineChart()
line.style = 10;  line.title = None;  line.legend = None
line.y_axis.numFmt = '"EUR "#,##0'
line.width, line.height = 14.5, 10

line.add_data(Reference(ws_calc, min_col=8, min_row=1, max_row=8), titles_from_data=True)
line.set_categories(Reference(ws_calc, min_col=7, min_row=2, max_row=8))
if line.series:
    s = line.series[0]
    s.graphicalProperties.line.solidFill      = "2F6F6A"
    s.graphicalProperties.line.width          = 25000
    s.marker.symbol                           = "circle"
    s.marker.size                             = 5
    s.marker.graphicalProperties.solidFill    = "2F6F6A"
    s.marker.graphicalProperties.line.solidFill = "2F6F6A"
ws_dash.add_chart(line, "F14")

# ── overdue detail table (rows 36+) ───────────────────────────────────
TSEC = 36
ws_dash.row_dimensions[TSEC].height = 10

ws_dash.merge_cells(f"B{TSEC}:I{TSEC}")
c = ws_dash.cell(TSEC, 2)
c.value = "Overdue Invoice Detail  (sorted by days overdue — requires Excel 365)"
c.font, c.alignment = _font(11, bold=True), _align("left", "center")

HDR = TSEC + 1
ws_dash.row_dimensions[HDR].height = 22
DETAIL_COLS = [
    # (header,              width, align,    number_format)
    ("Supplier",            22,   "left",    None),
    ("Category",            14,   "center",  None),
    ("Invoice Date",        13,   "center",  "DD-MMM-YY"),
    ("Due Date",            13,   "center",  "DD-MMM-YY"),
    ("Days Past Due",       13,   "center",  "0"),
    ("Amount (EUR)",        14,   "right",   "#,##0.00"),
    ("Status",              10,   "center",  None),
]
for j, (h, *_) in enumerate(DETAIL_COLS, 2):
    c = ws_dash.cell(HDR, j)
    c.value, c.font, c.fill, c.alignment = h, _font(9, bold=True, color=C["white"]), _fill(C["dark"]), _align("center")
    c.border = _border("thin", C["muted"])

# 20 data rows — each cell is a formula referencing _Calc!A15:G35
# _Calc col mapping: Supplier=A(1) Cat=B(2) InvDate=C(3) DueDate=D(4)
#                   DaysPastDue=E(5) Amount=F(6) Status=G(7)
CALC_SPILL_START = 15
for i in range(20):
    row      = HDR + 1 + i
    calc_row = CALC_SPILL_START + i
    bg       = C["red_bg"] if i % 2 == 0 else C["card"]
    ws_dash.row_dimensions[row].height = 16
    for j, (_, __, al, nf) in enumerate(DETAIL_COLS, 2):
        calc_col = get_column_letter(j - 1)   # j=2 -> col A, j=8 -> col G
        c = ws_dash.cell(row, j)
        c.value     = f'=IFERROR(_Calc!${calc_col}${calc_row},"")'
        c.fill      = _fill(bg)
        c.border    = _border("thin", C["line"])
        c.alignment = _align(al, "center")
        c.font      = _font(9, color=C["dark"])
        if nf:
            c.number_format = nf

# ── KPI summary row (row 58) ──────────────────────────────────────────
SUM_ROW = 59
ws_dash.row_dimensions[SUM_ROW].height = 22
ws_dash.merge_cells(f"B{SUM_ROW}:D{SUM_ROW}")
ws_dash.cell(SUM_ROW, 2).value = '=COUNTIF(GL_Data[Status],"Overdue")&" overdue  |  "&COUNTIF(GL_Data[Status],"Open")&" open  |  "&COUNTIF(GL_Data[Status],"Paid")&" paid"'
ws_dash.cell(SUM_ROW, 2).font      = _font(9, italic=True, color=C["muted"])
ws_dash.cell(SUM_ROW, 2).alignment = _align("left", "center")

ws_dash.merge_cells(f"E{SUM_ROW}:I{SUM_ROW}")
ws_dash.cell(SUM_ROW, 5).value = (
    '="Total budget: EUR "&TEXT(SUM(Retail_Data[Budget (EUR)]),"#,##0")'
    '&"   |   AP open: EUR "&TEXT(SUM(VENDMAST_Data[AP Balance (EUR)]),"#,##0")'
)
ws_dash.cell(SUM_ROW, 5).font      = _font(9, italic=True, color=C["muted"])
ws_dash.cell(SUM_ROW, 5).alignment = _align("right", "center")


# ─────────────────────────────────────────────────────────────────────
# GL_LISTING  — source data + formula column "Days Past Due"
# ─────────────────────────────────────────────────────────────────────
ws_gl.sheet_properties.tabColor  = "2F6F6A"
ws_gl.sheet_view.showGridLines   = False
ws_gl.freeze_panes = "A2"

GL_HDR = [
    ("Journal Description", 30, "left"),
    ("Supplier Code",        12, "center"),
    ("Supplier Name",        24, "left"),
    ("Amount (EUR)",         14, "right"),
    ("Currency",             10, "center"),
    ("Invoice Date",         14, "center"),
    ("Due Date",             14, "center"),
    ("Category",             14, "center"),
    ("GL Code",              10, "center"),
    ("PO Number",            16, "center"),
    ("Status",               10, "center"),
    ("Days Past Due",        13, "center"),  # formula column — auto-calculated
]
for j, (h, w, al) in enumerate(GL_HDR, 1):
    ws_gl.column_dimensions[get_column_letter(j)].width = w
    c = ws_gl.cell(1, j)
    c.value, c.font, c.fill, c.alignment = h, _font(10, bold=True, color=C["white"]), _fill(C["sea"]), _align("center")
ws_gl.row_dimensions[1].height = 22

STATUS_FG = {"Overdue": C["red"],    "Open": C["dark"],  "Paid": C["ok"]}
STATUS_BG = {"Overdue": C["red_bg"], "Open": C["card"],  "Paid": C["green_bg"]}

for i, row in enumerate(GL_ROWS, 2):
    sc = row["status"]
    bg = STATUS_BG.get(sc, C["card"])
    vals = [
        row["journal_desc"], row["supplier_code"], row["supplier_name"],
        row["amount"],       row["currency"],      row["invoice_date"],
        row["due_date"],     row["category"],      row["gl_code"],
        row["po_number"],    sc,
        # col 12 = formula: days past due (positive for open/overdue past due date, 0 otherwise)
        '=IF([@Status]<>"Paid",MAX(0,TODAY()-[@[Due Date]]),0)',
    ]
    ws_gl.row_dimensions[i].height = 15
    for j, (val, (_, _, al)) in enumerate(zip(vals, GL_HDR), 1):
        c = ws_gl.cell(i, j)
        c.value = val
        c.fill  = _fill(bg)
        c.font  = _font(9, bold=(j == 11), color=STATUS_FG.get(sc if j == 11 else "Open", C["dark"]))
        c.alignment = _align(al, "center")
        if j == 4:        c.number_format = '#,##0.00'
        if j in (6, 7):   c.number_format = 'DD-MMM-YY'

tbl = Table(displayName="GL_Data",
            ref=f"A1:{get_column_letter(len(GL_HDR))}{1+len(GL_ROWS)}")
tbl.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws_gl.add_table(tbl)


# ─────────────────────────────────────────────────────────────────────
# VENDMAST  — source data; AP Balance is hardcoded from sample data
#             (in real use you paste your AP balance values here)
# ─────────────────────────────────────────────────────────────────────
ws_vend.sheet_properties.tabColor  = "B8860B"
ws_vend.sheet_view.showGridLines   = False
ws_vend.freeze_panes = "A2"

VEND_HDR = [
    ("Supplier Code",         14, "center"),
    ("Supplier Name",         26, "left"),
    ("AP Balance (EUR)",      18, "right"),
    ("Currency",              10, "center"),
    ("Payment Method",        16, "center"),
    ("Payment Terms (days)",  22, "center"),
]
for j, (h, w, al) in enumerate(VEND_HDR, 1):
    ws_vend.column_dimensions[get_column_letter(j)].width = w
    c = ws_vend.cell(1, j)
    c.value, c.font, c.fill, c.alignment = h, _font(10, bold=True, color=C["white"]), _fill(C["warn"]), _align("center")
ws_vend.row_dimensions[1].height = 22

for i, (sup_code, sup_name, curr, pay_method, terms) in enumerate(SUPPLIERS, 2):
    ap = round(vend_ap.get(sup_code, 0), 2)
    vals = [sup_code, sup_name, ap, curr, pay_method, terms]
    ws_vend.row_dimensions[i].height = 16
    for j, (val, (_, _, al)) in enumerate(zip(vals, VEND_HDR), 1):
        c = ws_vend.cell(i, j)
        c.value, c.alignment = val, _align(al, "center")
        c.font = _font(9, bold=(j == 3 and ap > 50_000), color=C["red"] if (j == 3 and ap > 50_000) else C["dark"])
        if j == 3: c.number_format = '#,##0.00'

tbl2 = Table(displayName="VENDMAST_Data",
             ref=f"A1:{get_column_letter(len(VEND_HDR))}{1+len(SUPPLIERS)}")
tbl2.tableStyleInfo = TableStyleInfo(name="TableStyleMedium3", showRowStripes=True)
ws_vend.add_table(tbl2)


# ─────────────────────────────────────────────────────────────────────
# RETAIL_TEAM  — source data
# ─────────────────────────────────────────────────────────────────────
ws_retail.sheet_properties.tabColor  = "2471A3"
ws_retail.sheet_view.showGridLines   = False
ws_retail.freeze_panes = "A2"

RET_HDR = [
    ("Period",         12, "center"),
    ("Supplier Name",  26, "left"),
    ("Category",       16, "center"),
    ("GL Code",        10, "center"),
    ("PO Number",      16, "center"),
    ("Budget (EUR)",   16, "right"),
]
for j, (h, w, al) in enumerate(RET_HDR, 1):
    ws_retail.column_dimensions[get_column_letter(j)].width = w
    c = ws_retail.cell(1, j)
    c.value, c.font, c.fill, c.alignment = h, _font(10, bold=True, color=C["white"]), _fill(C["blue"]), _align("center")
ws_retail.row_dimensions[1].height = 22

for i, row in enumerate(RETAIL_ROWS, 2):
    vals = [row["period"], row["supplier_name"], row["category"],
            row["gl_code"], row["po_number"], row["budget"]]
    ws_retail.row_dimensions[i].height = 15
    for j, (val, (_, _, al)) in enumerate(zip(vals, RET_HDR), 1):
        c = ws_retail.cell(i, j)
        c.value, c.alignment = val, _align(al, "center")
        c.font = _font(9, color=C["dark"])
        if j % 2 == 0: c.fill = _fill("F5F5F5")
        if j == 6: c.number_format = '#,##0.00'

tbl3 = Table(displayName="Retail_Data",
             ref=f"A1:{get_column_letter(len(RET_HDR))}{1+len(RETAIL_ROWS)}")
tbl3.tableStyleInfo = TableStyleInfo(name="TableStyleMedium4", showRowStripes=True)
ws_retail.add_table(tbl3)


# ─────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────
out = Path(__file__).parent / "supplier_dashboard.xlsx"
wb.save(out)
print(f"Saved: {out}")
print(f"  GL rows: {len(GL_ROWS)}")
print(f"  Suppliers: {len(SUPPLIERS)}")
print(f"  Budget rows: {len(RETAIL_ROWS)}")
print()
print("Dashboard KPI formulas (recalculate automatically when you update source data):")
print("  Total Outstanding  =SUMIF(GL_Data[Status],\"<>Paid\",GL_Data[Amount (EUR)])")
print("  Overdue Amount     =SUMIF(GL_Data[Status],\"Overdue\",GL_Data[Amount (EUR)])")
print("  Overdue Count      =COUNTIF(GL_Data[Status],\"Overdue\")")
print("  On-Time Payment    =IFERROR(COUNTIF(...Paid)/COUNTA(...Status),0)")
print()
print("Overdue detail table requires Excel 365 (FILTER + SORT dynamic arrays).")
print("For older Excel: use AutoFilter on GL_Listing -> Status = Overdue, sort Days Past Due.")
