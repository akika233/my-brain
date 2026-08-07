"""Smoke-test using text extracted verbatim from the 4 real PDFs."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from invoice_extractor.parse_invoice import parse_invoice_text

invoices = {
    # ── Sup-Invoice-CINVROU0002026000132 ─────────────────────────────────────
    "CINVROU": (
        "OPPCI Savills IM European Outlet Fund SAS (Roubaix)\n"
        "91-93 boulevard Pasteur\n75015 Paris\n"
        "New Balance France Retail SARL\n36 rue du Louvre\n75001 Paris\n"
        "Facture: CINVROU0002026000132\n"
        "Date: 23 févr. 2026\n"
        "Montant Total HT 27 317,58\n"
        "Total T.V.A. 5 463,52\n"
        "TOTAL DE LA FACTURE 32 781,10\n"
    ),
    # ── MARKM. LASER_ Invoice F-2026-02-5295 ─────────────────────────────────
    "MakeAndMark": (
        "580,00 €\n116,00 €\n696,00 €\n"
        "Facture\nNuméro F-2026-02-5295\n"
        "Date d'émission 06 fév. 2026\n"
        "Émetteur ou Émettrice\nMAKE AND MARK\n"
        "Total HT\nTotal TVA\nTotal TTC\n"
        "20% 116,00 € 580,00 €\n"
    ),
    # ── Sup-Credit-FR554UKABEC (Amazon credit note) ───────────────────────────
    "Amazon": (
        "Avoir\n"
        "Numéro de commande client Parly II - 20250017\n"
        "Numéro de l\u2019avoir FR554UKABEC\n"   # right single quote U+2019
        "Date d\u2019émission de l\u2019avoir 31 décembre 2025\n"
        "Vendu par Amazon Business EU S.à.r.l, Succursale Française\n"
        "Avoir total -9,98 €\n"
        "20,0% -8,32 € -1,66 €\n"
    ),
    # ── Sup-Invoice-251210720 (cleaning) ────────────────────────────────────
    "Cleaning": (
        "Facture N° Date de Facture Client NEW BALANCE FRANCE RETAIL SARL\n"
        "C/O DBA\n36 RUE DU LOUVRE\n75001 PARIS\n"
        "251210720 31/12/2025\n"
        "COMMANDE N° PO 20251013\n"
        "Total HT :\nTotal TVA :\nTotal TTC :\nNet à payer:\n"
        "227,69 20,00 45,54 273,23\n"
        "227,69\n45,54\n273,23\n273,23 EUR\n"
    ),
}

EXPECTED = {
    "CINVROU":    ("CINVROU0002026000132", "2026-02-23", 27317.58, 5463.52, None),
    "MakeAndMark":("F-2026-02-5295",      "2026-02-06", 580.0,    116.0,   None),
    "Amazon":     ("FR554UKABEC",          "2025-12-31", -8.32,    -1.66,   "20250017"),
    "Cleaning":   ("251210720",            "2025-12-31", 227.69,   45.54,   "20251013"),
}

all_ok = True
for name, text in invoices.items():
    r = parse_invoice_text(text, name)
    exp_num, exp_date, exp_amt, exp_vat, exp_po = EXPECTED[name]
    ok = (
        r.invoice_number == exp_num and
        r.invoice_date   == exp_date and
        r.amount         == exp_amt  and
        r.vat_amount     == exp_vat  and
        (exp_po is None or r.po_number == exp_po)
    )
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_ok = False
    print(f"{status} {name}")
    print(f"    invoice_number : {r.invoice_number!r}  (expected {exp_num!r})")
    print(f"    invoice_date   : {r.invoice_date!r}  (expected {exp_date!r})")
    print(f"    supplier       : {r.supplier!r}")
    print(f"    amount (HT)    : {r.amount}  (expected {exp_amt})")
    print(f"    vat_amount     : {r.vat_amount}  (expected {exp_vat})")
    print(f"    po_number      : {r.po_number!r}  (expected {exp_po!r})")
    print(f"    notes          : {r.parse_notes}")
    print()

print("ALL PASS" if all_ok else "SOME FAILURES — see above")
