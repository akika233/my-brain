# Invoice Extractor — 20-minute speaking script

**Audience:** finance / AP / DTC retail ops (adapt names as needed)  
**Length:** ~20 minutes speaking (+ optional 5 min Q&A)  
**Demo assets:** Excel output, sample PDFs, DocStore → Excel flow  

**Section:** [[career]]

---

## Timing overview

| Mins | Section | Goal |
|---:|---|---|
| 0–2 | Opening | Why this matters |
| 2–5 | Problem | What was painful today |
| 5–9 | Solution overview | What the tool does end-to-end |
| 9–14 | How it works (demo) | Download → extract → Excel |
| 14–17 | Hard problems we solved | Layout, OCR, validation |
| 17–19 | Limits & next steps | Honest scope |
| 19–20 | Close | Ask / next decision |

---

## [0:00–2:00] Opening

Good [morning/afternoon]. I’m going to walk through a small tool we built to speed up invoice capture for retail invoices — especially French layouts — and to connect it to the documents we already pull from DocStore.

The outcome I care about is simple:

> Take a list of document references from Excel, download the PDFs from DocStore, pull the key fields into a structured spreadsheet, and flag anything that needs a human look.

This is not a full AP automation platform. It’s a practical extractor that fits how we already work: Aurora / DocStore for documents, Excel for tracking.

By the end of these 20 minutes you should know:

1. What problem it solves  
2. What fields it returns  
3. How you’d run it on a real batch  
4. Where it is reliable today — and where it still needs review  

---

## [2:00–5:00] The problem

Today, for many invoices, the flow is still manual:

- Someone finds the LREF / DocRef in a listing  
- Opens DocStore  
- Downloads the PDF  
- Re-types supplier, invoice number, date, HT, TVA, PO into Excel or a tracker  

That creates three costs:

1. **Time** — especially with multi-country DocStores and many small invoices  
2. **Errors** — copy/paste mistakes on amounts and dates  
3. **Inconsistency** — French invoices don’t all use the same labels (`Total HT`, `Montant Total HT`, `Numéro`, `Date d’émission`, credit notes, logo-only suppliers…)

We also saw that “just scrape the PDF text” is not enough. Some PDFs look fine to a human but break a naive parser because:

- Columns get merged when text is flattened  
- The supplier name may exist only inside a logo image  
- Credit notes are negative and easy to mis-read  

So the goal was: **reliable enough for a first pass**, with **clear review flags**, not silent wrong numbers.

---

## [5:00–9:00] Solution overview

### What you get

One command (or a short scripted run) that can:

1. Read **DocRef** + **Country** from Excel (for example the `2026 GL listing` sheet)  
2. Download PDFs from bosuka DocStore (`{Country} Docstore`)  
3. Extract fields into an Excel file  

**Output columns:**

| Column | Meaning |
|---|---|
| `source_file` | PDF name |
| `invoice_number` | Facture / numéro / avoir |
| `invoice_date` | Emission / facture date |
| `supplier` | Émetteur / letterhead / OCR logo fallback |
| `amount` | Total HT |
| `vat_rate` | % or derived |
| `vat_amount` | Total TVA |
| `po_number` | PO / commande patterns when present |
| `currency` | Usually EUR |
| `needs_review` | True if something looks incomplete or inconsistent |
| `validation` | Why it was flagged |
| `raw_excerpt` / `parse_notes` | Debug context |

### Design principles

Three principles guided the build:

1. **Use what we already have** — DocStore + Excel, no new portal  
2. **Prefer text when the PDF has it** — OCR only when a field is missing  
3. **Never trust silently** — arithmetic checks (HT + TVA ≈ TTC) and missing-field flags  

### Package location (if someone asks)

- Source: `career/invoice_extractor/`  
- Portable zip: `career/invoice_extractor_bundle.zip` (also in Downloads)  
- Run from repo: `python -m career.invoice_extractor ...`

---

## [9:00–14:00] Demo walkthrough *(speak while showing screen)*

### Step A — Excel as the job list

Instead of hardcoding invoice numbers in a Python string, we read:

- **DocRef** (aliases: `DocRef`, `AllRows.DOCREF`, `LREF`)  
- **Country** (e.g. `AT`, `NG`, `FR`)  

Example from our budget tracker: sheet `2026 GL listing`.

So if Country = `AT` and DocRef = `00011841`, the tool opens:

`…/store/AT%20Docstore/document/?L[LREF]=00011841`

and saves:

`AT_00011841.pdf`

**Talking point:** This matches the old Selenium script people already used, but driven by Excel and reusable across countries.

### Step B — Download

Show the command (or talk through it):

```text
python -m career.invoice_extractor ^
  --from-excel career/DTC_Retail_2026_Budget_Tracker.xlsx ^
  --sheet "2026 GL listing" ^
  --download-dir RENT_TO_TEST ^
  --download-only
```

Credentials stay in `.env` — not in the script.

### Step C — Extract

Same tool, without `--download-only`, writes structured Excel:

```text
python -m career.invoice_extractor ^
  --from-excel ... ^
  --download-dir career/invoice_pdfs ^
  --output career/invoices.xlsx
```

Or extract PDFs you already have:

```text
python -m career.invoice_extractor --input "path\to\pdfs" --output career/invoices.xlsx
```

### Step D — Review the output

Open `invoices.xlsx` and point to:

- Clean rows: supplier, date, HT, TVA filled  
- Rows with `needs_review = True` — those are the ones a person should spot-check  
- Credit notes: negative HT / TVA  

**Talking point:** The point of `needs_review` is to make the tool useful in production without pretending it’s 100% automatic.

---

## [14:00–17:00] Hard problems we solved *(keep this light, not too technical)*

### 1) Layout destruction

Early versions failed not because French labels were unknown, but because PDF text extractors flattened two-column layouts into one line. Supplier names got glued to “À l’attention de…”.

**Fix:** rebuild text from word coordinates — preserve visual rows and column gaps — then parse.

### 2) Logo-only suppliers

Some invoices have a full text layer for amounts, but the supplier exists only as pixels in the letterhead.

**Fix:** if supplier is missing *and* there are images, OCR only the top letterhead band — not the whole page. We pick the visually largest text (brand size), then still flag for review.

### 3) Silent wrong amounts

A credit note could be parsed as positive if a regex ate the minus sign.

**Fix:** validation — HT + VAT should reconcile with TTC; missing core fields force review.

### 4) DocStore download that actually works

Pure HTTP login attempts were unreliable against bosuka. The working approach is the one ops already used: Selenium to find the PDF link, then `requests` with basic auth to download.

**Upgrade:** Excel-driven Country + DocRef, multi-country in one run, dedupe duplicates.

---

## [17:00–19:00] Limits & next steps

### Honest limits today

- Best on **French-style** labels we trained/tested against; other languages need more samples  
- **PO** is often missing on the PDF — we can’t invent it  
- OCR supplier names can misread characters → always review-flagged  
- Needs **Chrome + network/VPN** for DocStore  
- This is a **first-pass extractor**, not posting into ERP  

### Suggested next steps

1. Run on a real week of DocRefs from the GL listing and measure review rate  
2. Expand fixtures with more real NB supplier layouts (highest value)  
3. Optional: supplier alias file for recurring logo-only vendors  
4. Optional: harden date/number patterns from synthetic French test packs  

### Decision I’d like from the group

- Is “download + Excel extract + review flag” the right operating model for DTC retail invoice capture?  
- Who owns the weekly run (AP / finance ops)?  
- Which Excel should be the official job list source?

---

## [19:00–20:00] Close

To summarise in one sentence:

> We built a local Python tool that turns DocStore PDFs — selected from Excel Country + DocRef — into a structured invoice table, with validation flags so people only touch the exceptions.

Happy to take questions — especially on accuracy, who runs it, and how it should plug into the budget tracker / supplier dashboard.

---

## Optional Q&A prompts *(if silence)*

- “How accurate is it?” → On our four French reference PDFs, core fields extract; logo suppliers recover with OCR + review flag. Production accuracy depends on supplier mix — we should measure on a live batch.  
- “Does it replace DocStore?” → No. It uses DocStore.  
- “Can IT host this?” → Today it’s a laptop/script tool; packaging as a scheduled job is possible later.  
- “Security?” → Credentials in local `.env`, processing stays local; no invoice data sent to an external AI API for the core path.  
- “Why not buy a vendor OCR product?” → Possible later; this was built to fit our DocStore + Excel workflow quickly and stay under our control.

---

## Slide checklist (if you make slides)

1. Title — Invoice capture helper  
2. Problem — manual download + retype  
3. Outcome — Excel in, Excel out  
4. Field list table  
5. Architecture (Excel → DocStore → PDF → Extract → Excel)  
6. Demo screenshot of output  
7. `needs_review` example  
8. Hard problems (3 bullets)  
9. Limits / next steps  
10. Ask / decision  

---

## Demo backup plan

If DocStore/VPN is down in the room:

1. Show pre-downloaded PDFs in a folder  
2. Run extract-only: `--input … --output invoices.xlsx`  
3. Open the Excel and walk the columns  

If Python fails:

1. Open a prepared `invoices.xlsx`  
2. Show before/after on one PDF  
3. Show the command text on a slide  

---

## Speaking tips

- Stay at business level until the “hard problems” section; then max 3 minutes of tech  
- Always come back to **time saved** and **fewer silent errors**  
- Don’t oversell accuracy — sell **first pass + review queue**  
- If asked for code depth: point to `career/invoice_extractor/` and offer a separate technical deep-dive  

**See also:** [[README]]
