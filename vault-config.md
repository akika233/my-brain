# Vault Config
This file describes the structure of this knowledge base.
Any AI tool connecting to this repo should read this first.

## Folders
- profile: about me, goals, values
- journal: daily entries (YYYY-MM-DD.md format)
- career: work notes, career goals, skills
- health: gym routine, nutrition, wellness tracking
- learning: things currently studying or practicing
- life-admin: housing, finances, practical stuff
- hobbies: fun stuff, creative projects
- data: structured data — reminders, lists, trackers (JSON)

## Data folder
- data/reminders.json — array of {date, message, label} objects
- data/diet-log.json — daily nutrition tracking (calories, macros, meals)
- data/food-db.json — DekaMarkt-sourced food nutrition for canvas meal text matching
- data/progression.json — weight milestones and InBody check-ins
- data/ is for structured/machine-readable files (JSON, CSV)
- All other content uses markdown (.md)

## Telegram bot
- `telegram-bot/` — phone logger for diet + InBody (writes the JSON files above)
- Setup: see `telegram-bot/README.md`

## Rules
- New information gets saved to the most relevant folder
- Journal entries use YYYY-MM-DD.md naming (e.g. 2026-05-28.md)
- All changes are committed and pushed to GitHub main branch
- Files are markdown (.md) format unless in data/
- Never delete files — only create, update, or move
- File names use lowercase-with-dashes (e.g. career-goals.md, not Career Goals.md)
- One topic per file — split when a file gets too long
- All .md files end with a Section footer for Obsidian compatibility
