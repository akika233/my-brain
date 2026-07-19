# Telegram diet + InBody bot

Logs meals and InBody scans into this vault from your phone.

## What it writes

| Action | File |
|---|---|
| Meals / water / notes | `data/diet-log.json` |
| Food matching | `data/food-db.json` |
| InBody check-in | `data/progression.json` + `health/body-composition.md` |

## Setup (once)

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token
2. In this folder:

```powershell
cd telegram-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

3. Put your token in `.env` as `TELEGRAM_BOT_TOKEN=...`
4. Start the bot, message it `/whoami`, put that id in `.env` as `TELEGRAM_ALLOWED_USER_ID=...`
5. Restart the bot

## Run

```powershell
cd telegram-bot
.\.venv\Scripts\Activate.ps1
python bot.py
```

Leave this terminal open (or run it as a Windows background service / Task Scheduler later).

## Usage

- Send what you ate — macros are estimated and added to `data/diet-log.json`
  - Precise: `kipfilet 120g + rijst 80g + broccoli 200g` (uses food-db)
  - Free-form: `I ate a cheese sandwich and some melon`
- Meal / package photo — send a picture of food OR the voedingswaarden label
  - Optional caption: `100g`, `hele bak`, `half`
  - Needs `GEMINI_API_KEY` (free) or `OPENAI_API_KEY` in `.env`
- `/today` — progress vs 1400 kcal / 95g protein targets
- `/water 300`
- `/undo`
- `/inbody` — step-by-step scan entry
- `/inbody_quick 49.2kg smm 20.8 pbf 25.1 ecw 0.365`

Optional in `.env`:
- `GEMINI_API_KEY` — free vision for photos/labels ([get key](https://aistudio.google.com/apikey))
- `OPENAI_API_KEY` — alternative vision/text AI
- `GIT_AUTO_COMMIT=true` (and `GIT_AUTO_PUSH=true`) — commit each log to git
