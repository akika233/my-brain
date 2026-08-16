# Supplier Management Dashboard — Plan

Plan for a visual dashboard over Aurora AP data to fix late payments, wrong amounts,
failed direct debits, and unmatched invoices — reported in P&L terms.

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
credit transfer). To report on DD failures at all, the vendor master needs to expose the
mandate flag and the payment run needs to return a rejection reason. Flagging as a data
gap to close before that view can be built.

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

**View 4 — Payment method health (answers "is direct debit working?")**
DD mandates active vs used, failed collections with reason codes, DD-flagged vendors
that were actually paid by manual transfer. Blocked until the mandate and rejection data
is available — build the frame now, populate when the fields exist.

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

## 6. Still needed

- The **GL listing** and **vendor master** extracts (referenced but not yet supplied)
- A full AP log, not the 9-row sample — needed to size the problem and set thresholds
- Confirmation of which Aurora report generates `AP_LG_NF`, so the export can be fixed
  at source rather than patched downstream
- Whether direct debit mandates live in Aurora or only at the bank

**See also:** [[README]]

**Section:** [[career]]
