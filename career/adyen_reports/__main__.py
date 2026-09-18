#!/usr/bin/env python3
"""
Download scheduled Adyen reports (Customer Area -> Reports -> ... -> Manage report ->
Automatic) via their predictable daily filename, e.g. payments_accounting_report_2026_07_08.csv.

This does NOT trigger report generation - the report subscription must already be set
to auto-generate on a schedule in the Adyen Customer Area. This script just fetches the
files once they exist.

This is meant to be run manually, whenever you want to top up your local reports -
there's no scheduled task. Default behaviour (no args): downloads every daily report
from the 1st of the current month through yesterday, into a per-month subfolder.
Files already on disk are skipped, so running it repeatedly (e.g. a few times a
month) is safe and only fetches what's new. If you skip a whole month, use --month
or --start/--end to backfill it manually.

Usage:
  # Just run it: tops up the current month (1st through yesterday)
  python -m career.adyen_reports

  # A specific month (e.g. to backfill one you missed)
  python -m career.adyen_reports --month 2026-07

  # Backfill an arbitrary date range
  python -m career.adyen_reports --start 2026-08-01 --end 2026-08-08

  # One specific date
  python -m career.adyen_reports --date 2026-08-05
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from .downloader import (
    AdyenReportConfig,
    DownloadSummary,
    download_month,
    download_range,
    download_report,
)


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _parse_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _parse_month(raw: str) -> tuple[int, int]:
    dt = datetime.strptime(raw, "%Y-%m")
    return dt.year, dt.month


def _finish(summary: DownloadSummary, label: str) -> int:
    print(
        f"\n{label}: {len(summary.downloaded)} downloaded, "
        f"{len(summary.not_found)} not found, {len(summary.errors)} error(s)"
    )
    if summary.errors:
        print("Completed WITH ERRORS - see above.", file=sys.stderr)
        return 1
    if not summary.downloaded:
        print(
            "WARNING: nothing was downloaded for this range. Check ADYEN_REPORT_TYPE, "
            "ADYEN_ACCOUNT_NAME, and that reports are actually being auto-generated "
            "for these dates in the Customer Area.",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()

    parser = argparse.ArgumentParser(description="Download scheduled Adyen reports")
    parser.add_argument(
        "--month",
        type=_parse_month,
        help="Download one full month (YYYY-MM). Default: current month, 1st through yesterday.",
    )
    parser.add_argument("--date", type=_parse_date, help="Download one specific date (YYYY-MM-DD)")
    parser.add_argument("--start", type=_parse_date, help="Backfill start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=_parse_date, help="Backfill end date (YYYY-MM-DD, default today)")
    parser.add_argument("--overwrite", action="store_true", help="Re-download even if the file already exists")
    args = parser.parse_args(argv)

    cfg = AdyenReportConfig.from_env()

    if args.date:
        path = download_report(cfg, args.date, overwrite=args.overwrite)
        if not path:
            print(f"No report found for {args.date}.", file=sys.stderr)
            return 1
        print(f"Done: {path}")
        return 0

    if args.start:
        end = args.end or date.today()
        summary = download_range(cfg, args.start, end, overwrite=args.overwrite)
        return _finish(summary, f"{args.start} to {end}")

    if args.month:
        year, month = args.month
        summary = download_month(cfg, year, month, overwrite=args.overwrite)
        return _finish(summary, f"{year:04d}-{month:02d}")

    today = date.today()
    start = today.replace(day=1)
    end = today - timedelta(days=1)
    if start > end:
        print("The current month just started - nothing to download yet.")
        return 0
    summary = download_range(cfg, start, end, overwrite=args.overwrite)
    return _finish(summary, f"{start} to {end}")


if __name__ == "__main__":
    raise SystemExit(main())
