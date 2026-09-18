"""Regression check against the four reference invoice PDFs.

Run:  python career/invoice_extractor/_test_invoices.py [pdf_folder]

Each entry is a real supplier layout that previously broke the parser, so this doubles
as documentation of which quirk each file covers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from career.invoice_extractor.pipeline import extract_invoice

DEFAULT_FOLDER = Path.home() / "Downloads"

# filename -> (invoice_number, invoice_date, amount_ht, vat_amount, po_number, quirk)
EXPECTED = {
    "Sup-Invoice-CINVROU0002026000132.pdf": (
        "CINVROU0002026000132", "2026-02-23", 27317.58, 5463.52, None,
        "'Facture:' label, 'Date: 23 fevr. 2026', 'Montant Total HT', 'Total T.V.A.', "
        "supplier in a side-by-side column",
    ),
    "MARKM. LASER_ Invoice F-2026-02-5295.pdf": (
        "F-2026-02-5295", "2026-02-06", 580.0, 116.0, None,
        "bare 'Numero' label, 'Emetteur ou Emettrice' on the next line, "
        "totals printed in a right-hand recap column",
    ),
    "Sup-Credit-FR554UKABEC.pdf": (
        "FR554UKABEC", "2025-12-31", -8.32, -1.66, "20250017",
        "credit note: negative amounts, \"Numero de l'avoir\", VAT summary row, "
        "PO buried in 'Numero de commande client'",
    ),
    "Sup-Invoice-251210720.pdf": (
        "251210720", "2025-12-31", 227.69, 45.54, "20251013",
        "tabular header with number+date on a later row, totals in a separate column, "
        "supplier only inside a logo image (recovered by OCR)",
    ),
}


def main(folder: Path) -> int:
    failures = 0
    skipped = 0

    for filename, (num, date, amount, vat, po, quirk) in EXPECTED.items():
        path = folder / filename
        if not path.is_file():
            print(f"SKIP {filename} (not found in {folder})")
            skipped += 1
            continue

        rec = extract_invoice(path)
        checks = {
            "invoice_number": (rec.invoice_number, num),
            "invoice_date": (rec.invoice_date, date),
            "amount": (rec.amount, amount),
            "vat_amount": (rec.vat_amount, vat),
        }
        if po is not None:
            checks["po_number"] = (rec.po_number, po)

        wrong = {k: v for k, v in checks.items() if v[0] != v[1]}
        if wrong:
            failures += 1
            print(f"FAIL {filename}")
            for field, (got, want) in wrong.items():
                print(f"       {field}: got {got!r}, want {want!r}")
        else:
            print(f"PASS {filename}")
        print(f"       covers: {quirk}")
        print(f"       supplier={rec.supplier!r} review={rec.needs_review} | {rec.validation}")

    print()
    if failures:
        print(f"{failures} FAILURE(S)")
        return 1
    print(f"ALL PASS ({len(EXPECTED) - skipped} checked, {skipped} skipped)")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_FOLDER
    raise SystemExit(main(target))
