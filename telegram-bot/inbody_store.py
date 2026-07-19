"""Write InBody check-ins to progression.json and body-composition.md."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Amsterdam")


def today_str() -> str:
    return datetime.now(TZ).date().isoformat()


class InBodyStore:
    def __init__(self, progression_path: Path, body_comp_md: Path):
        self.progression_path = progression_path
        self.body_comp_md = body_comp_md

    def _load_progression(self) -> dict[str, Any]:
        return json.loads(self.progression_path.read_text(encoding="utf-8"))

    def _save_progression(self, data: dict[str, Any]) -> None:
        self.progression_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def add_checkin(
        self,
        weight_kg: float,
        smm_kg: float | None = None,
        pbf_percent: float | None = None,
        ecw_ratio: float | None = None,
        day: str | None = None,
        label: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        day = day or today_str()
        data = self._load_progression()
        checkins: list[dict[str, Any]] = data.setdefault("checkins", [])

        # Replace same-day inbody if present
        checkins = [c for c in checkins if not (c.get("date") == day and c.get("type") == "inbody")]
        entry: dict[str, Any] = {
            "date": day,
            "type": "inbody",
            "weight_kg": weight_kg,
            "label": label or f"InBody {day}",
        }
        if smm_kg is not None:
            entry["smm_kg"] = smm_kg
        if pbf_percent is not None:
            entry["pbf_percent"] = pbf_percent
        if ecw_ratio is not None:
            entry["ecw_ratio"] = ecw_ratio
        if notes:
            entry["notes"] = notes

        checkins.append(entry)
        checkins.sort(key=lambda c: c["date"])
        data["checkins"] = checkins
        self._save_progression(data)
        self._append_markdown(entry)
        return entry

    def _append_markdown(self, entry: dict[str, Any]) -> None:
        if not self.body_comp_md.exists():
            return
        text = self.body_comp_md.read_text(encoding="utf-8")
        # Avoid duplicating same-date section
        heading = f"## InBody — {entry['date']}"
        if heading in text:
            # Replace existing section until next ## or footer
            pattern = re.compile(
                rf"{re.escape(heading)}.*?(?=\n## |\n\*\*See also:|\Z)",
                re.DOTALL,
            )
            text = pattern.sub(self._section_body(entry) + "\n\n", text)
        else:
            # Insert before See also / Section footer
            section = self._section_body(entry) + "\n\n"
            marker = "**See also:**"
            if marker in text:
                text = text.replace(marker, section + marker, 1)
            else:
                text = text.rstrip() + "\n\n" + section

        self.body_comp_md.write_text(text, encoding="utf-8")

    def _section_body(self, entry: dict[str, Any]) -> str:
        rows = [
            f"| Weight | {entry['weight_kg']} kg | — |",
        ]
        if "smm_kg" in entry:
            rows.append(f"| SMM (skeletal muscle mass) | {entry['smm_kg']} kg | — |")
        if "pbf_percent" in entry:
            rows.append(f"| PBF (body fat %) | {entry['pbf_percent']}% | — |")
        if "ecw_ratio" in entry:
            rows.append(f"| ECW Ratio | {entry['ecw_ratio']} | — |")

        lines = [
            f"## InBody — {entry['date']}",
            "",
            "| Metric | Value | Status |",
            "|---|---|---|",
            *rows,
        ]
        if entry.get("notes"):
            lines.extend(["", entry["notes"]])
        return "\n".join(lines)

    def latest(self) -> dict[str, Any] | None:
        data = self._load_progression()
        checkins = [c for c in data.get("checkins", []) if c.get("type") == "inbody"]
        if checkins:
            return checkins[-1]
        baseline = data.get("baseline")
        if baseline:
            return {**baseline, "type": "inbody", "label": "Baseline"}
        return None


def parse_inbody_quick(text: str) -> dict[str, float]:
    """Parse loose text like: 49.2kg smm 20.8 pbf 25.1 ecw 0.365"""
    t = text.lower().replace(",", ".")
    out: dict[str, float] = {}

    def grab(patterns: list[str]) -> float | None:
        for p in patterns:
            m = re.search(p, t)
            if m:
                return float(m.group(1))
        return None

    weight = grab(
        [
            r"(\d+(?:\.\d+)?)\s*kg",
            r"weight\s*[:=]?\s*(\d+(?:\.\d+)?)",
            r"gewicht\s*[:=]?\s*(\d+(?:\.\d+)?)",
        ]
    )
    smm = grab(
        [
            r"smm\s*[:=]?\s*(\d+(?:\.\d+)?)",
            r"muscle\s*[:=]?\s*(\d+(?:\.\d+)?)",
        ]
    )
    pbf = grab(
        [
            r"pbf\s*[:=]?\s*(\d+(?:\.\d+)?)",
            r"fat\s*%?\s*[:=]?\s*(\d+(?:\.\d+)?)",
            r"vet\s*%?\s*[:=]?\s*(\d+(?:\.\d+)?)",
        ]
    )
    ecw = grab(
        [
            r"ecw\s*(?:ratio)?\s*[:=]?\s*(\d+(?:\.\d+)?)",
        ]
    )
    if weight is not None:
        out["weight_kg"] = weight
    if smm is not None:
        out["smm_kg"] = smm
    if pbf is not None:
        out["pbf_percent"] = pbf
    if ecw is not None:
        out["ecw_ratio"] = ecw
    return out
