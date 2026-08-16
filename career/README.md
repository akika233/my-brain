# career

Work notes, career goals, skills.

## Supplier dashboard

- Design plan: [[supplier-dashboard-plan]] — problems, data model, five views, build phases
- Template builder: `build_dashboard.py` → `supplier_dashboard.xlsx`

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
