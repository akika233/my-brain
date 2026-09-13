# learning

Things I'm studying or practicing

## Active

- [[dutch-b1-planner]] — Dutch B1 with *Contact! 2* (3 months: Jul–Oct 2026)
- [[dutch-b1-log]] — session + chapter checklist
- **Self-contained learning module:** `learning/dutch-b1-learn.html` — open on GitHub Pages or the local server
  - **Phone:** https://akika233.github.io/dutch-b1-site/dutch-b1-learn.html
  - All 8 chapters built-in: vocab flashcards + TTS audio, grammar, reading, listening, speaking, writing
  - **Reading / Listening difficulty:** NT2 II · B1→B2 — Klokhuis-style culture articles + Jeugdjournaal-style news/interview audio (see [NTI Nederlands voor anderstaligen](https://www.nti.nl/talen/nederlands/nederlands-voor-anderstaligen/), [Jeugdjournaal](https://jeugdjournaal.nl/), [Het Klokhuis](https://hetklokhuis.nl/))
  - **CD Lab:** play real Contact! 2 MP3s (tekstboek/werkboek CDs) — via local server or a folder picker
  - **30-min test per chapter:** timed listening (4 questions) + real CD sample + 2 speaking recordings
  - Dutch TTS: prefers **Colette** (`nl-NL-ColetteNeural`)
  - **Phone / GitHub Pages:** browser Dutch voice (Colette if Windows/Edge has it). No extra server.
  - **PC practice server:** neural Colette MP3s via `python learning/serve-dutch-b1.py` then `http://127.0.0.1:8765/dutch-b1-learn.html`. `pip install edge-tts` once.
  - Speech recognition for speaking practice
  - Progress saved in browser (localStorage)
- **Cloud site (phone anywhere):** https://akika233.github.io/dutch-b1-site/
  - Plan + Practice UI online
  - On phone: Practice → **PDF book** / **Audio** → pick from OneDrive
  - Contact! 2 files are NOT uploaded (copyright) — pick them from your phone
- **Home PC auto-load:** `python learning/serve-dutch-b1.py`

**Section:** [[learning]]
