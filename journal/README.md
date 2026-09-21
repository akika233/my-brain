# journal

Daily entries and reflections. One file per day: `YYYY-MM-DD.md`.

## Format (always)
```markdown
# [Weekday], [Month Day, Year]

## Work / career
- …

## Health / training
- …

## Learning
- …

## Personal
- …

**Section:** [[journal]]
```

Only include sections where something actually happened. Compact bullets — a log, not a diary.

## Merge protocol
1. Read `journal/YYYY-MM-DD.md` if it exists
2. **Merge** new bullets into the right section — never overwrite the whole file
3. Keep existing content; dedupe obvious repeats
4. Commit with a clear message

## Ownership
Journal Coach owns create/merge here. Domain detail still belongs in `health/`, `learning/`, `career/`, `life-admin/` when the fact is durable (not just “what happened today”).

**Section:** [[journal]]
