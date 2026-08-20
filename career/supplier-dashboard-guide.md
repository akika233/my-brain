# Supplier dashboard — user guide

How to use `career/supplier_dashboard.xlsx` as AP / Retail Finance. The file
turns three Aurora extracts (AP log, GL listing, vendor list) into KPIs for
late payment, wrong amount, failed direct debit, unmatched invoices, late
invoice receipt, and suppliers that cannot be matched.

Open it in **Excel or WPS Office**. Do not save a copy that Excel/WPS already
"repaired" — that version has had formulas stripped. If a repair dialog
appears, close without saving and rebuild (see [[README]]).

**See also:** [[supplier-dashboard-plan]]

## What you type vs what calculates

| Sheet | You type | Leave it alone |
|---|---|---|
| `Dashboard` | Nothing | KPI tiles, charts, exception queue |
| `KPI_Definitions` | Owners / targets if they change | Formulas, definitions |
| `AP_Log` | Paste a new AP extract into the source columns | Calculated columns (Status, Aging, Exception Reason) |
| `GL_Listing` | Paste a new GL extract | `In Vendor Master` |
| `VENDMAST` | Mandate columns H–O (see first-time setup) | A–G (from Aurora). `DD Supplier` is formula |
| `DD_Monitor` | Nothing | Entirely from VENDMAST + GL |
| `Reconciliation` | Nothing | Recalc after paste; rebuild if new suppliers appear |
| `Suppliers` | Nothing | Same — rebuild if the supplier list grows |
| `P&L_View` | Nothing | Spend by Flash Category |
| `Data_Quality` | Owner and target date | Counts |
| `_Calc` | Hidden — ignore | Chart helpers |

Grey/light cells are formulas. Yellow/input cells on VENDMAST are the only
standing manual input.

## First-time setup (once)

DD receipt control is dormant until frequency is filled in.

1. Open `VENDMAST`.
2. For every row where `DD Supplier` = Y, complete:
   - **DD Scheme** — Core or B2B
   - **Mandate Status** — Active / Cancelled / Missing
   - **Mandate Signed** and **Treasury Approved** — dates
   - **Mandate Filed** — Y/N
   - **Expected Invoice Frequency** — Weekly / Fortnightly / Monthly / Quarterly / Annual
   - **Payment Terms (days)** if Aurora did not supply them
3. Save.

Until frequency is set, `DD_Monitor` reads `Frequency not set` and the 7-day /
15-day SLAs will not fire.

## Weekly use case — payment run and chasing

**Question:** what must we pay, what is blocked, what is a matching mess?

1. Open `Dashboard`. Read the four bands top to bottom.
   - **Payment timeliness** — open AP, overdue value, overdue %, weighted days past due. Overdue % target is below 10%.
   - **Blocked items and matching** — over-90-days (will not clear by paying faster), match exception rate, PO coverage, unusable GL codes.
   - **Direct debit control** — DD exposure, mandates not active, DD suppliers with no invoices, Core scheme share.
   - **Receipt and reconciliation** — 7-day receipt breaches, suppliers not in vendor master, AP vs master variance, concentration.
2. Scroll to the **exception queue**. Largest open amount first. Each row has a reason (no PO, not in vendor master, GL corrupted, unapplied credit, overdue 90+).
3. Work the queue:
   - *Cash timing* (recent, clean terms, just unpaid) → payment run.
   - *Blocked* (90+ days, no PO, not on vendor master) → do not just pay; fix the match first.
   - *Unapplied credit* → net off before paying the gross invoice.
4. On `AP_Log`, filter `Exception Reason` or `Status` = Overdue for the full list.
5. On `DD_Monitor`, filter `Receipt Status` for Reminder due / Escalate / No invoice activity. Send the 7-day reminder or escalate to the PO owner at 15 days (EMEA DTC Direct Debit Process).

## Monthly use case — close and P&L

**Question:** what hit the P&L, what should we accrue, who does not reconcile?

1. Paste the latest extracts (below) or rebuild.
2. `P&L_View` — spend by Flash Category and GL account. Accruals are split from posted invoices so the period is not double-counted.
3. `DD_Monitor` — `Accrual Estimate` is the expected-but-unreceived DD invoice (from that supplier's average GL invoice). That number is K12 Accrual Exposure; book it at month end.
4. `Reconciliation` — every supplier across AP, GL and vendor master.
   - Not in vendor master → create the master (no method, terms or mandate until you do).
   - Balance variance → AP log vs vendor master do not agree; investigate before signing off.
5. `Data_Quality` — assign Owner and Target date on anything with a count. Export faults (scientific-notation GL, truncated names, Excel serial dates) have to be fixed in the Aurora extract, not in this file.

## When a specific complaint comes in

| They say | You open | You look for |
|---|---|---|
| Payment is late | `Dashboard` K02/K03, then `AP_Log` Status = Overdue | Due date vs today. Split 1–90 (timing) from 90+ (blocked) |
| Amount is wrong | `AP_Log` Exception Reason, Type = CR | Partial pay, unapplied credit, terms 1 day |
| Direct debit is not working | `DD_Monitor` + `VENDMAST` | Mandate not Active, Core scheme, manual pay to a DD supplier (K16), no invoice in GL (K24) |
| Invoice does not match | `AP_Log` Exception Reason, `GL_Listing` PO Ref | Missing PO, non-standard PO, supplier not in master |
| Invoice not received on time | `DD_Monitor` Receipt Status | Frequency not set → set it. Then Reminder due / Escalate |
| Cannot match payment to supplier | `Reconciliation`, `Data_Quality` | Not in vendor master; vendor name truncated to 4 characters |

## Refreshing the extracts

**Same suppliers, new lines** — paste over the source columns on `AP_Log`,
`GL_Listing` and `VENDMAST` (A–F only). Spare blank rows are already inside
the tables. Recalculate (F9). Do not paste over calculated columns.

**New suppliers appeared** — rebuild so `Suppliers` and `Reconciliation` pick
them up:

```bash
python career/build_dashboard.py --input "C:\path\to\AP_LG_NF.CSV" --reference "C:\path\to\GL+vendorlist.xlsx"
```

Export rules that matter:

- Export the GL and vendor list as **xlsx**, never CSV. CSV drops the other
  tabs and rounds 12-digit GL accounts to `6.24E+11`.
- Format GL account as text in the extract.
- Close the dashboard file before rebuilding — WPS/Excel lock it.

## Do not

- Type over formula columns on `AP_Log` / `GL_Listing` / `DD_Monitor`.
- Save after a "repaired unreadable content" dialog.
- Treat over-90-day items as a faster payment-run problem.
- Approve a DD collection when `Mandate Status` is not Active.

**Section:** [[career]]
