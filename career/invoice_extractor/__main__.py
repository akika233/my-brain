#!/usr/bin/env python3
"""
Extract invoice fields from PDFs (local folder or NF Docstore).

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
  python -m career.invoice_extractor --input "C:\\Users\\shjiang\\OneDrive - New Balance Athletics, Inc\\Documents\\Invoice"
  python -m career.invoice_extractor --from-docstore --lref 79954
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .docstore import LocalFolderDocstore, build_docstore_from_env, default_invoice_folder
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
    flagged = sum(1 for r in records if r.needs_review)
    print(f"Wrote {len(records)} invoice(s) -> {out}")
    if flagged:
        print(f"{flagged} invoice(s) flagged for review (see needs_review/validation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
