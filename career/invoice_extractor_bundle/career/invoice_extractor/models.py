from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class InvoiceRecord:
    source_file: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    supplier: str | None = None
    amount: float | None = None  # gross / Endbetrag when available, else net
    amount_net: float | None = None
    vat_rate: float | None = None
    vat_amount: float | None = None
    po_number: str | None = None
    contract_number: str | None = None
    currency: str | None = None
    # German/English commercial-rent breakdown (net sums)
    basic_rent: float | None = None
    service_charges: float | None = None
    marketing_charges: float | None = None
    turnover_rent: float | None = None
    storage_charges: float | None = None
    service_period: str | None = None  # e.g. "2026-03" or "2026-01;2026-02"
    service_year: int | None = None
    service_month: int | None = None
    needs_review: bool = False
    validation: str | None = None
    raw_excerpt: str | None = None
    parse_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]
