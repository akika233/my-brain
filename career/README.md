# career

Work notes, career goals, skills.

## Supplier dashboard

Design plan: [[supplier-dashboard-plan]] — problems, data model, five views, build phases.

`aurora_extracts.py` reads the three Aurora exports; `build_dashboard.py` turns them
into a formula-driven workbook. The readers normalise Aurora's AS/400 conventions —
`CYYMMDD` dates (`1260204` → 2026-02-04), `CYYPP` periods (`12601` → 2026-01),
space-padded codes — plus the AP log's own mix of `dd/mm/yy`, bare Excel serials and
`00/00/00` for "no due date".

```bash
pip install openpyxl
python career/build_dashboard.py \
  --input "C:\path\to\AP_LG_NF.CSV" \
  --reference "C:\path\to\GL+vendorlist.xlsx"
```

`--reference` is the workbook holding the GL listing and vendor list tabs (defaults
`--gl-sheet Sheet1`, `--vendor-sheet Sheet2`; header rows are found by looking for
`ACCN08` and `SUPN05`, so title and control-total rows above them are fine). Omit it
and the workbook still builds from the AP log alone.

Output is `career/supplier_dashboard.xlsx`:

| Sheet | What it is for |
|---|---|
| `Dashboard` | 16 KPI tiles in four bands, five charts, exception queue |
| `KPI_Definitions` | all 24 KPIs with formula, source, owner, target, cadence |
| `AP_Log` | open items plus calculated columns, as Excel table `AP_Data` |
| `GL_Listing` | the GL extract plus a vendor-master presence flag |
| `VENDMAST` | vendor list plus the DD mandate columns AP maintains |
| `DD_Monitor` | direct debit control, driven by `VENDMAST` + `GL_Listing` |
| `Reconciliation` | every supplier across all three extracts, with variances |
| `Suppliers` | per-supplier exposure and concentration |
| `P&L_View` | spend by Flash Category and GL account, accruals split out |
| `Data_Quality` | export faults to fix at source, with owner columns |
| `_Calc` | hidden chart and spill helpers |

Every KPI is an Excel formula, so refreshing an extract in place recalculates the
workbook without re-running Python. Re-run the script when the supplier population
changes — `Suppliers` and `Reconciliation` are materialised at build time. The source
tables keep spare blank rows inside their ranges so pasted data is picked up without
anyone resizing them. The exception queue needs Excel 365 (`FILTER`/`SORT`); on older
Excel, filter `AP_Log` on Exception Reason instead.

`DD Supplier` on VENDMAST is derived from `PMTH05`, so it never drifts. The mandate
columns (scheme, status, signed, treasury approved, filed) and expected invoice
frequency are not in Aurora — they come from the AP mandate repository, and the
receipt control stays dormant until the frequency column is filled in.

Direct debit thresholds come from the *EMEA DTC Direct Debit Process* document:
reminder at 7 calendar days past the expected invoice date, escalation 15 days after
that, and mandate completeness requiring signature, treasury approval and filing.

The AP export and the generated workbook are gitignored — they hold real supplier data.

## Invoice PDF extractor

Pull invoice fields from bosuka DocStore PDFs (Selenium + basic auth), or from a local folder.

```bash
pip install -r career/requirements-invoice.txt
# copy career/config.example.env → career/.env
# set DOCSTORE_USERNAME, DOCSTORE_PASSWORD, DOCSTORE_COUNTRY, DOCSTORE_LREFS
# Chrome must be installed (Selenium Manager fetches the driver)

# Extract PDFs already on disk
python -m career.invoice_extractor --input "C:\Users\shjiang\OneDrive - New Balance Athletics, Inc\Documents\Invoice"

# Download by LREF from DocStore, then extract
python -m career.invoice_extractor --from-docstore --country NG --lref 221566 --lref 223663 --output career/invoices.xlsx
```

DocStore page URL shape:
`http://bosuka1.newbalance.com:6400/docStore/store/NG%20Docstore/document/?L[LREF]=221566`

Downloads are saved as `{country}_{LREF}.pdf` (e.g. `NG_221566.pdf`).

## Adyen scheduled report downloader

Run it manually whenever you want to top up your local reports. It downloads every
daily Adyen report (default: Payment Accounting Report) using Adyen's predictable
report-download URL. No webhook/server, no scheduled task - just run the command.

**One-time setup (in the Adyen Customer Area):**
1. Reports -> \<report type\> (e.g. Payment Accounting) -> Manage report -> set **Automatic generation: On**, pick CSV, daily.
2. Developers -> Users (or API credentials) -> create a **Report** user, assign the Report Download role, and set its password (this is separate from your normal API key).
3. Note your **merchant account name** (or company account name) exactly as it appears in the CA.

```bash
pip install -r career/requirements-adyen.txt
# copy career/config.example.env -> career/.env and fill in the ADYEN_* values

# Just run it: downloads the current month, 1st through yesterday
python -m career.adyen_reports

# Missed a month? Backfill it explicitly
python -m career.adyen_reports --month 2026-07

# Backfill an arbitrary date range, or one specific date
python -m career.adyen_reports --start 2026-08-01 --end 2026-08-08
python -m career.adyen_reports --date 2026-08-05
```

Files land in a per-month subfolder: `{ADYEN_REPORT_DOWNLOAD_DIR}/2026-07/payments_accounting_report_2026_07_01.csv`, etc. Re-running the same range skips files that already exist (unless `--overwrite`), so running it repeatedly - even several times a day - is safe and only fetches what's new.

A day with no report (weekend, holiday, no transactions) is reported as "not found" and skipped - that's expected. A real failure (bad credentials, network error) makes the run exit non-zero and print the error, instead of silently pretending it worked.

URL pattern used (see [Adyen's automatic reports guide](https://docs.adyen.com/reporting/automatically-get-reports/)):
`https://ca-live.adyen.com/reports/download/MerchantAccount/{ADYEN_ACCOUNT_NAME}/{ADYEN_REPORT_TYPE}_{YYYY_MM_DD}.csv`, authenticated with HTTP Basic Auth using the Report user's credentials.

If you later want reports the moment they're generated instead of pulling them yourself, Adyen also supports a `balancePlatform.report.created` / `REPORT_AVAILABLE` webhook - but that requires hosting a public HTTPS endpoint to receive it, which this script deliberately avoids.

**Section:** [[career]]
