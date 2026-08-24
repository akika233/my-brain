# Supplier dashboard — AP process plan

How AP uses `supplier_dashboard.xlsx` as an operating file, not a report.

Two tracks share one Monday extract. They must not be mixed: **aging is
invoices already in AP**; **receipt / chase / accrue is invoices that should
have arrived and have not**. Paying faster does not fix a missing invoice, and
chasing a supplier does not clear a 152-day item that has no PO.

**See also:** [[supplier-dashboard-guide]] · [[supplier-dashboard-plan]]

## Roles

| Role | Owns | Dashboard home |
|---|---|---|
| AP clerk | Aging, exceptions, chasing missing invoices, mandate completeness | `AP_Log`, exception queue, `DD_Monitor` |
| AP lead | Weekly pack, 7-day reminders, 15-day escalations | `Dashboard` bands 1–3, `DD_Monitor` Action Required |
| Retail / PO owner | Confirm missing invoices, approve POs, respond to escalations | Escalation rows only |
| Retail Finance | Month-end accrual, Flash Category spend | `DD_Monitor` Accrual Estimate, `P&L_View` |
| Treasury | Mandate scheme, Core vs B2B, DD exposure | `VENDMAST` H–L, K13/K14/K23 |

## Cadence

| When | Track | What happens |
|---|---|---|
| Monday AM | Both | Paste / rebuild extracts. Recalculate. Do not start chasing on Friday's file. |
| Monday | A — supplier / aging | Payment run candidates vs blocked items. |
| Monday | B — DD monitor | Receipt statuses, reminders, escalations, silent DD suppliers. |
| Wednesday COP (wk 3 of close) | B then A | Chase follow-up. Mark spend / mandate progress. |
| Last working day | Accrual | Book K12 from `DD_Monitor`. Check `P&L_View`. Reconcile AP vs vendor master. |
| First week of quarter | Mandate | Core vs B2B, filing completeness (K14, K15). |

Until `VENDMAST` column M (Expected Invoice Frequency) is filled for every DD
supplier, Track B is blind. Do that before the first Monday.

---

## Track A — supplier management (AP aging)

**Question:** of the invoices we *have*, which do we pay, which are blocked, which
supplier is concentrating risk?

### Step 1 — Aging profile (5 minutes)

`Dashboard` → Aging Profile chart + Payment timeliness tiles.

Read in this order:

1. **Open AP (K01)** — size of the book.
2. **Overdue % (K03)** — target below 10%. If it is 67% as on the sample, the
   problem is not one late invoice.
3. **Aging buckets** — Current / 1–30 / 31–60 / 61–90 / 90+.
4. **Over 90 days (K04)** — treat as blocked, not slow. A faster payment run
   will not clear these.

Then open `Suppliers` and sort by Overdue Amount. That is the per-supplier aging
summary AP expects: open items, overdue, 90+, max days past due, exception count.

### Step 2 — Split the book into two piles

On `AP_Log`, filter `Aging Bucket` and `Status`.

| Pile | Filter | Action this week |
|---|---|---|
| Pay | Status = Overdue, Aging = 1–30 or 31–60, Exception Reason blank | Payment run. Cash timing only. |
| Unblock | Aging = 90+, or Exception Reason populated | Do **not** pay. Work the reason. |
| Credit | Type = CR | Net off before paying the matching invoice. |
| Invisible | Due Date blank | Fix vendor terms — these never age, so they never get chased. |

Exception reasons, in the order the file already ranks them:

1. Unapplied credit
2. Supplier not in vendor master
3. GL account corrupted on export
4. No PO reference
5. Due date before invoice date
6. Payment terms 1 day or less
7. Partial payment / amount mismatch
8. Non-standard PO format
9. Over 90 days past due

### Step 3 — Chase *open AP* (stuck invoices, not missing ones)

`Dashboard` exception queue (largest amount first) or `AP_Log` filtered.

For each row, the chase is internal first:

- No PO / non-standard PO → Retail / PO owner, not the supplier.
- Not in vendor master → vendor master maintenance (`Reconciliation`).
- Amount mismatch / unapplied credit → AP matching.
- 90+ with a clean PO → then chase the supplier for a statement / copy invoice.

Log the chase **outside** the formula columns: add a note in an AP working
copy, or keep a side list of supplier + LREF + last contact date. The
workbook does not yet have an owner / last-chased column — do not type over
Status or Exception Reason.

### Step 4 — Concentration and master data

`Suppliers` % of Open AP (K19, watch above 25%) and `Reconciliation`:

- Not in vendor master → cannot pay cleanly, cannot set terms, cannot mandate.
- AP vs vendor master variance → do not sign off the aging until it is explained.

---

## Track B — direct debit monitor (invoice receipt)

**Question:** of the invoices we *should have*, which arrived, which to chase,
which to accrue, which DD is unsafe to collect?

This is the control the EMEA DTC Direct Debit Process asked for. It runs on
`VENDMAST` + `GL_Listing`, not on the AP log — a missing invoice is not in AP.

### Step 1 — Mandate gate (before any collection)

`VENDMAST` filtered to `DD Supplier` = Y, or Dashboard K13 / K14 / K23.

Do not allow a collection when:

- Mandate Status is not Active
- Mandate Filed is not Y
- Signed or treasury date is blank
- Scheme is Core and the risk has not been accepted (unregistered with HSBC)

K16 (manual payments to DD suppliers) is a failed collection or a duplicate-pay
risk — investigate every one the same day.

K24 / `DD_Monitor` Receipt Status = **No invoice activity** is the highest-risk
row: the supplier can pull funds and has never billed. Verify billing before
the next collection.

### Step 2 — Invoice received, by supplier

`DD_Monitor` is the per-supplier receipt register:

| Column | Meaning |
|---|---|
| Last Invoice in GL | Most recent AP-sourced GL date for that supplier |
| Days Since Last Invoice | Clock since that date |
| Days Past Expected | Clock minus the frequency interval (7 / 14 / 30 / 91 / 365) |
| Receipt Status | On track / Due / Reminder due / Escalate / No invoice activity / Frequency not set |
| Action Required | The sentence AP should execute |

Filter in this order:

1. **Frequency not set** → set VENDMAST column M. Do not chase yet.
2. **No invoice activity** → verify the supplier is actually billing.
3. **Escalate** (>22 days past expected: 7 + 15) → PO owner + supplier.
4. **Reminder due** (>7 days past expected) → reminder to supplier.
5. **Due** → watchlist, not yet a chase.
6. **On track** → skip.

Dashboard chart "Direct Debit Receipt Status" is the same split in one picture.

### Step 3 — Chase *missing* invoices

The chase on Track B is the opposite of Track A: there is no AP line yet.

| Status | Who | SLA |
|---|---|---|
| Reminder due | AP → supplier | Within 7 days of expected invoice date |
| Escalate | AP + PO owner → supplier | 15 days after the reminder (22 days total) |
| No invoice activity | AP, then Retail | Before next DD collection |

Use Last Invoice in GL + Expected Frequency to tell the supplier the period you
are missing. After the invoice is posted, the next Monday extract should move
the row back to On track and drop the Accrual Estimate.

### Step 4 — Accrue what has not arrived

At month end, `DD_Monitor` Accrual Estimate (K12) is the booking source.

- Estimated from that supplier's **average historical GL invoice**, because a
  missing invoice cannot be summed from AP.
- Only rows on Reminder due or Escalate get a non-zero estimate (On track is
  assumed to arrive in time; Frequency not set cannot be estimated).
- Retail Finance books the total. `P&L_View` already splits posted invoices
  from the accrual/reversal cycle so period cost is not double-counted.

If the estimate looks wrong (new supplier, one-off spike), override in the
accrual journal — do not overwrite the formula. Note the override in VENDMAST
Notes.

**Rent and other contracted costs still need an accrual.** They are out of K12
only because the *method* is wrong for them, not because they should be ignored.

K12 estimates "we usually get an invoice of about €X and it has not shown up".
That fits variable DD bills (utilities, cleaning). Rent is a known contract:
quarterly `Loyer`, TOR, credits. Averaging MCA001's GL (`€27k`, `€1.3k`, `€43k`,
plus a `€119k` credit) would book nonsense. Those amounts live on the Contracted
Cost Sheet, which is also why they have no PO and are excluded from PO coverage
(K06) — a matching rule, not an accrual rule.

If the landlord is `PMTH05 = DD` they **do** appear on `DD_Monitor` (SCI names
in France often are property companies). Chase them on Track B like any other DD
supplier. Book the accrual from the lease / contracted-cost sheet, not from
K12's average. If they are not DD, they never enter `DD_Monitor`; accrue from
the contracted-cost sheet on the existing schedule.

Do not use "not in K12" as a reason to skip the rent accrual.

---

## How the two tracks meet

```
Monday extract
    ├─ AP_Log ──────── Track A: age, pay, unblock, match
    ├─ GL_Listing ─┬─ Track B: last invoice date, receipt SLA
    └─ VENDMAST ───┴─ Track B: mandate + expected frequency
                              └─ month end: Accrual Estimate → journal
```

Same supplier can appear on both: EST001 overdue in AP **and** a later period
not yet received. Work Track A on the open item and Track B on the missing
period. Do not use one chase email for both — the supplier will send the wrong
document.

Close pack (one page):

1. Aging: overdue % and 90+ (Dashboard).
2. Exceptions still open (queue).
3. DD receipt: reminder / escalate / no activity counts.
4. Accrual: K12 total, by supplier from `DD_Monitor`.
5. Recon: suppliers not in master + AP vs master variance.

---

## What the file already does vs what AP still needs

Already in the workbook: aging buckets, per-supplier overdue/90+, exception
queue, DD receipt SLA, accrual estimate, P&L split.

Not in the workbook yet — keep on paper / a working copy until built:

- **Owner + last chased date** on each exception and each DD row (without this,
  OMN001-style items age in silence).
- **Expected next invoice date** as a date, not only "days past expected".
- **Accrual worksheet** (supplier, estimate, booked Y/N, journal ref) — K12 is
  a total, not a posting list with sign-off.
- **Statement / copy-invoice request log** for Track A 90+ items.
- Aging printed as Current / 1–30 / 31–60 / 61–90 / 90+ **by supplier** (the
  chart is company-total; `Suppliers` has overdue and 90+ but not the five
  buckets).

Those five are the next build if AP is going to live in this file every
Monday rather than export to a side spreadsheet.

**Section:** [[career]]
