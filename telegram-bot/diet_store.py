"""Read/write data/diet-log.json."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")


def today_str() -> str:
    return datetime.now(TZ).date().isoformat()


class DietStore:
    def __init__(self, path: Path):
        self.path = path

    def _load(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def targets(self) -> dict[str, Any]:
        return self._load()["daily_targets"]

    def get_entry(self, day: str | None = None) -> dict[str, Any] | None:
        day = day or today_str()
        for entry in self._load()["entries"]:
            if entry["date"] == day:
                return entry
        return None

    def _ensure_entry(self, data: dict[str, Any], day: str) -> dict[str, Any]:
        for entry in data["entries"]:
            if entry["date"] == day:
                return entry
        entry = {
            "date": day,
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "water_ml": 0,
            "meals": [],
            "notes": "",
        }
        data["entries"].append(entry)
        data["entries"].sort(key=lambda e: e["date"])
        return entry

    def add_meal(
        self,
        meal_label: str,
        calories: float,
        protein: float,
        carbs: float,
        fat: float,
        water_ml: float = 0,
        day: str | None = None,
    ) -> dict[str, Any]:
        day = day or today_str()
        data = self._load()
        entry = self._ensure_entry(data, day)
        entry["meals"].append(meal_label)
        entry["calories"] = round(float(entry.get("calories") or 0) + calories)
        entry["protein_g"] = round(float(entry.get("protein_g") or 0) + protein)
        entry["carbs_g"] = round(float(entry.get("carbs_g") or 0) + carbs)
        entry["fat_g"] = round(float(entry.get("fat_g") or 0) + fat)
        current_water = entry.get("water_ml")
        if current_water is None:
            current_water = 0
        entry["water_ml"] = round(float(current_water) + water_ml)
        self._save(data)
        return entry

    def add_water(self, ml: float, day: str | None = None) -> dict[str, Any]:
        day = day or today_str()
        data = self._load()
        entry = self._ensure_entry(data, day)
        current = entry.get("water_ml") or 0
        entry["water_ml"] = round(float(current) + ml)
        self._save(data)
        return entry

    def undo_last_meal(self, day: str | None = None) -> tuple[str | None, dict[str, Any] | None]:
        """Remove last meal string only (macros stay — use /recalc or note).

        For simplicity we store meal lines with embedded macros in notes isn't ideal.
        Better approach: undo removes last meal and we can't perfectly reverse macros
        unless we parse. So we only support undo when the last meal was just added
        in-session, OR we recompute from food matcher if possible.

        Practical approach: keep last_undo stack in a sidecar? Simpler: store
        structured meal_details optionally. For v1, undo removes last meal label
        and subtracts if we can re-parse it.
        """
        day = day or today_str()
        data = self._load()
        entry = None
        for e in data["entries"]:
            if e["date"] == day:
                entry = e
                break
        if not entry or not entry.get("meals"):
            return None, entry
        removed = entry["meals"].pop()
        self._save(data)
        return removed, entry

    def subtract_macros(
        self,
        calories: float,
        protein: float,
        carbs: float,
        fat: float,
        water_ml: float = 0,
        day: str | None = None,
    ) -> dict[str, Any]:
        day = day or today_str()
        data = self._load()
        entry = self._ensure_entry(data, day)
        entry["calories"] = max(0, round(float(entry.get("calories") or 0) - calories))
        entry["protein_g"] = max(0, round(float(entry.get("protein_g") or 0) - protein))
        entry["carbs_g"] = max(0, round(float(entry.get("carbs_g") or 0) - carbs))
        entry["fat_g"] = max(0, round(float(entry.get("fat_g") or 0) - fat))
        current_water = entry.get("water_ml") or 0
        entry["water_ml"] = max(0, round(float(current_water) - water_ml))
        self._save(data)
        return entry

    def set_note(self, note: str, day: str | None = None) -> dict[str, Any]:
        day = day or today_str()
        data = self._load()
        entry = self._ensure_entry(data, day)
        entry["notes"] = note
        self._save(data)
        return entry

    def recent_days(self, n: int = 7) -> list[dict[str, Any]]:
        entries = sorted(self._load()["entries"], key=lambda e: e["date"], reverse=True)
        return entries[:n]


def format_day(entry: dict[str, Any] | None, targets: dict[str, Any], day: str | None = None) -> str:
    day = day or (entry["date"] if entry else today_str())
    if not entry:
        return (
            f"📅 {day} — nothing logged yet\n\n"
            f"Targets: {targets['calories']} kcal · "
            f"{targets['protein_g']}g P · {targets['carbs_g']}g C · "
            f"{targets['fat_g']}g F · {targets['water_ml']} ml"
        )

    def bar(cur: float, tgt: float) -> str:
        if not tgt:
            return ""
        pct = min(100, int(round(100 * cur / tgt)))
        return f"{pct}%"

    cals = float(entry.get("calories") or 0)
    protein = float(entry.get("protein_g") or 0)
    carbs = float(entry.get("carbs_g") or 0)
    fat = float(entry.get("fat_g") or 0)
    water = float(entry.get("water_ml") or 0)

    lines = [
        f"📅 {day}",
        f"🔥 {cals:.0f}/{targets['calories']} kcal ({bar(cals, targets['calories'])})",
        f"💪 {protein:.0f}/{targets['protein_g']}g protein ({bar(protein, targets['protein_g'])})",
        f"🍞 {carbs:.0f}/{targets['carbs_g']}g carbs ({bar(carbs, targets['carbs_g'])})",
        f"🥑 {fat:.0f}/{targets['fat_g']}g fat ({bar(fat, targets['fat_g'])})",
        f"💧 {water:.0f}/{targets['water_ml']} ml ({bar(water, targets['water_ml'])})",
    ]
    meals = entry.get("meals") or []
    if meals:
        lines.append("")
        lines.append("Meals:")
        for i, m in enumerate(meals, 1):
            lines.append(f"  {i}. {m}")
    if entry.get("notes"):
        lines.append("")
        lines.append(f"Note: {entry['notes']}")
    return "\n".join(lines)
