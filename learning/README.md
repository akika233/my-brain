# learning

Things I'm studying or practicing

## Active

- [[dutch-b1-planner]] — Dutch B1 with *Contact! 2* (3 months: Jul–Oct 2026)
- [[dutch-b1-log]] — session + chapter checklist
- **Self-contained learning module:** `learning/dutch-b1-learn.html` — Vercel (Colette on phone) or the local server
  - **Phone:** https://dutch-b1-sage.vercel.app/
  - All 8 chapters built-in: vocab flashcards + TTS audio, grammar, reading, listening, speaking, writing
  - **Reading / Listening difficulty:** NT2 II · B1→B2 — Klokhuis-style culture articles + Jeugdjournaal-style news/interview audio (see [NTI Nederlands voor anderstaligen](https://www.nti.nl/talen/nederlands/nederlands-voor-anderstaligen/), [Jeugdjournaal](https://jeugdjournaal.nl/), [Het Klokhuis](https://hetklokhuis.nl/))
  - **CD Lab:** play real Contact! 2 MP3s (tekstboek/werkboek CDs) — via local server or a folder picker
  - **30-min test per chapter:** timed listening (4 questions) + real CD sample + 2 speaking recordings
  - Dutch TTS: free **Microsoft Edge TTS** — Colette (`nl-NL-ColetteNeural`) via Vercel `/api/tts`, no Azure key
  - **GitHub Pages copies** still exist but have no TTS server — use the Vercel URL on your phone
  - **PC practice server:** same Colette MP3s via `python learning/serve-dutch-b1.py` then `http://127.0.0.1:8765/dutch-b1-learn.html`. `pip install edge-tts` once.
  - Speech recognition for speaking practice
  - Progress saved in browser (localStorage)
- **Cloud site (phone anywhere):** https://akika233.github.io/dutch-b1-site/
  - Plan + Practice UI online
  - On phone: Practice → **PDF book** / **Audio** → pick from OneDrive
  - Contact! 2 files are NOT uploaded (copyright) — pick them from your phone
- **Home PC auto-load:** `python learning/serve-dutch-b1.py`

**Section:** [[learning]]
