from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from .models import InvoiceRecord


def save_records(records: list[InvoiceRecord], output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()

    if suffix == ".xlsx":
        _save_xlsx(records, output_path)
    elif suffix == ".json":
        _save_json(records, output_path)
    else:
        if suffix != ".csv":
            output_path = output_path.with_suffix(".csv")
        _save_csv(records, output_path)
    return output_path


def _save_csv(records: list[InvoiceRecord], path: Path) -> None:
    fieldnames = InvoiceRecord.field_names()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_dict())


def _save_json(records: list[InvoiceRecord], path: Path) -> None:
    path.write_text(
        json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _save_xlsx(records: list[InvoiceRecord], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    headers = InvoiceRecord.field_names()
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in records:
        row = r.to_dict()
        ws.append([row.get(h) for h in headers])
    for col in ws.columns:
        letter = col[0].column_letter
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[letter].width = min(max(width + 2, 12), 48)
    wb.save(path)
