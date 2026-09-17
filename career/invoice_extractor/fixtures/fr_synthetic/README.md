# French synthetic invoice fixtures

Source: [djo33350/french-synthetic-document-test-samples](https://huggingface.co/datasets/djo33350/french-synthetic-document-test-samples)  
Licence: **CC BY 4.0** (attribution required; fully synthetic / fictional parties)

## Contents

| PDF | Domain | Notes in dataset |
|---|---|---|
| `EC-01-D03.pdf` | E-commerce | clean |
| `EC-07-D02.pdf` | E-commerce | duplicate invoice-number scenario |
| `BT-01-D03.pdf` | Construction / BTP | clean (document may be labeled devis/solde) |
| `BT-07-D02.pdf` | Construction / BTP | incorrect VAT amount scenario |
| `RE-01-D03.pdf` | Restaurant | clean |
| `RE-07-D02.pdf` | Restaurant | printed total mismatch |

Ground truth JSON lives in `ground_truth/` (amounts in **cents**).

## Other useful sources (not downloaded here)

| Source | What | Fit for us |
|---|---|---|
| Same HF repo commercial packs (~€29/sector) | More FR PDF+JSON pairs | Best volume of French layouts |
| [Kaggle Generated Invoices](https://www.kaggle.com/datasets/jakubgal/generated-invoices) | Multilingual synthetic PDF+JSON | Good volume; filter to FR |
| [invoice2data](https://github.com/invoice-x/invoice2data) | YAML template library + community templates | Pattern ideas, not NB layouts |
| Your DocStore / Invoice folder | Real NB supplier PDFs | Highest value for production accuracy |

Do **not** scrape random real company invoices from the web — privacy / copyright risk. Prefer synthetic fixtures + your own internal PDFs.
