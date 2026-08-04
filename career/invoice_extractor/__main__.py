#!/usr/bin/env python3
"""
Extract invoice fields from PDFs (local folder or NF Docstore).

Field mapping (French invoices):
  supplier          ← Vendu par / left-side company (e.g. Worldpack Trading B.V.)
  invoice_date      ← Date de la facture, else Date de Paiement
  invoice_number    ← Notre référence (e.g. 00077971, Marseille - 20250017)
  po_number         ← Votre référence (e.g. IN230450)
  amount            ← Total HT
  vat_amount        ← TVA
  vat_rate          ← derived or printed %

Usage:
  python -m career.invoice_extractor --input "C:\\Users\\shjiang\\OneDrive - New Balance Athletics, Inc\\Documents\\Invoice"
  python -m career.invoice_extractor --from-docstore --lref 79954
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .docstore import LocalFolderDocstore, build_docstore_from_env, default_invoice_folder
from .parse_invoice import parse_invoice_text
from .pdf_text import extract_text
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
            text = extract_text(path)
            rec = parse_invoice_text(text, source_file=path.name)
            records.append(rec)
            print(
                f"OK  {path.name} | {rec.supplier} | {rec.invoice_date} | "
                f"Notre={rec.invoice_number} | Votre={rec.po_number} | "
                f"HT={rec.amount} | TVA={rec.vat_amount}"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {path.name}: {exc}", file=sys.stderr)
    return records


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
        help="Download from NF Docstore / configured DOCSTORE_MODE",
    )
    parser.add_argument(
        "--lref",
        action="append",
        default=[],
        help="NF Docstore LREF to download (repeatable), e.g. --lref 79954",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=None,
        help="Where downloads are saved (default: NB Invoice OneDrive folder)",
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
        help="Specific PDF file paths",
    )
    args = parser.parse_args(argv)
    download_dir = args.download_dir or default_dir

    pdf_paths: list[Path] = []

    if args.files:
        pdf_paths = list(args.files)
    elif args.from_docstore or args.lref:
        if args.lref and not os.getenv("DOCSTORE_MODE"):
            os.environ["DOCSTORE_MODE"] = "nf"
        client = build_docstore_from_env(extra_lrefs=args.lref or None)
        try:
            for doc_id in client.list_pdfs():
                pdf_paths.append(client.download(doc_id, download_dir))
        finally:
            client.close()
    else:
        folder = args.input or default_dir
        client = LocalFolderDocstore(folder)
        pdf_paths = [folder / name for name in client.list_pdfs()]

    if not pdf_paths:
        print("No PDFs found.", file=sys.stderr)
        return 1

    records = process_pdfs(pdf_paths)
    if not records:
        print("Nothing extracted.", file=sys.stderr)
        return 1

    out = save_records(records, args.output)
    print(f"Wrote {len(records)} invoice(s) → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
