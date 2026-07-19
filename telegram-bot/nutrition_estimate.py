"""Estimate meal nutrition from free-form text or photos.

Priority:
1. Match items against data/food-db.json (accurate)
2. If OPENAI_API_KEY is set — AI estimate for leftovers / free-form / photos
3. Otherwise — local heuristic estimate so something always gets logged
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass

import httpx

from food_matcher import MealParseResult, MatchedItem, load_food_db, parse_meal

log = logging.getLogger("brain-bot.estimate")

CONVO_PREFIX = re.compile(
    r"^(?:i\s+(?:just\s+)?(?:ate|had|eaten)|ik\s+(?:heb\s+)?(?:gegeten|gehad)|"
    r"(?:for\s+)?(?:breakfast|lunch|dinner|snack|ontbijt|lunch|avondeten|tussendoortje)\s*(?:was|:)?|"
    r"today\s+i\s+(?:ate|had)|vandaag\s+(?:at|gegeten)|"
    r"ate|had|gegeten)\s+",
    re.IGNORECASE,
)

# Typical per-100g macros when food-db misses (rough EU averages)
CATEGORY_PER_100G = [
    (["pizza", "burger", "friet", "fries", "kebab", "shoarma", "patat"],
     {"calories": 260, "protein": 12, "carbs": 28, "fat": 12, "portion": 200}),
    (["pasta", "noodle", "noodles", "spaghetti", "macaroni"],
     {"calories": 140, "protein": 5, "carbs": 25, "fat": 2, "portion": 250}),
    (["rijst", "rice", "nasi", "bami"],
     {"calories": 130, "protein": 3, "carbs": 28, "fat": 0.5, "portion": 200}),
    (["brood", "bread", "toast", "sandwich", "boterham", "wrap"],
     {"calories": 250, "protein": 10, "carbs": 35, "fat": 7, "portion": 150}),
    (["kip", "chicken", "vlees", "meat", "beef", "gehakt", "vis", "fish", "zalm", "tonijn"],
     {"calories": 160, "protein": 25, "carbs": 0, "fat": 6, "portion": 120}),
    (["ei", "egg", "omelet", "omelette"],
     {"calories": 140, "protein": 12, "carbs": 1, "fat": 10, "portion": 100}),
    (["yoghurt", "yogurt", "kwark", "skyr", "quark"],
     {"calories": 70, "protein": 10, "carbs": 5, "fat": 1, "portion": 150}),
    (["kaas", "cheese"],
     {"calories": 350, "protein": 25, "carbs": 0, "fat": 28, "portion": 30}),
    (["groente", "veg", "salade", "salad", "broccoli", "soep", "soup"],
     {"calories": 40, "protein": 2, "carbs": 6, "fat": 1, "portion": 200}),
    (["fruit", "meloen", "apple", "banaan", "banana", "bes", "berry"],
     {"calories": 50, "protein": 0.5, "carbs": 12, "fat": 0.2, "portion": 150}),
    (["chocolade", "koek", "cookie", "cake", "taart", "ijs", "ice cream", "snoep"],
     {"calories": 400, "protein": 5, "carbs": 50, "fat": 20, "portion": 40}),
    (["shake", "smoothie", "protein"],
     {"calories": 150, "protein": 20, "carbs": 10, "fat": 3, "portion": 300}),
    (["koffie", "coffee", "thee", "tea", "water"],
     {"calories": 5, "protein": 0, "carbs": 1, "fat": 0, "portion": 200}),
    (["olie", "oil", "boter", "butter", "dressing", "saus", "sauce"],
     {"calories": 500, "protein": 1, "carbs": 5, "fat": 50, "portion": 15}),
]

DEFAULT_UNKNOWN = {"calories": 180, "protein": 8, "carbs": 18, "fat": 7, "portion": 150}

AMOUNT_re = re.compile(r"(\d+(?:[.,]\d+)?)\s*(g|gram|grams|ml|stuk|stuks|x)?", re.I)


@dataclass
class EstimateResult:
    meal_label: str
    calories: float
    protein: float
    carbs: float
    fat: float
    water_ml: float
    source: str  # "food-db" | "mixed" | "ai" | "estimate"
    details: list[str]
    notes: str = ""


def _clean_description(text: str) -> str:
    t = text.strip()
    t = CONVO_PREFIX.sub("", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t or text.strip()


def _heuristic_item(chunk: str) -> MatchedItem:
    lower = chunk.lower()
    amount = None
    unit = None
    m = amount_re.search(chunk)
    if m:
        amount = float(m.group(1).replace(",", "."))
        unit = (m.group(2) or "g").lower()

    macros = DEFAULT_UNKNOWN
    for keys, vals in CATEGORY_PER_100G:
        if any(k in lower for k in keys):
            macros = vals
            break

    portion = float(macros["portion"])
    if amount is not None:
        if unit in ("x", "stuk", "stuks"):
            grams = amount * portion
        else:
            grams = amount
    else:
        grams = portion

    scale = grams / 100.0
    return MatchedItem(
        name=chunk.strip(),
        grams=round(grams, 1),
        calories=round(macros["calories"] * scale, 1),
        protein=round(macros["protein"] * scale, 1),
        carbs=round(macros["carbs"] * scale, 1),
        fat=round(macros["fat"] * scale, 1),
        matched_keyword="~estimate",
    )


def _from_parse(parsed: MealParseResult, source: str, extra_notes: str = "") -> EstimateResult:
    details = [
        f"{i.name} {i.grams:g}g → {i.calories:.0f} kcal / {i.protein:.0f}g P"
        + (" (est.)" if i.matched_keyword == "~estimate" else "")
        for i in parsed.items
    ]
    return EstimateResult(
        meal_label=parsed.meal_label,
        calories=parsed.calories,
        protein=parsed.protein,
        carbs=parsed.carbs,
        fat=parsed.fat,
        water_ml=parsed.water_ml,
        source=source,
        details=details,
        notes=extra_notes,
    )


def estimate_local(text: str, foods: list[dict]) -> EstimateResult:
    cleaned = _clean_description(text)
    # Prefer splitting on " and " / " en " for free-form
    soft = re.sub(r"\s+(?:and|en|&)\s+", " + ", cleaned, flags=re.I)
    parsed = parse_meal(soft, foods)

    items = list(parsed.items)
    for chunk in parsed.unmatched:
        items.append(_heuristic_item(chunk))

    if not items:
        items.append(_heuristic_item(cleaned or text))

    merged = MealParseResult(
        items=items,
        unmatched=[],
        meal_label=", ".join(
            f"{i.name} {i.grams:g}g" if i.matched_keyword != "~estimate" else f"~{i.name}"
            for i in items
        ),
        calories=round(sum(i.calories for i in items), 1),
        protein=round(sum(i.protein for i in items), 1),
        carbs=round(sum(i.carbs for i in items), 1),
        fat=round(sum(i.fat for i in items), 1),
        water_ml=round(sum(i.water_ml for i in items), 1),
    )
    used_est = any(i.matched_keyword == "~estimate" for i in items)
    used_db = any(i.matched_keyword != "~estimate" for i in items)
    if used_est and used_db:
        source = "mixed"
    elif used_est:
        source = "estimate"
    else:
        source = "food-db"
    return _from_parse(merged, source)


PHOTO_PROMPT = """Analyze this food photo for a diet log.

It may be:
A) A plated / prepared meal — identify foods and estimate edible portion sizes
B) A food package / supermarket product — read brand + product name
C) A nutrition label (voedingswaarden) — READ the numbers from the label

Rules for packages/labels (Dutch or English):
- Prefer values FROM THE LABEL over guessing
- Use "per portie / per serving" if amount eaten matches; otherwise scale from per 100g
- If caption says how much was eaten (e.g. "100g", "hele bak", "half"), use that
- If no amount given: use 1 serving from the label, or a realistic single portion
- Note pack size vs amount logged in "notes"

Return ONLY JSON with keys:
meal_label, calories, protein_g, carbs_g, fat_g, water_ml, items, notes, photo_type
photo_type must be one of: meal, package, label
items: short strings like "Magere kwark 150g — 92 kcal / 15g P"
"""


async def _estimate_openai(
    text: str | None,
    image_bytes: bytes | None,
    image_mime: str,
) -> EstimateResult | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    system = (
        "You estimate nutrition for a personal diet log (~1400 kcal/day, 95g protein). "
        "Return ONLY compact JSON with keys: "
        "meal_label, calories, protein_g, carbs_g, fat_g, water_ml, items, notes, photo_type. "
        "Dutch or English OK. For package/label photos, read printed voedingswaarden."
    )

    if image_bytes:
        prompt = (text.strip() + "\n\n" if text else "") + PHOTO_PROMPT
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        user_content: str | list = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64}"}},
        ]
    else:
        prompt = text or "Estimate nutrition."
        user_content = prompt

    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
        return _parse_ai_json(data["choices"][0]["message"]["content"], text)
    except Exception as e:
        log.warning("OpenAI estimate failed: %s", e)
        return None


async def _estimate_gemini(
    text: str | None,
    image_bytes: bytes | None,
    image_mime: str,
) -> EstimateResult | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip() or "gemini-3.1-flash-lite"
    fallbacks = [
        model,
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    ]
    models: list[str] = []
    for m in fallbacks:
        if m not in models:
            models.append(m)

    instruction = (
        "You estimate nutrition for a personal diet log (~1400 kcal/day, 95g protein). "
        "Return ONLY compact JSON (no markdown) with keys: "
        "meal_label, calories, protein_g, carbs_g, fat_g, water_ml, items, notes, photo_type. "
        "Dutch or English OK. For package/label photos, read printed voedingswaarden."
    )

    parts: list[dict] = []
    if image_bytes:
        prompt = (text.strip() + "\n\n" if text else "") + PHOTO_PROMPT
        parts.append({"text": instruction + "\n\n" + prompt})
        parts.append(
            {
                "inline_data": {
                    "mime_type": image_mime,
                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                }
            }
        )
    else:
        parts.append({"text": instruction + "\n\n" + (text or "Estimate nutrition.")})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=90.0) as client:
        for model_name in models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            try:
                r = await client.post(url, json=payload)
                if r.status_code in (429, 503, 404):
                    log.warning("Gemini %s -> %s, trying next", model_name, r.status_code)
                    continue
                r.raise_for_status()
                data = r.json()
                raw = data["candidates"][0]["content"]["parts"][0]["text"]
                return _parse_ai_json(raw, text)
            except Exception as e:
                last_err = e
                log.warning("Gemini %s failed: %s", model_name, e)
                continue
    if last_err:
        log.warning("All Gemini models failed: %s", last_err)
    return None


def _parse_ai_json(raw: str, fallback_text: str | None) -> EstimateResult:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    obj = json.loads(raw)
    label = str(obj.get("meal_label") or fallback_text or "meal photo").strip()
    items = obj.get("items") or []
    details = [str(x) for x in items] if isinstance(items, list) else []
    photo_type = str(obj.get("photo_type") or "").strip()
    notes = str(obj.get("notes") or "")
    if photo_type and photo_type not in notes.lower():
        notes = (f"[{photo_type}] {notes}").strip()
    return EstimateResult(
        meal_label=label,
        calories=float(obj.get("calories") or 0),
        protein=float(obj.get("protein_g") or 0),
        carbs=float(obj.get("carbs_g") or 0),
        fat=float(obj.get("fat_g") or 0),
        water_ml=float(obj.get("water_ml") or 0),
        source="ai",
        details=details,
        notes=notes,
    )


def has_vision_api() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    )


async def estimate_with_ai(
    text: str | None = None,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> EstimateResult | None:
    # Prefer OpenAI if set, else Gemini (free tier friendly for photos)
    result = await _estimate_openai(text, image_bytes, image_mime)
    if result:
        return result
    return await _estimate_gemini(text, image_bytes, image_mime)


def needs_ai_boost(text: str, local: EstimateResult) -> bool:
    """Prefer AI when free-form / heavy estimation and a key exists."""
    if not has_vision_api():
        return False
    if local.source in ("estimate", "mixed"):
        return True
    if CONVO_PREFIX.search(text.strip()) or len(text.split()) >= 8:
        return True
    return False


async def estimate_meal(
    text: str,
    foods: list[dict],
    prefer_ai: bool = False,
) -> EstimateResult:
    local = estimate_local(text, foods)
    if prefer_ai or needs_ai_boost(text, local):
        ai = await estimate_with_ai(text=text)
        if ai:
            return ai
    return local
