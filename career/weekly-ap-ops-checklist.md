# Weekly AP ops checklist

Short operating checklist for Work Finance Ops. Full detail: [[supplier-dashboard-guide]], [[supplier-dashboard-process]].

## Monday — refresh
1. Close the open dashboard workbook (Excel/WPS lock)
2. Export fresh Aurora extracts (GL + vendor as **xlsx**, not CSV)
3. Paste or rebuild `supplier_dashboard.xlsx`
4. Recalculate; do **not** save a “repaired” file

## Monday — Track A (aging)
1. Read Dashboard bands: timeliness → blocked → DD → receipt
2. Work exception queue largest-first
3. Split cash-timing vs blocked (90+, no PO, not in master)
4. Filter `AP_Log` for Overdue / Exception Reason

## Monday — Track B (DD receipt)
1. Confirm `VENDMAST` frequency filled for DD suppliers
2. Filter `DD_Monitor` Reminder due / Escalate / No invoice activity
3. Send 7-day reminders; escalate at 15 days per EMEA DTC DD process
4. Never approve DD collection if Mandate Status ≠ Active

## Month-end
1. Book accrual from `DD_Monitor` Accrual Estimate (K12)
2. Check `P&L_View` Flash Category spend
3. Reconcile AP vs vendor master; assign `Data_Quality` owners

## Do not
- Mix aging fixes with missing-invoice chase
- Type over formula columns
- Treat 90+ day items as a faster payment-run problem

**See also:** [[supplier-dashboard-guide]], [[supplier-dashboard-process]]

**Section:** [[career]]
