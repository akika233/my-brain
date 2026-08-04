# career

Work notes, career goals, skills.

## Supplier dashboard

- Template builder: `build_dashboard.py` → `supplier_dashboard.xlsx`

## Invoice PDF extractor

Pull invoice fields from NF Docstore (`bosuka1:6400`) PDFs, or from the local Invoice folder.

**Field mapping (French invoices)**

| Output column | Source on PDF |
|---|---|
| `supplier` | `Vendu par`, else left-side company (e.g. Worldpack Trading B.V.) |
| `invoice_date` | `Date de la facture`, else `Date de Paiement` |
| `invoice_number` | `Notre référence` / N° commande client |
| `po_number` | `Votre référence` (e.g. IN230450) |
| `amount` | `Total HT` |
| `vat_amount` | `TVA` |
| `vat_rate` | printed % or derived (TVA / HT) |

```bash
pip install -r career/requirements-invoice.txt
# copy career/config.example.env → career/.env and set password + LREFs

# Extract PDFs already in the Invoice folder
python -m career.invoice_extractor --input "C:\Users\shjiang\OneDrive - New Balance Athletics, Inc\Documents\Invoice"

# Download LREF 79954 from NF Docstore, then extract
python -m career.invoice_extractor --from-docstore --lref 79954 --output career/invoices.xlsx
```

Docstore URL shape: `http://bosuka1:6400/docStore/store/NF%20Docstore/document/?L[LREF]=79954`

If download fails (HTML login wall / different binary URL), open the PDF download link in the browser and share that URL so the client can be pinned exactly.

**Section:** [[career]]
