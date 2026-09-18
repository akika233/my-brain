from __future__ import annotations

import calendar
import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

_CA_HOST = {"live": "ca-live.adyen.com", "test": "ca-test.adyen.com"}


def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


@dataclass
class AdyenReportConfig:
    """Config for one report subscription (one Reports -> ... -> Manage report in the CA)."""

    environment: str  # "live" | "test" | a literal hostname
    scope: str  # "MerchantAccount" | "Company"
    account_name: str  # merchant account or company account name, as shown in the CA URL
    report_type: str  # filename prefix, e.g. "payments_accounting_report"
    extension: str  # "csv" | "tsv"
    username: str  # e.g. "report@Company.YourCompanyAccount"
    password: str
    download_dir: Path

    @classmethod
    def from_env(cls) -> "AdyenReportConfig":
        def _req(key: str) -> str:
            val = os.getenv(key)
            if not val:
                raise SystemExit(
                    f"Missing required env var: {key}. Copy career/config.example.env "
                    f"to career/.env and fill in the ADYEN_* values."
                )
            return val

        return cls(
            environment=os.getenv("ADYEN_ENVIRONMENT", "live").strip().lower(),
            scope=os.getenv("ADYEN_REPORT_SCOPE", "MerchantAccount").strip(),
            account_name=_req("ADYEN_ACCOUNT_NAME"),
            report_type=os.getenv("ADYEN_REPORT_TYPE", "payments_accounting_report").strip(),
            extension=os.getenv("ADYEN_REPORT_EXTENSION", "csv").strip().lstrip("."),
            username=_req("ADYEN_REPORT_USERNAME"),
            password=_req("ADYEN_REPORT_PASSWORD"),
            download_dir=Path(
                os.getenv("ADYEN_REPORT_DOWNLOAD_DIR", "career/adyen_reports/downloads")
            ),
        )

    def _host(self) -> str:
        # Allow a literal hostname override for edge cases (e.g. region-specific CA).
        return _CA_HOST.get(self.environment, self.environment)

    def filename_for(self, report_date: date) -> str:
        return f"{self.report_type}_{report_date:%Y_%m_%d}.{self.extension}"

    def month_dir(self, report_date: date) -> Path:
        """Reports nest under a YYYY-MM subfolder so a year of monthly runs stays scannable."""
        return self.download_dir / f"{report_date:%Y-%m}"

    def url_for(self, report_date: date) -> str:
        return (
            f"https://{self._host()}/reports/download/"
            f"{self.scope}/{self.account_name}/{self.filename_for(report_date)}"
        )


def download_report(
    cfg: AdyenReportConfig, report_date: date, *, overwrite: bool = False
) -> Path | None:
    """Download a single day's report. Returns the saved path, or None if Adyen
    hasn't generated a report for that date (HTTP 404 - e.g. no transactions / weekend).

    Raises SystemExit on 401 (bad credentials - no point retrying other days) and
    re-raises other HTTP/network errors so the caller can record them as real failures.
    """
    dest_dir = cfg.month_dir(report_date)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / cfg.filename_for(report_date)
    if dest.exists() and not overwrite:
        print(f"SKIP (already downloaded)  {dest.name}")
        return dest

    url = cfg.url_for(report_date)
    resp = _session().get(
        url,
        auth=(cfg.username, cfg.password),
        headers={"Accept-Encoding": "gzip"},
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    if resp.status_code == 401:
        raise SystemExit(
            "401 Unauthorized - check ADYEN_REPORT_USERNAME/ADYEN_REPORT_PASSWORD "
            "and that the report user has the Report Download role."
        )
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"OK  {dest.name}  ({len(resp.content):,} bytes) -> {dest}")
    return dest


@dataclass
class DownloadSummary:
    """Result of a multi-day download run, so callers can tell 'no report that
    day' (fine, expected) apart from 'something actually broke' (should be loud).
    """

    downloaded: list[Path] = field(default_factory=list)
    not_found: list[date] = field(default_factory=list)
    errors: list[tuple[date, str]] = field(default_factory=list)


def download_range(
    cfg: AdyenReportConfig, start: date, end: date, *, overwrite: bool = False
) -> DownloadSummary:
    """Download every day's report from `start` to `end` (inclusive).

    Missing days (404 - no transactions / weekend) are recorded as `not_found`,
    not errors. Real failures (network errors, unexpected HTTP statuses) are
    caught per-day so one bad day doesn't abort the whole batch, and recorded
    in `errors` for the caller to surface. A 401 (bad credentials) still aborts
    immediately via SystemExit - retrying 30 more times with the same wrong
    password wastes time and can trip rate limits.
    """
    summary = DownloadSummary()
    d = start
    while d <= end:
        try:
            path = download_report(cfg, d, overwrite=overwrite)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR  {cfg.filename_for(d)}: {exc}", file=sys.stderr)
            summary.errors.append((d, str(exc)))
        else:
            if path:
                summary.downloaded.append(path)
            else:
                print(f"NOT FOUND  {cfg.filename_for(d)} (not generated / no data that day)")
                summary.not_found.append(d)
        d += timedelta(days=1)
    return summary


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """First and last calendar date of (year, month), leap-years included."""
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def download_month(
    cfg: AdyenReportConfig, year: int, month: int, *, overwrite: bool = False
) -> DownloadSummary:
    """Download every daily report for one full calendar month."""
    start, end = month_bounds(year, month)
    print(f"Downloading {cfg.report_type} reports for {year:04d}-{month:02d} ({start} to {end})...")
    return download_range(cfg, start, end, overwrite=overwrite)
