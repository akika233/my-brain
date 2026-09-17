#!/usr/bin/env python3
"""
Extract invoice fields from PDFs (local folder or bosuka DocStore).

Field mapping (French invoices):
  supplier          <- Emetteur / Emettrice, Vendu par, letterhead company,
                       else OCR of the logo when the name is only in an image
  invoice_date      <- Date d'emission / Date de la facture / Date (French months supported)
  invoice_number    <- Facture:, Numero, Numero de l'avoir (credit notes)
  po_number         <- Votre reference, COMMANDE N PO, or POR#####/20xx##### pattern
  amount            <- Total HT / Montant Total HT
  vat_amount        <- Total TVA / Total T.V.A.
  vat_rate          <- printed % or derived from VAT / HT
  needs_review      <- set when a field is missing or HT+VAT does not reconcile with TTC

Usage:
  python -m career.invoice_extractor --input "D:\\Invoices"
  python -m career.invoice_extractor --from-docstore --country AT --lref 00011841
  python -m career.invoice_extractor --from-excel career/DTC_Retail_2026_Budget_Tracker.xlsx --sheet "2026 GL listing"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .docstore import (
    BosukaDocstore,
    LocalFolderDocstore,
    build_docstore_from_env,
    default_invoice_folder,
    read_jobs_from_excel,
)
from .pipeline import extract_invoice
from .store import save_records


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


def process_pdfs(paths: list[Path]) -> list:
    records = []
    for path in paths:
        try:
            rec = extract_invoice(path)
            records.append(rec)
            flag = " [REVIEW]" if rec.needs_review else ""
            print(
                f"OK{flag}  {path.name} | {rec.supplier} | {rec.invoice_date} | "
                f"invoice={rec.invoice_number} | po={rec.po_number} | "
                f"amt={rec.amount} | basic={rec.basic_rent} | svc={rec.service_charges} | "
                f"mkt={rec.marketing_charges} | to={rec.turnover_rent} | "
                f"stor={rec.storage_charges} | period={rec.service_period}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {path.name}: {exc}", file=sys.stderr)
    return records


def _download_from_docstore(
    *,
    jobs: list[tuple[str, str]] | None,
    lrefs: list[str] | None,
    country: str | None,
    download_dir: Path,
) -> list[Path]:
    if country:
        os.environ["DOCSTORE_COUNTRY"] = country
    if not os.getenv("DOCSTORE_MODE"):
        os.environ["DOCSTORE_MODE"] = "bosuka"

    client = build_docstore_from_env(
        extra_lrefs=None if jobs else (lrefs or None),
        jobs=jobs,
    )
    pdf_paths: list[Path] = []
    try:
        if isinstance(client, BosukaDocstore):
            client.prefetch()
        for doc_id in client.list_pdfs():
            try:
                pdf_paths.append(client.download(doc_id, download_dir))
                print(f"DL  {pdf_paths[-1].name}")
            except Exception as exc:  # noqa: BLE001
                print(f"ERR {doc_id}: {exc}", file=sys.stderr)
    finally:
        client.close()
    return pdf_paths


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    default_dir = default_invoice_folder()

    parser = argparse.ArgumentParser(description="Extract invoice info from PDFs")
    parser.add_argument(
        "--input",
        type=Path,
        help=f"Folder of local PDFs (default: {default_dir})",
    )
    parser.add_argument(
        "--from-docstore",
        action="store_true",
        help="Download from bosuka DocStore via Selenium",
    )
    parser.add_argument(
        "--from-excel",
        type=Path,
        help="Excel with DocRef + Country columns (replaces hardcoded invoice list)",
    )
    parser.add_argument(
        "--sheet",
        default=None,
        help='Excel sheet name, e.g. "2026 GL listing" (auto-detect if omitted)',
    )
    parser.add_argument(
        "--docref-col",
        default=None,
        help="Override DocRef column header (default: DocRef / AllRows.DOCREF / LREF)",
    )
    parser.add_argument(
        "--country-col",
        default=None,
        help="Override Country column header (default: Country)",
    )
    parser.add_argument(
        "--lref",
        action="append",
        default=[],
        help="DocStore LREF to download (repeatable), e.g. --lref 00011841",
    )
    parser.add_argument(
        "--country",
        default=None,
        help="DocStore country when using --lref (store = '{country} Docstore')",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=None,
        help="Where downloads are saved (default: invoice folder / RENT_TO_TEST style)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Only download PDFs; skip field extraction / Excel output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("career/invoices.xlsx"),
        help="Output .xlsx / .csv / .json",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        type=Path,
        help="Specific PDF/image file paths",
    )
    args = parser.parse_args(argv)
    download_dir = args.download_dir or default_dir

    pdf_paths: list[Path] = []

    if args.files:
        pdf_paths = list(args.files)
    elif args.from_excel:
        jobs = read_jobs_from_excel(
            args.from_excel,
            sheet=args.sheet,
            docref_col=args.docref_col,
            country_col=args.country_col,
        )
        if not jobs:
            print("No DocRef/Country rows found in Excel.", file=sys.stderr)
            return 1
        print(f"Loaded {len(jobs)} job(s) from {args.from_excel.name}")
        for country, docref in jobs[:5]:
            print(f"  {country}  {docref}")
        if len(jobs) > 5:
            print(f"  ... +{len(jobs) - 5} more")
        pdf_paths = _download_from_docstore(
            jobs=jobs,
            lrefs=None,
            country=None,
            download_dir=download_dir,
        )
    elif args.from_docstore or args.lref:
        pdf_paths = _download_from_docstore(
            jobs=None,
            lrefs=args.lref or None,
            country=args.country,
            download_dir=download_dir,
        )
    else:
        folder = args.input or default_dir
        folder = Path(folder)
        pdf_paths = [
            p
            for p in sorted(folder.iterdir())
            if p.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
        ]

    if not pdf_paths:
        print("No invoice files found.", file=sys.stderr)
        return 1

    if args.download_only:
        print(f"Downloaded {len(pdf_paths)} PDF(s) -> {download_dir}")
        return 0

    records = process_pdfs(pdf_paths)
    if not records:
        print("Nothing extracted.", file=sys.stderr)
        return 1

    out = save_records(records, args.output)
    flagged = sum(1 for r in records if r.needs_review)
    print(f"Wrote {len(records)} invoice(s) -> {out}")
    if flagged:
        print(f"{flagged} invoice(s) flagged for review (see needs_review/validation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
