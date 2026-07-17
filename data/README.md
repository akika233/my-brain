# data

Structured data — reminders, lists, trackers (JSON)

## Files
- `diet-log.json` — daily nutrition (calories, protein, carbs, fat, water, meals)
- `food-db.json` — DekaMarkt-sourced food nutrition for canvas text logging (NL + EN keywords)
- `progression.json` — weight milestones and InBody check-in dates
- `reminders.json` — reminders list

To refresh the canvas food matcher after editing `food-db.json`, run `python data/gen-food-db-ts.py` and sync into the goal-progression canvas.

**Section:** [[data]]
