"""Match free-text meal descriptions against data/food-db.json."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

PREP_WORDS = {
    "gestoomde",
    "gestoomd",
    "gekookte",
    "gekookt",
    "gebakken",
    "gegrilde",
    "gegrild",
    "grilled",
    "steamed",
    "boiled",
    "baked",
    "fried",
    "roasted",
    "raw",
    "verse",
    "vers",
    "kleine",
    "klein",
    "grote",
    "groot",
    "small",
    "large",
    "fresh",
    "cooked",
}

# Split meal text into item chunks
SPLIT_RE = re.compile(r"\s*(?:\+|,(?!\d)|;\s*|\n)+\s*")
# amount patterns: 200g, 200 g, 250ml, 2x, ×2, 2×
AMOUNT_RE = re.compile(
    r"(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>g|gram|grams|ml|milliliter|milliliters)?\b"
    r"|[x×]\s*(?P<mult>\d+(?:[.,]\d+)?)"
    r"|(?P<mult2>\d+(?:[.,]\d+)?)\s*[x×]",
    re.IGNORECASE,
)


@dataclass
class MatchedItem:
    name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    water_ml: float = 0.0
    matched_keyword: str = ""


@dataclass
class MealParseResult:
    items: list[MatchedItem]
    unmatched: list[str]
    meal_label: str
    calories: float
    protein: float
    carbs: float
    fat: float
    water_ml: float


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = text.replace("ë", "e").replace("é", "e").replace("ö", "o").replace("ü", "u")
    return text


def load_food_db(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    foods = data["foods"]
    # Prefer longer keywords first for matching
    for food in foods:
        food["_keywords_sorted"] = sorted(
            (_norm(k) for k in food["keywords"]), key=len, reverse=True
        )
    return foods


def _strip_prep(text: str) -> str:
    words = text.split()
    kept = [w for w in words if _norm(w.rstrip(".,")) not in PREP_WORDS]
    return " ".join(kept).strip() or text


def _extract_amount(text: str) -> tuple[str, float | None, str | None]:
    """Return (cleaned_name, amount, unit). unit is 'g', 'ml', or 'x'."""
    amount = None
    unit = None
    cleaned = text

    for match in AMOUNT_RE.finditer(text):
        if match.group("qty") is not None:
            amount = float(match.group("qty").replace(",", "."))
            unit = (match.group("unit") or "g").lower()
            if unit.startswith("gram"):
                unit = "g"
            if unit.startswith("milliliter"):
                unit = "ml"
        elif match.group("mult") is not None:
            amount = float(match.group("mult").replace(",", "."))
            unit = "x"
        elif match.group("mult2") is not None:
            amount = float(match.group("mult2").replace(",", "."))
            unit = "x"
        cleaned = (text[: match.start()] + " " + text[match.end() :]).strip()
        break  # first amount wins

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")
    return cleaned, amount, unit


def _find_food(name: str, foods: list[dict]) -> tuple[dict | None, str]:
    needle = _norm(_strip_prep(name))
    if not needle:
        return None, ""

    best = None
    best_kw = ""
    best_score = -1

    for food in foods:
        for kw in food["_keywords_sorted"]:
            score = -1
            if needle == kw:
                score = 1000 + len(kw)
            else:
                # Whole-word / phrase containment only (avoid "ei" ∈ "eiwitpoeder")
                pattern = r"(?:^|\s)" + re.escape(kw) + r"(?:$|\s)"
                if re.search(pattern, f" {needle} "):
                    score = 500 + len(kw)
                elif re.search(pattern, f" {kw} ") and needle in kw.split():
                    score = 100 + len(needle)
            if score > best_score:
                best = food
                best_kw = kw
                best_score = score

    return best, best_kw


def parse_meal(text: str, foods: list[dict]) -> MealParseResult:
    chunks = [c.strip() for c in SPLIT_RE.split(text) if c.strip()]
    if not chunks:
        chunks = [text.strip()]

    items: list[MatchedItem] = []
    unmatched: list[str] = []

    for chunk in chunks:
        name_part, amount, unit = _extract_amount(chunk)
        name_part = _strip_prep(name_part)
        food, kw = _find_food(name_part or chunk, foods)
        if not food:
            unmatched.append(chunk)
            continue

        base = float(food.get("baseGrams", 100) or 100)
        if unit == "x" and amount is not None:
            grams = amount * base
        elif unit == "ml" and amount is not None:
            grams = amount  # treat ml ≈ g for liquids in this db
        elif amount is not None:
            grams = amount
        else:
            grams = base

        scale = grams / base
        water = 0.0
        if "waterMl" in food:
            water = float(food["waterMl"]) * (grams / base)

        items.append(
            MatchedItem(
                name=name_part or kw,
                grams=round(grams, 1),
                calories=round(food["calories"] * scale, 1),
                protein=round(food["protein"] * scale, 1),
                carbs=round(food["carbs"] * scale, 1),
                fat=round(food["fat"] * scale, 1),
                water_ml=round(water, 1),
                matched_keyword=kw,
            )
        )

    label_parts = [f"{i.name} {i.grams:g}g" for i in items]
    if unmatched:
        label_parts.extend(unmatched)

    return MealParseResult(
        items=items,
        unmatched=unmatched,
        meal_label=", ".join(label_parts) if label_parts else text.strip(),
        calories=round(sum(i.calories for i in items), 1),
        protein=round(sum(i.protein for i in items), 1),
        carbs=round(sum(i.carbs for i in items), 1),
        fat=round(sum(i.fat for i in items), 1),
        water_ml=round(sum(i.water_ml for i in items), 1),
    )
