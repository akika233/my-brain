# Skills map

Living evidence of what you can do — built from shipped work in this vault, not aspirational labels.

**Positioning (working draft):** Finance-ops practitioner who designs and builds the control layer around AP — aging, direct debit, match quality, and P&L visibility — instead of only clearing invoices by hand.

## Skill clusters

### 1. AP control design (process → measurable system)
- Turn operational complaints into owned metrics (late pay, wrong amount, failed DD, unmatched invoice, late receipt, hard-to-match supplier).
- Separate *cash timing* problems from *blockage* problems so owners and actions differ.
- Map EMEA DTC Direct Debit process rules into dashboard controls (7-day reminder, 15-day escalate, mandate completeness, Core vs B2B).
- Design five operating views: cash & aging, exceptions queue, match quality, DD monitor, P&L cost of failure.

**Evidence:** `career/supplier-dashboard-plan.md`, `career/supplier-dashboard-process.md`, `KPI_Definitions` design (24 KPIs, 16 tiles, four bands).

### 2. Finance data engineering (messy ERP → usable fact tables)
- Normalize Aurora / AS/400 conventions: `CYYMMDD` dates, `CYYPP` periods, space-padded codes, mixed `dd/mm/yy` + Excel serials + `00/00/00` sentinels.
- Join AP log ↔ GL listing ↔ vendor master ↔ DocStore (`LREF`) into one supplier dimension.
- Detect and escalate extract faults at source (GL accounts destroyed by CSV scientific notation, multi-tab lost when saved as CSV, truncated vendor names).
- Prefer formula-driven Excel refresh over re-running Python when population is stable; re-materialize supplier/reconciliation sheets when population changes.

**Evidence:** `career/aurora_extracts.py`, `career/build_dashboard.py`, data-quality write-ups in the plan.

### 3. Spreadsheet product craft (cross-tool, audit-safe)
- Build multi-sheet workbooks that survive both Excel and WPS (no dynamic arrays; avoid table self-refs WPS strips).
- KPI tiles + exception queues with `LARGE` / `INDEX` / `MATCH` patterns instead of `FILTER` / `SORT`.
- Calculated columns, spare blank rows in tables, hidden `_Calc` helpers — operator-friendly refresh without code.

**Evidence:** `career/build_dashboard.py` → `supplier_dashboard.xlsx` sheet design (`Dashboard`, `AP_Log`, `DD_Monitor`, `Reconciliation`, `P&L_View`, `Data_Quality`, …).

### 4. Match & reconciliation logic
- PO / PA ↔ GL journal matching with trimmed/upper keys, month aliases, allocation weights when one PO spans many tracker rows.
- Flag journals whose PO is missing from the tracker; force-match via typed PA when needed.
- FX and invoice-currency lookups fixed where prior tracker pointed at wrong columns / typos (`DDK`).

**Evidence:** `career/improve_budget_tracker.py` (DTC Retail 2026 Budget Tracker rewrite).

### 5. Document & report automation
- Pull invoice PDFs from DocStore (Selenium + basic auth) or local folders; extract fields to Excel; drive downloads from GL `DocRef` + Country columns.
- Idempotent Adyen report downloader (HTTP Basic, predictable URLs, skip existing, explicit backfill) — no webhook host required.

**Evidence:** `career/invoice_extractor/`, `career/README.md` Adyen section.

### 6. Diagnostic storytelling (numbers that force action)
- Read a small open-AP sample and name concrete chase / master-data / export fixes (e.g. long-overdue no-PO items, DD exposure with no invoice in GL, suppliers posting without vendor master).
- Write operator guides and process docs so the system can be run without the builder.

**Evidence:** plan §8 immediate actions; `career/supplier-dashboard-guide.md`.

## Proof artifacts (portfolio bullets)

Use these almost verbatim in a review or CV:

1. Designed and built a formula-driven **supplier control dashboard** over Aurora AP/GL/vendor extracts: aging, exception queue, DD monitor, P&L view, and 24 defined KPIs.
2. Diagnosed systemic extract failures (CSV scientific notation on 12-digit GL accounts, mixed date formats) and designed the fix-at-source sequence before trusting P&L views.
3. Rewrote **PO-to-GL matching** on the DTC Retail budget tracker so PA/PO lines allocate correctly across split rows and FX/currency lookups stop pointing at broken ranges.
4. Built an **invoice PDF extractor** wired to DocStore LREF, reusable from Excel DocRef columns.
5. Automated **Adyen daily report** pulls with safe re-runs and month backfill.

## Strengths this pattern shows
- You ship end-to-end: problem framing → data model → build → operator process.
- You think in controls and owners, not just charts.
- You make tools other people can refresh without you.

## Gaps to name honestly (not failures — next bets)
- **Career narrative still thin:** goals and skills lived in tooling docs, not in `career-goals.md` / this file until now.
- **Stakeholder packaging:** strong on build; less written yet on how you socialized the dashboard to Treasury / PO owners / leadership.
- **Scale proof:** sample extracts in the plan; need one clean full-population refresh story with before/after KPI movement.
- **Depth choice:** decide whether the next 90 days double down on **AP controls / finance systems**, **automation / light data engineering**, or a hybrid “finance ops + tooling” lane.

## One next practice
Pick one live win this month and write a 5-line “before → after → metric” note into this file (or a review doc). Example shape: *DD suppliers with no invoice in GL: N → chased → first receipt / accrual booked.*

**Section:** [[career]]
