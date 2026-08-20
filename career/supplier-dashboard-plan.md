# Supplier Management Dashboard — Plan

Plan for a visual dashboard over Aurora AP data to fix late payments, wrong amounts,
failed direct debits, and unmatched invoices — reported in P&L terms.

How to use the built file: [[supplier-dashboard-guide]].

Builds on the existing template in `build_dashboard.py` → `supplier_dashboard.xlsx`
(see [[README]]), which currently runs on synthetic data.

## 1. The six problems, restated as things you can measure

A dashboard is only useful if each complaint becomes a number with an owner. Mapping:

| Complaint | Metric on the dashboard | Driver field in Aurora |
|---|---|---|
| Payment late | Days past due, % of AP value overdue | `PDUE` vs today |
| Wrong amount | Invoice vs PO vs GL variance, unapplied credits | `BTMT17` vs `PTMT17` vs invoice PDF |
| Direct debit not working | Failed/blocked DD runs, DD vendors paid manually | `PMTH05`, `PCAT05` |
| Invoice doesn't match | 3-way match exception rate (PO / receipt / invoice) | `SOPN15` (PO ref), missing PO |
| Invoice not received on time | Days from invoice date to entry into ledger | `DATE` vs posting period `PERIOD` |
| Hard to match payment/invoice to supplier | % of lines with a clean supplier + PO + doc reference | `SUPN15`, `SREF15`, `LREF15` |

## 2. What the AP log already tells us

From `AP_LG_NF.CSV` — 9 open items, EUR 29,013 gross, valued at 16 Aug 2026.
Small sample, but every one of the six problems is already visible in it.

**Aging is the headline.** Six of nine items (EUR 19,455, 67% of open AP) are past due:

- `OMN001` — two invoices of EUR 3,500 each, due 17 Mar 2026, **152 days overdue**
- `PLA001` — EUR 170, due 7 Apr 2026, **131 days overdue**
- `EST001` — three invoices totalling EUR 12,285, 17–24 days overdue

The split matters. The `EST001` items are a *cash timing* problem — recent, on clean
30-day terms, just not paid. The `OMN001` and `PLA001` items are a *blockage* problem —
five months old, nobody is chasing them, and they will not clear by paying faster.
These two groups need different dashboard treatment and different owners.

**Concentration risk:** `EST001` alone is EUR 22,024, or 76% of gross open AP.
One supplier relationship dominates the exposure.

**Data quality faults that directly cause the "can't match" complaint:**

- **GL accounts are destroyed by Excel.** Six of the nine rows (67%) carry `GLAC17` as
  `6.24E+11`, `6.13E+11` or `6.28E+11` — 12-digit account codes rounded to 3 significant
  figures on CSV export. Those lines **cannot be mapped to a P&L account at all**. Fixing
  the export (text-format the column, or export from Aurora as fixed-width) is a
  prerequisite, not a nice-to-have.
- **Dates arrive in two incompatible formats.** Most rows are `dd/mm/yy`; `OPT001` and
  `PLA001` come through as Excel serials (46331, 46301, 46118, 46119). Any aging
  calculation silently mis-buckets these.
- **`OPT001` has a due date before its invoice date** (6 Oct 2026 due, 5 Nov 2026
  invoice). Either the terms are keyed wrong or the dates are swapped.
- **`PLA001` has 1-day payment terms** (invoice 6 Apr, due 7 Apr) — almost certainly a
  missing terms setup on the vendor master, which guarantees the invoice is born overdue.
- **PO references are inconsistent.** `POR19843` style on most rows, bare `20244729` on
  `PLA001`, and **blank on `OMN001`**. A missing PO is exactly why that one sat for five
  months: there is nothing to 3-way match it against.
- **An unapplied credit note is sitting loose.** `MCA001`, EUR -859.12, `PDUE` of
  `00/00/00`. Unapplied credits are a classic source of "wrong amount" — you pay the
  gross invoice and the credit never nets off.

**Direct debit is not visible in this extract.** Every row is `PMTH05 = SEP` (SEPA
credit transfer). The mandate flag, scheme and expected invoice frequency are not in
Aurora at all — they live in the AP mandate repository — so `VENDMAST` in the workbook
carries dedicated columns for them.

**The GL listing and vendor master first arrived empty, and the reason matters.** They
were tabs in a workbook saved as `.CSV`. CSV is a single-sheet format, so every tab
except the active one was silently dropped, and that same save rounded the GL accounts
to scientific notation. Supplied as `.xlsx` they came through intact — which also
confirms the corruption: GL accounts are genuinely 12 digits (`615220001040`), so the
AP log's `6.13E+11` is a truncated `613…` rent account. The account *family* survives,
the account does not.

## 2b. What the GL and vendor list show

75 GL lines and 51 suppliers for France Retail (company `NF`). These are samples, so
counts below are indicative rather than a full population — but the failure modes are
unambiguous.

**Suppliers are trading without a vendor master record.** Nine of the thirteen suppliers
posting to the GL have no row in the vendor list: `ABE001`, `BKS001`, `CAS001`, `CEN001`,
`ESP002`, `MCA001`, `MGE001`, `NIK001`, `PRO005`. `MCA001` is the striking one — it
appears in the AP log *and* posts rent of €27k, €1.3k and €43k plus a €119k credit note,
yet has no master record. No master record means no agreed payment method, no terms and
no mandate. This is the root of "payment or invoice hard to match to the supplier".

**The vendor name field is unusable for identification.** Every `SNAM05` value is exactly
four characters: `Adye`, `SCI `, `ESTU`. `SCI002` and `SCI003` are both `SCI `, and
`SCI001` reads ` ESP`, which does not match its own code. You cannot identify a supplier
from this field, which is precisely why matching is manual.

**AP and the vendor master do not reconcile.** Of the five AP-log suppliers, two agree
exactly (`OPT001` €677.98, `PLA001` €170.00), two differ (`EST001` €22,024 vs €2,855;
`OMN001` €7,000 vs €8,400) and one is absent. Note the €2,855 figure is exactly the sum
of `EST001`'s two oldest invoices, so the two extracts are as-of different dates — worth
confirming before treating the whole difference as an error.

**Direct debit is where the real exposure sits.** Six suppliers are set to `PMTH05 = DD`,
holding €175,394 of open balance — money collectable without a payment run approving it.
`SCI001` alone is €129,506. **Five of the six have no invoice anywhere in the GL.** That
is exactly the gap the process document describes: no systematic monitoring of suppliers
set up for DD who have not submitted invoices. The one exception, `SCI002`, last invoiced
16 June 2026 — 61 days ago.

**PO coverage is better than the AP log suggested**: 41 of 50 AP-sourced GL lines (82%)
carry a `POR` reference. All nine without one are rent or property charges (`Loyer`,
`Le Marais Base rent Q3 2026`, `Lyon TOR Q2 266`). Under the DD process those sit on the
Contracted Cost Sheet and legitimately have no PO, so the target excludes them rather
than counting them as failures.

**The GL carries a ready-made P&L dimension.** `Flash Category` groups spend into
Rent - Office and Building (€143,913), Parts, Maintenance & Repair (€27,765) and Cleaning
(€3,528). Accruals post as `Journal type = Reversing` and reverse the following period,
so the P&L view separates posted invoices from the accrual cycle.

One caution: the GL sheet's own control total reads €271,936.57 against 75 rows summing
to €175,205. The extract is partial, so do not reconcile to that header figure.

## 3. Data model — the joins that make it work

Four sources, and the join keys already exist:

```
Aurora AP log (open items)      ── SUPN15 ──┐
Aurora GL listing (posted)      ── GLAC17 ──┤
Vendor master (VENDMAST)        ── SUPN15 ──┼── Supplier dimension
DocStore invoice PDFs           ── LREF15 ──┘
```

The important one: **`LREF15` in the AP log is the same LREF the existing
`invoice_extractor` uses to pull PDFs from DocStore.** That gives a direct, automatic
path from an open AP line to the supplier's actual invoice document — supplier name,
amount, VAT, PO number, all extracted. Comparing the extracted values against the AP
line is what turns "invoice doesn't match" from a manual hunt into a computed exception
flag. This is the single highest-value link in the whole design and the reason to build
on the tooling that already exists rather than starting fresh.

Derived fields to compute once, in the load step, not in the dashboard:

- `days_past_due` = today − `PDUE` (guarded for `00/00/00` and serial-date rows)
- `aging_bucket` = Current / 1–30 / 31–60 / 61–90 / 90+
- `has_po` = `SOPN15` populated and matching the `POR#####` pattern
- `gl_valid` = `GLAC17` is a full-length code, not scientific notation
- `match_status` = Matched / PO missing / Amount variance / No document
- `partial_paid` = `BTMT17` ≠ `PTMT17`

## 4. Dashboard layout — five views

**View 1 — Cash & aging (answers "are we paying late?")**
KPI tiles: total open AP, overdue value, overdue %, count 90+ days. Stacked bar of
aging buckets by supplier. A forward 13-week payment forecast off `PDUE` so Treasury
sees the cash requirement before the due date, not after.

**View 2 — Exceptions (answers "why is this invoice stuck?")**
The working queue, and the view the AP clerk lives in. One row per blocked item, sorted
by value × days stuck, each tagged with a reason: no PO, amount variance, GL invalid,
duplicate suspect, unapplied credit, no document in DocStore. Every row needs a named
owner and an age — an exception with no owner is why `OMN001` reached 152 days.

**View 3 — Match quality (answers "can we trust the data?")**
Trend of 3-way match rate, % of lines with a valid PO, % with a usable GL code, invoice
receipt lag (`DATE` → posting `PERIOD`). This is the view that shows whether the
underlying process is improving or you are just clearing symptoms faster.

**View 4 — Direct debit control (answers "is direct debit working?")**
This view is not invented here: the *EMEA DTC Direct Debit Process* document already
specifies it, calling for a Direct Debit Supplier Dashboard built on GL listings and
VendMast to identify DD suppliers, record signed mandates, establish expected invoice
frequency from historical activity, monitor receipt against that schedule, and flag
missing invoices for proactive follow-up. The workbook implements it as `DD_Monitor`,
with thresholds taken straight from the document: reminder at **7 calendar days** past
the expected invoice date, escalation to the PO owner **15 days** after that, mandate
completeness requiring signature, treasury approval and SharePoint filing, and the
**Core vs B2B** split — roughly 99% of mandates sit on Core, which is not registered
with HSBC, so anyone holding the bank details can collect.

**View 5 — P&L view (answers "what does this cost us?")**
Spend by GL account and category against budget, accrual vs actual by period, and the
real P&L cost of the failures: late-payment interest and penalty charges, lost early-
settlement discounts, FX loss on delayed foreign-currency payments, and unapplied
credits as unrecognised income. This is the view that justifies the project to a CFO —
it converts an operational annoyance into a euro figure.

## 5. Build sequence

**Phase 1 — Fix the extract.** Get a clean Aurora export: `GLAC17` as text, one date
format, `PDUE` never `00/00/00`. Two-thirds of the GL codes in the current CSV are
unusable, so the P&L view cannot be trusted until this is fixed. Half a day, and it
unblocks everything.

**Phase 2 — Load and normalise.** A Python loader producing one tidy fact table plus a
supplier dimension, with the derived fields from section 3. Reuses the parsing patterns
already in `invoice_extractor`.

**Phase 3 — Views 1, 2, 5.** Aging, exceptions, P&L — these run entirely on the AP log
and GL listing, which are data you already have. This is where the visible win lands.

**Phase 4 — Wire in DocStore.** Join `LREF15` to the extractor, populate View 3, and
turn amount variance into an automatic flag.

**Phase 5 — View 4** once the direct-debit mandate and rejection fields are available.

## 6. KPI set

Twenty-four KPIs are defined on the `KPI_Definitions` tab of the workbook — the "Layout &
KPI definition" and "Define metrics & data sources" milestones from the project charter.
Each carries a definition, the literal Excel formula, its data source, an owner and a
target. Sixteen appear as tiles on the dashboard, grouped into four bands:

| Band | KPIs on the tile row |
|---|---|
| Payment timeliness | Open AP, Overdue Value, Overdue % of AP, Weighted Avg Days Past Due |
| Blocked items and invoice matching | Over 90 Days, Match Exception Rate, PO Coverage Rate, GL Codes Unusable |
| Direct debit control | DD Exposure, DD Without Active Mandate, DD Suppliers With No Invoices, Core Scheme Share |
| Invoice receipt and supplier reconciliation | Receipt SLA Breaches, Suppliers Not in Vendor Master, AP vs Vendor Master Variance, Top Supplier Concentration |

Over-90-day balances sit with matching rather than timeliness on purpose: those items are
blocked, and a faster payment run does not clear them.

Targets are set where the process document gives one (7-day reminder, 15-day escalation,
B2B migration, 100% mandate documentation) and left as "tracked, not targeted" where it
does not, rather than inventing a number.

One measure worth calling out: **accrual exposure** is estimated from each supplier's
average historical GL amount, not summed from AP. A missing invoice is by definition not
in AP yet, so summing the open balance would always report zero.

## 7. Still needed

The single highest-value input is the **expected invoice frequency per DD supplier**.
Without it the receipt control cannot compute an expected date, and every DD row reads
"Frequency not set". It can be seeded from GL history for suppliers that have billed
before, and from the contract for those that have not.

- **Expected invoice frequency** for the six DD suppliers (VENDMAST column M)
- **The DD mandate register** — scheme, status, signed date, treasury approval,
  SharePoint filing. Not in Aurora; comes from the AP repository (VENDMAST columns H–L)
- **Payment terms per supplier**, which the vendor list extract does not carry at all
- Full extracts rather than samples, so the reconciliation counts can be trusted
- **Set the GL account column to text before exporting**, and never save the source
  as `.CSV`
- Confirmation of which Aurora report generates `AP_LG_NF`, so the export can be fixed
  at source rather than patched downstream

## 8. Immediate actions the data already justifies

1. Investigate `SCI001` — €129,506 of direct debit exposure with no invoice anywhere in
   the GL. Highest single risk on the dashboard.
2. Create vendor master records for the nine suppliers currently trading without one,
   starting with `MCA001`, which is posting six-figure rent and credit notes.
3. Ask why `EST001` shows €22,024 in the AP log against €2,855 in the vendor master, and
   confirm the two extracts are as of the same date.
4. Fix the `AP_LG_NF` export to emit text GL accounts and a single date format.
5. Chase `OMN001` — two invoices, €7,000, 152 days overdue, one with no PO reference.

**See also:** [[README]]

**Section:** [[career]]
