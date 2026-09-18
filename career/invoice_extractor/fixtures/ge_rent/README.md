# German rent invoice fixtures (from `invoice - GE.zip`)

13 JPG scans / email crops of German commercial-rent invoices (NB Germany).
Used to harden `parse_rent_de.py` (OCR + DE/EN rent labels).

**Not** text-layer PDFs — pipeline OCRs images via RapidOCR.

## Fields targeted

| Column | German / English cues |
|---|---|
| `basic_rent` | Mindestmiete, Monatsmiete, Basismiete, Rental income |
| `service_charges` | Nebenkosten, Service Charge, VZ NK |
| `marketing_charges` | Marketingbeitrag, Werbekosten |
| `turnover_rent` | Umsatzmiete, Turnover rent |
| `storage_charges` | Storage Income, Lager |
| `service_period` | Zeitraum / Leistungsdatum → `YYYY-MM` |
| `amount` | Endbetrag / Brutto |
| `contract_number` | Vertrag / Lease ID (when no PO) |

## Run

```bash
python -m career.invoice_extractor --input "career/invoice_extractor/fixtures/ge_rent/invoice - GE" --output career/ge_rent_invoices.xlsx
```
