"""Fetch Hevy workouts/routines into local health/hevy-*.json and print a summary."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API = "https://api.hevyapp.com"
KEY = os.getenv("HEVY_API_KEY", "").strip()
HEADERS = {"api-key": KEY, "Accept": "application/json"}
TODAY = datetime.now().date().isoformat()


def get_all(path: str, key_name: str, page_size: int = 10) -> list:
    items: list = []
    page = 1
    while True:
        r = httpx.get(
            f"{API}{path}",
            params={"page": page, "pageSize": page_size},
            headers=HEADERS,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        batch = data.get(key_name) or []
        items.extend(batch)
        page_count = data.get("page_count") or 1
        print(f"{path} page {page}/{page_count} (+{len(batch)})")
        if page >= page_count or not batch:
            break
        page += 1
    return items


def fmt_sets(sets: list) -> str:
    parts = []
    for s in sets or []:
        if s.get("deleted") or s.get("type") == "warmup":
            continue
        wt = s.get("weight_kg")
        reps = s.get("reps")
        dur = s.get("duration_seconds")
        dist = s.get("distance_meters")
        if dur:
            parts.append(f"{dur}s")
        elif wt is not None and reps is not None:
            parts.append(f"{wt:g} kg × {reps}")
        elif reps is not None:
            parts.append(f"{reps} reps")
        elif dist is not None:
            parts.append(f"{dist} m")
    return " · ".join(parts)


def workout_md(w: dict) -> str:
    start = (w.get("start_time") or "")[:10]
    title = w.get("title") or "Workout"
    lines = [f"## {start} — {title}", ""]
    notes = (w.get("description") or "").strip()
    if notes:
        lines.append(notes)
        lines.append("")
    lines.extend(["| Exercise | Sets |", "|---|---|"])
    for ex in w.get("exercises") or []:
        summary = fmt_sets(ex.get("sets") or [])
        if not summary:
            continue
        lines.append(f"| {ex.get('title')} | {summary} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not KEY:
        raise SystemExit("Missing HEVY_API_KEY in .env")

    workouts = get_all("/v1/workouts", "workouts")
    routines = get_all("/v1/routines", "routines")
    try:
        measurements = get_all("/v1/body_measurements", "body_measurements")
    except Exception as e:
        print("measurements skip:", e)
        measurements = []

    count = httpx.get(f"{API}/v1/workouts/count", headers=HEADERS, timeout=30).json()
    out = ROOT / "health"
    (out / "hevy-workouts.json").write_text(
        json.dumps(
            {"fetched_at": TODAY, "count": count, "workouts": workouts},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "hevy-routines.json").write_text(
        json.dumps({"fetched_at": TODAY, "routines": routines}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    if measurements:
        (out / "hevy-measurements.json").write_text(
            json.dumps(
                {"fetched_at": TODAY, "body_measurements": measurements},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"\nSaved {len(workouts)} workouts, {len(routines)} routines")
    print("count:", count)

    # Build gym-log from Hevy (keep intro + see also)
    sections = []
    for w in sorted(workouts, key=lambda x: x.get("start_time") or "", reverse=True):
        sections.append(workout_md(w))
        print("---")
        print((w.get("start_time") or "")[:19], w.get("title"))
        for ex in w.get("exercises") or []:
            s = fmt_sets(ex.get("sets") or [])
            if s:
                print(f"  {ex.get('title')}: {s}")

    gym_log = (
        "# Gym Log\n\n"
        f"_Synced from Hevy on {TODAY}. Raw JSON: `health/hevy-workouts.json` (local only)._\n\n"
        + "\n".join(sections)
        + "**See also:** [[workout-routine]], [[body-composition]], [[hevy-integration]]\n\n"
        "**Section:** [[health]]\n"
    )
    (out / "gym-log.md").write_text(gym_log, encoding="utf-8")
    print("\nUpdated health/gym-log.md")


if __name__ == "__main__":
    main()
