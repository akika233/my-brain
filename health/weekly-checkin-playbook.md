# Weekly check-in playbook

CEO-brief review of training + nutrition toward the 45 kg goal. Detail lives in the linked files — this is the operating rhythm.

## Every week (10 minutes)
1. **Diet** — skim last 7 days in `data/diet-log.json` vs targets in [[nutrition]] (1400 kcal / 95g protein). Flag protein misses first.
2. **Training** — confirm 4 Hevy sessions landed (or note misses) via [[gym-log]] / Hevy sync (`data/sync-hevy.py`).
3. **Progression** — check next milestone date in [[progression-map]] and `data/progression.json`.
4. **Body** — if an InBody or weigh-in happened, log to `data/progression.json` + [[body-composition]].
5. **One call** — keep, deload, or fix protein. One sentence.

## Every 4–6 weeks
- InBody scan → update baseline table in [[body-composition]] and checkins in `data/progression.json`
- Adjust routine weights only if form is solid (see [[workout-routine]] progression rules)

## Logging channels
| Channel | Writes |
|---|---|
| Telegram bot | `data/diet-log.json`, InBody → progression + body-composition |
| Chat with trainer | diet-log / gym-log / progression as needed |
| Hevy sync script | gym-log (+ local hevy JSON) |

## Safety rails
- Do not go below 1,200 kcal
- Fat loss from nutrition; training protects SMM
- Never invent scan numbers — ask if missing

**See also:** [[nutrition]], [[progression-map]], [[hevy-integration]]

**Section:** [[health]]
