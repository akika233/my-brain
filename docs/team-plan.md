# Team plan — which teammate agents to create next

Coordinator-facing plan. Paste this as-is. Grounded in the current `my-brain` vault (read 2026-09-18). No teammate agent definitions, personas, or skills folders exist yet. The only “agents” already in the repo are the always-on Cursor vault assistant, a Telegram diet/InBody logger, and a Dutch-tutor prompt inside the B1 practice stack.

---

## What my-brain is for

`my-brain` is a personal operating system: an Obsidian-compatible Git vault that an AI is supposed to read, update, commit, and push. `vault-config.md` and `.cursor/rules/brain.mdc` define eight life areas (`profile/`, `journal/`, `career/`, `health/`, `learning/`, `life-admin/`, `hobbies/`, `data/`). New facts get filed, never deleted; journal days are merged, not overwritten.

In practice the vault is not evenly built. Two written personal goals live in `profile/goals.md`:

1. **45 kg body composition** by ~1 Dec 2026 (4-day Hevy strength + ~1,400 kcal / 95 g protein + InBody every 4–6 weeks).
2. **Dutch B1** with *Contact! 2*, 22 Jul → 22 Oct 2026 (Mon/Tue/Thu 21:00–23:00).

The third live system is **work**, not a personal goal: `career/` is an AP / Retail Finance toolkit for New Balance DTC (Aurora extracts, supplier dashboard, invoice OCR/DocStore, budget-tracker PO↔GL match, Adyen report pull). `life-admin/` and `hobbies/` are empty stubs. `profile/` has email and those two goals — no values file, no career-goals file, no skills inventory.

The coordinator already exists in spirit: `.cursor/rules/brain.mdc` is a generalist vault keeper. Specialists should be created only where the vault already has process, cadence, and data. Do not staff empty folders.

---

## Verdict on the three suspected roles

| Role | Verdict | Why |
|---|---|---|
| **Personal trainer** | **Create (Phase 1)** | Health is one of two written goals. Full program, InBody strategy, Hevy IDs, gym log, and slipping check-ins already exist. |
| **Accountant** | **Create the work version (Phase 2). Do not create a personal accountant yet.** | `career/` is an AP operating file with Monday/month-end cadence, named human roles (AP clerk, AP lead, Retail Finance, Treasury), invoices, GL, DD mandates. `life-admin/` promises “housing, finances” but contains only a README — there is nothing for a household/tax accountant to own. |
| **Career mentor** | **Reject until source material exists (Phase 3+)** | `career/README.md` says “career goals, skills” but the folder is 100% operational finance tooling. No promotion path, skill gaps, CV, or mentoring notes. A mentor agent would invent a career. Revisit only after `career/career-goals.md` (or similar) is written. |

---

## Recommended roster (build first → later)

| # | Name | One-line job |
|---|---|---|
| 1 | **Vault Keeper** | Routes new facts into the right file, merges today’s journal, commits/pushes, and refuses to invent empty life areas. |
| 2 | **Dutch Tutor** | Runs the *Contact! 2* B1 plan: speaking partner, writing corrections, session log, chapter pace. |
| 3 | **Personal Trainer** | Owns the 4-day back/glutes/core split, progressive overload, and InBody muscle-preservation checks toward 45 kg. |
| 4 | **Nutrition Coach** | Hits 1,400 kcal / 95 g protein; logs meals into `data/diet-log.json`; keeps `food-db.json` honest. |
| 5 | **AP Ops Copilot** | Monday aging vs DD-receipt pack, month-end accruals, invoice extract, PO↔GL match — the accountant the repo actually needs. |
| 6 | **Weekly Reviewer** | Sunday (or Monday AM) scoreboard: gym days, protein days, Dutch nights, InBody/weigh-in calendar, vault hygiene. |
| 7 | **Life Admin** | Housing, NL practicalities, personal reminders — only after `life-admin/` has real notes. |
| — | *Personal accountant* | Not a teammate until household money exists in the vault. |
| — | *Career mentor* | Not a teammate until career goals/skills exist. |
| — | *Hobbies / creative* | Folder is empty; do not staff. |
| — | *Dating / life-coach* | Mentioned only as a journal section in `brain.mdc`; zero content. |

If you want fewer agents this week, merge **Personal Trainer + Nutrition Coach** into one **Body Coach**. Keep them split if you can: Hevy vs Telegram/food-db are different connectors and cadences (4 gym days vs every meal).

---

## Role specs

### 1. Vault Keeper (coordinator)

**Why it belongs.** This is the only agent the repo already specifies. `.cursor/rules/brain.mdc` is titled “My Personal AI Assistant”: check vault files before answering, auto-save to the right folder, merge journals, never delete, Obsidian `[[wiki-links]]` + `**Section:**` footers, commit and push to `main`. `vault-config.md` is the onboarding doc “any AI tool connecting to this repo should read first.” Without this role, specialists will overwrite each other or skip git.

**Connectors / tools.** GitHub (`akika233/my-brain`); markdown vault; optional `GIT_AUTO_COMMIT` / `GIT_AUTO_PUSH` already used by `telegram-bot/`. No extra APIs.

**Recurring work.**

- File anything the user says into the matching folder (examples in `brain.mdc`).
- Merge `journal/YYYY-MM-DD.md` using the four allowed sections: Work/career, Health/training, Learning, Personal.
- Keep filenames `lowercase-with-dashes`; one topic per file.
- Do not create hobbies/life-admin/career-goal notes unless the user actually said something.
- Hand off: Dutch nights → Dutch Tutor; workouts → Trainer; meals → Nutrition; Aurora/AP → AP Ops.

**Create this week.** Yes — make the current `brain.mdc` generalist an explicit teammate so others stay in their lanes.

---

### 2. Dutch Tutor

**Why it belongs.** Second written goal in `profile/goals.md`. Full 12-week plan in `learning/dutch-b1-planner.md` (22 Jul → 22 Oct 2026, 8 chapters, Mon/Tue/Thu 21:00–23:00). Session template and empty chapter checklist in `learning/dutch-b1-log.md`. Practice stack: `learning/dutch-b1-learn.html`, GitHub Pages (`docs/`, `https://akika233.github.io/my-brain/`), local server `learning/serve-dutch-b1.py`, TTS Colette, CD Lab, 30-min chapter tests. `learning/transcript_ai.py` already hard-codes the persona: *“You are a Dutch B1 tutor.”* Planner rule: treat study slots like gym appointments; speak every session; log every night.

**Urgency.** As of 2026-09-18 the plan is in month 3 (H6–H8 + review). The log still shows all 8 chapters unchecked and only a 22 Jul “planner created” entry. Month 2 checkpoint (15 Sep) is already due. This agent is time-critical.

**Connectors / tools.**

- Vault: `learning/dutch-b1-planner.md`, `learning/dutch-b1-log.md`, `learning/README.md`.
- Local/OneDrive materials (copyright — not in git): `C:\Users\akika\OneDrive\Documents\OneDrive\Documents\Contact 2 (B1)` (PDFs + CDs). Phone: pick PDF/audio from OneDrive via the Pages site (`docs/README.md`).
- Gemini (`GEMINI_API_KEY`) for CD transcription + writing review (`transcript_ai.py`, learn-page review).
- Edge TTS `nl-NL-ColetteNeural` (or browser Dutch voice fallback).
- Optional: user speech recordings / transcripts for correction.

**Recurring work.**

- Night-before ping for Mon/Tue/Thu 21:00 blocks; if a night is missed, fold the missed block into the next slot (planner rule 5).
- After each session: log listening/reading/writing/speaking/chapter part/minutes into `dutch-b1-log.md`.
- Writing: “Corrigeer dit B1-Nederlands en leg 3 fouten uit.”
- Speaking: shadow → monologue → role-play both sides; keep a 50-chunk phrase bank toward the 22 Oct checkpoint.
- Buffer week (14–22 Oct): run the mock B1 day from the planner.

**Create this week.** Yes.

---

### 3. Personal Trainer — INCLUDE

**Why it belongs.** First written goal in `profile/goals.md`. `health/body-composition.md` (InBody 14 Jul 2026: 50.5 kg, SMM 20.6 kg low-normal, PBF 26% high-normal, 156 cm, age 32). Strategy: strength to preserve/build muscle in a deficit; priority core/back/glutes. `health/workout-routine.md`: beginner, commercial gym, 4-day InBody-optimized split with starting weights. `health/hevy-integration.md`: four Hevy routine IDs, `HEVY_API_KEY`, `python data/sync-hevy.py`. `health/gym-log.md` last synced 20 Jul (two workouts + a 16 Jul Pilates class). `health/progression-map.md`: training milestones by month (hip thrust, RDL, deadlift, squat, plank) and InBody calendar through 1 Dec 2026. `data/progression.json` still has `"checkins": []` — the Aug/Sep weigh-ins were not written back.

**Connectors / tools.**

- Hevy API (`https://api.hevyapp.com`, key in local `.env` — gitignored).
- Vault: `health/workout-routine.md`, `health/gym-log.md`, `health/hevy-integration.md`, `health/progression-map.md`, `health/hevy-workouts.json` (local only).
- InBody numbers also land via Telegram `/inbody` → `data/progression.json` + `health/body-composition.md` (Nutrition/Telegram owns capture; Trainer owns interpretation).

**Recurring work.**

- After gym: sync Hevy → `gym-log.md`; flag skipped days vs Mon/Tue/Thu/Fri (or flexible Tue/Wed/Fri/Sat) split.
- Progression: +2.5 kg when top of rep range is hit on all sets; hip thrust is #1.
- Form cues for beginner hip thrust / RDL / deadlift / squat (Month 1 checklist still open).
- Every 4–6 weeks: compare InBody SMM (must hold ≥20.6, goal ≥21.0) vs PBF drop; do not cut calories further if SMM is falling.
- Weigh-in / scan calendar from `progression-map.md` (next named dates in the file: 6 Oct InBody #3, then Nov/Dec).

**Create this week.** Yes.

---

### 4. Nutrition Coach — INCLUDE as sibling to trainer, not as “accountant”

**Why it belongs.** Same 45 kg goal; the vault says fat loss comes from nutrition, training only protects muscle (`health/body-composition.md`, `health/nutrition.md`). Daily targets are encoded in three places: `health/nutrition.md`, `health/progression-map.md`, `data/diet-log.json` (`daily_targets`: 1400 / 95 P / 140 C / 45 F / 2000 ml). Logging product already exists: `telegram-bot/` (text, photo/label vision, `/today`, `/week`, `/water`, `/undo`, `/inbody`). Food data: `data/food-db.json` (DekaMarkt, NL+EN keywords). Journal 14–16 Jul shows protein chronically under target (69 g, 37 g, 46 g). Diet log trails off into incomplete days (17–23 Jul). Rules: protein first, never below 1,200 kcal, carbs around training, weekend treats OK if weekly average holds.

**Connectors / tools.**

- Telegram bot (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_ID`); Gemini or OpenAI vision for meal/label photos.
- `data/diet-log.json`, `data/food-db.json`, `python data/gen-food-db-ts.py` (canvas food matcher).
- Cursor “goal progression canvas” mentioned in `health/nutrition.md` / `data/README.md` (not in this git tree — treat as a user-side UI).

**Recurring work.**

- Daily: confirm log vs 95 g protein / 1,400 kcal; suggest the next meal if protein is short (this is the actual failure mode in the journal).
- Add missing DekaMarkt items to `food-db.json` when the user names a product.
- Weekly average vs deficit (~0.4 kg/week, 3–5 months, 45 kg by Dec).
- Training-day carb timing (coordinate with Trainer, do not change the Hevy program).

**Create this week if capacity; otherwise merge into Personal Trainer as Body Coach.** Do not skip nutrition entirely — the scale goal cannot be hit on training notes alone.

---

### 5. AP Ops Copilot — this is the accountant the repo is designed for

**Why it belongs.** `career/` is the largest operational system in the vault. Human roles are already named in `career/supplier-dashboard-process.md`:

| Human role | Owns |
|---|---|
| AP clerk | Aging, exceptions, chasing missing invoices, mandate completeness |
| AP lead | Weekly pack, 7-day reminders, 15-day escalations |
| Retail / PO owner | Confirm missing invoices, approve POs |
| Retail Finance | Month-end accrual, Flash Category spend |
| Treasury | Mandate scheme, Core vs B2B, DD exposure |

The user is building the operating file those roles live in: `career/build_dashboard.py` → `supplier_dashboard.xlsx` from Aurora AP log + GL listing + vendor master; user guide `career/supplier-dashboard-guide.md`; design `career/supplier-dashboard-plan.md`. Adjacent tools: `career/invoice_extractor/` (DocStore LREF PDFs, French invoices, German rent OCR), `career/improve_budget_tracker.py` (Ruzana’s DTC Retail 2026 Budget Tracker PO↔GL), Adyen daily Payment Accounting Report downloader documented in `career/README.md`. Work identity in paths: `C:\Users\shjiang\OneDrive - New Balance Athletics, Inc\Documents\Invoice`, company `NF` (France Retail), EMEA DTC Direct Debit Process (reminder 7 days, escalate 15 days later).

This is **work accounting / AP control**, not a career mentor and not a personal bookkeeper.

**Connectors / tools.**

- Local Excel/WPS + Aurora extracts (`AP_LG_NF*.CSV`, GL+vendor xlsx) — gitignored; never commit live supplier data (`.gitignore`).
- `python career/build_dashboard.py`, `career/aurora_extracts.py`.
- DocStore: `http://bosuka1.newbalance.com:6400` (or `bosuka1:6400`) via Selenium + basic/form auth (`career/config.example.env`). **Internal NB network — a cloud agent cannot log in.** Use this teammate on the work laptop, or have it interpret extracts the user already exported.
- Invoice PDFs on OneDrive; PaddleOCR/RapidOCR for scans.
- Adyen Customer Area Report user (HTTP basic, `ADYEN_*` in `career/.env`) — documented, module not in tree yet.
- WPS-safe Excel formulas only (no dynamic arrays) — see `career/README.md`.

**Recurring work.**

- **Monday AM:** rebuild/paste extracts; do not chase on Friday’s file. Split Track A (aging of invoices you *have*) vs Track B (receipt of invoices you *should have*).
- Payment run vs blocked (90+, no PO, not in vendor master). Exception queue largest-amount-first.
- DD_Monitor: Frequency not set → No invoice activity → Escalate → Reminder due.
- **Wednesday COP, week 3 of close:** chase follow-up.
- **Last working day:** book K12 accrual from DD_Monitor; rent/contracted cost from the contract sheet, not K12 average (`supplier-dashboard-process.md`).
- **First week of quarter:** Core vs B2B mandate completeness.
- Keep chase log *outside* formula columns (owner + last-chased still listed as “not in the workbook yet”).

**Create this week?** Only if a work Monday is landing this week and you already have Vault Keeper + Dutch + Trainer. Otherwise Phase 2 — the process docs are complete enough to stand up quickly.

---

### 6. Weekly Reviewer

**Why it belongs.** Two dated programs (body and Dutch) plus a Monday AP cadence, but the journal stops at 17 Jul 2026 and `data/progression.json` has no check-ins. `brain.mdc` already wants compact daily logs; `vault-config.md` lists `data/reminders.json` which is **not in the repo**. Someone has to notice silence.

**Connectors / tools.** Read-only across `journal/`, `health/gym-log.md`, `data/diet-log.json`, `data/progression.json`, `learning/dutch-b1-log.md`, `career/` gitignored outputs if present. Optional: create `data/reminders.json` in the schema from `vault-config.md`.

**Recurring work.**

- Once a week: gym sessions completed (target 4), protein days ≥95 g (target 5+/week from progression-map Month 1), Dutch nights (3), next InBody/weigh-in date, AP Monday pack done or not.
- Prompt Vault Keeper to write a short journal bullet if the user did the work but nothing was filed.
- Do not nag empty hobbies/life-admin.

**Phase 2.** After the three Phase 1 specialists exist, otherwise this agent has nobody to review.

---

### 7. Life Admin — implied, not ready

**Why it is implied.** Folder exists: `life-admin/README.md` — “Housing, finances, practical stuff.” `vault-config.md` same. Dutch planner week 9 prompt is “Justify a real choice (housing, job, weekend plan).” Food-db and Telegram copy are NL (DekaMarkt). Living/working context is Netherlands + NB EMEA.

**Why not now.** The folder has no leases, gemeente, belasting, insurance, or household budget. Creating this agent would be fiction.

**When to create.** After the user dumps even a short `life-admin/housing.md` or `life-admin/finances.md`. Then this agent owns reminders, renewals, and NL paperwork — still not a full personal accountant unless bank/tax files appear.

---

## Explicitly rejected or deferred

### Personal accountant — reject as a Phase 1/2 teammate

- **Personal money:** `life-admin/` empty. No income, rent, tax year, or bank exports.
- **Work money:** already covered by AP Ops Copilot. That agent should be named for AP/Retail Finance, not “Accountant,” so it does not get asked to do household tax.
- Revisit as **Personal Accountant** in Phase 3 only if `life-admin/` grows real finance artifacts (jaaropgave, huur, insurance). Until then, Life Admin is the right thinner role.

### Career mentor — reject until the user writes a career

- `career/` contains supplier dashboard, invoice extractor, budget tracker, Adyen docs — a job toolkit, not a development plan.
- `profile/goals.md` has no career goal.
- Journals have no Work/career section at all (only health).
- Colleague “Ruzana” appears as owner of a tracker workbook, not as a mentoring relationship.
- When ready: user writes `career/career-goals.md` (role, skills, NB DTC path). Then a mentor can use AP Ops output as *evidence of work*, not as the curriculum.

### Do not create

| Tempting agent | Reason |
|---|---|
| Hobbies / creative director | `hobbies/README.md` only. |
| Dating / emotional coach | Journal template lists “social, dating, emotional state”; no entries. |
| Separate Invoice OCR bot | Fold into AP Ops; `invoice_extractor` is a tool, not a teammate. |
| Separate Adyen downloader bot | Same — a command in `career/README.md`. |
| Separate Hevy sync bot | Tool for the Trainer (`data/sync-hevy.py`). |
| Values / philosopher | `profile/README.md` says “values”; no values file exists. |

---

## What already exists (do not rebuild)

| Thing | Path | Treat as |
|---|---|---|
| Generalist vault assistant | `.cursor/rules/brain.mdc` | Promote to Vault Keeper teammate |
| Vault map | `vault-config.md` | Onboarding for every new agent |
| Telegram diet + InBody logger | `telegram-bot/` | Connector for Nutrition (and InBody capture) |
| Dutch tutor prompt | `learning/transcript_ai.py` | Seed prompt for Dutch Tutor |
| Hevy sync | `data/sync-hevy.py` | Connector for Trainer |
| AP operating system | `career/supplier-dashboard-*.md` + `build_dashboard.py` | Seed prompt + SOPs for AP Ops |
| Invoice pipeline | `career/invoice_extractor/` | Tool under AP Ops |
| GitHub Pages B1 site | `docs/index.html`, `docs/dutch-b1-*.html` | User practice UI; Dutch Tutor should know it, not redesign it |

---

## Phased plan

### Phase 1 — create this week

Stand up **three** teammates (four if you split body work). Goal: cover the two lines in `profile/goals.md` plus the vault protocol that already runs.

1. **Vault Keeper** — copy `.cursor/rules/brain.mdc` + `vault-config.md` into the teammate brief. Job is routing and git hygiene, not expertise.
2. **Dutch Tutor** — seed from `learning/dutch-b1-planner.md`, `learning/dutch-b1-log.md`, and the tutor prompt in `learning/transcript_ai.py`. First task: honest catch-up vs the 15 Sep / 22 Oct checkpoints; do not pretend chapters are done.
3. **Personal Trainer** — seed from `health/workout-routine.md`, `health/hevy-integration.md`, `health/progression-map.md`, `health/body-composition.md`. First task: sync or ask for Hevy since 20 Jul; compare to the Month 2–3 lift milestones (we are past 14 Sep in the map).

**Same week if you have a fourth slot:** **Nutrition Coach** (Telegram + `data/diet-log.json` + protein-first rule). If not, give the Trainer the diet-log read and the 95 g target until Nutrition is split out.

Do **not** create accountant or career mentor this week.

### Phase 2 — next

4. **AP Ops Copilot** — seed from `career/supplier-dashboard-process.md` (operating cadence), `career/supplier-dashboard-guide.md` (what to type), `career/README.md` (commands). Run it where DocStore/Aurora are reachable (work laptop), or as a “read the extracts I pasted” cloud agent. First Monday: Track A vs Track B pack; do not mix overdue invoices with missing DD invoices.
5. **Nutrition Coach** if still merged into Trainer.
6. **Weekly Reviewer** — once 1–4 are logging, add the scoreboard and optionally `data/reminders.json`.

### Phase 3 — only after the user writes source material

7. **Life Admin** — when `life-admin/` has housing or practical notes.
8. **Personal Accountant** — when household finance files exist (still separate from AP Ops).
9. **Career Mentor** — when `career/career-goals.md` (or equivalent) exists: skills, direction, not invoice parsing.
10. **Hobbies** — when there is a project to keep.

---

## How to brief each new teammate (so they do not fight)

- Every specialist reads `vault-config.md` and `.cursor/rules/brain.mdc` first, then only its own folder plus `profile/goals.md`.
- Writes go to that folder’s files; Vault Keeper owns cross-folder journal lines and git.
- Never delete; merge; no live AP/supplier files in git.
- Cloud agents cannot use `bosuka1` DocStore, Hevy (needs local `.env`), or Telegram (needs a long-running process). Those stay local connectors; the teammate reasons over vault files the connectors already wrote.

---

## Repo map (what was read)

| Area | What is actually there |
|---|---|
| `profile/` | `about.md` (email only), `goals.md` (health + Dutch only) |
| `journal/` | 14–17 Jul 2026, health only |
| `health/` | Full training + nutrition OS + Hevy + InBody |
| `learning/` | Full Dutch B1 OS + practice site + tutor prompt |
| `career/` | AP dashboard + invoice extractor + budget tracker + Adyen docs |
| `life-admin/` | README stub |
| `hobbies/` | README stub |
| `data/` | `diet-log.json`, `food-db.json`, `progression.json` (no check-ins); `reminders.json` named but missing |
| `telegram-bot/` | Diet + InBody phone logger |
| `docs/` | GitHub Pages Dutch site (this plan is a new file beside it) |
| `.cursor/rules/brain.mdc` | Only Cursor rule; no other agent/persona/skill files |

**Section:** docs
