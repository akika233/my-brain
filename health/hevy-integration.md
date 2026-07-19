# Hevy Integration

Workout data is synced from the [Hevy app](https://www.hevyapp.com/).

## Setup

- API key is stored locally in `.env` (not committed to GitHub — stays on your machine only)
- Key: `HEVY_API_KEY` in `.env`

## What Hevy tracks

- Exercise logs (sets, reps, weight)
- Workout routines
- Personal records (PRs)

## Active routines (updated 2026-07-14 — InBody-optimized)

4-day Back/Glutes/Core split — see [[workout-routine]] for full details.

| Routine | Hevy ID |
|---|---|
| Back & Core A | `067b1a60-bc19-4801-a645-2a97186ca2dc` |
| Glutes & Legs A | `044cd783-941e-4936-b396-4fc8bfe2ff94` |
| Back & Core B | `604fdbcd-499e-4e46-bb3c-16fe54d2bea4` |
| Glutes & Posterior Chain B | `8bf4249c-47a9-49fb-95d8-9fd056388c06` |

## Notes

- Last sync: **2026-07-20** — 2 workouts, 4 routines → `health/hevy-workouts.json` + [[gym-log]]
- Re-sync anytime: `python data/sync-hevy.py` (use `telegram-bot\.venv` if needed)
- The AI can fetch your Hevy workout history when you ask about training progress
- Hevy API docs: [https://api.hevyapp.com/docs](https://api.hevyapp.com/docs)

**Section:** [[health]]
