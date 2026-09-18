Invoice Extractor — Python 3.10–3.13
====================================

1. Unzip this folder. The unzipped root must contain the `career` folder.

2. Install Python 3.13 (or 3.10+). Then in this folder:

     py -3.13 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     python -m pip install -r requirements.txt

   OCR uses PaddleOCR (not rapidocr-onnxruntime).
   On Python 3.13 you need paddlepaddle 3.3+.

3. Optional (DocStore download only):

     copy config.example.env career\.env

   Edit career\.env and set DOCSTORE_USERNAME / DOCSTORE_PASSWORD.
   Chrome is required for DocStore.

Extract local PDFs or images
----------------------------
  python -m career.invoice_extractor --input "D:\path\to\invoices" --output invoices.xlsx

Extract German rent PDFs/JPGs
-----------------------------
  python -m career.invoice_extractor --input "D:\path\to\ge_rent" --output ge_rent_invoices.xlsx

Download from DocStore via Excel (DocRef + Country columns)
----------------------------------------------------------
  python -m career.invoice_extractor --from-excel "tracker.xlsx" --sheet "2026 GL listing" --download-dir invoice_pdfs --output invoices.xlsx

Notes
-----
- Always run from this unzipped root (the folder that contains `career`).
- In VS Code/Cursor: Python: Select Interpreter -> .venv\Scripts\python.exe
- Text-layer PDFs do not need OCR. JPG/PNG scans use PaddleOCR automatically.
- Never share your career\.env file
