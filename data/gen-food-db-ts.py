import json
from pathlib import Path

db = json.loads(Path(__file__).with_name("food-db.json").read_text(encoding="utf-8"))
lines = []
for f in db["foods"]:
    kw = json.dumps(f["keywords"], ensure_ascii=False)
    line = f'  {{ keywords: {kw}, calories: {f["calories"]}, protein: {f["protein"]}, carbs: {f["carbs"]}, fat: {f["fat"]}'
    if "baseGrams" in f:
        line += f', baseGrams: {f["baseGrams"]}'
    if "waterMl" in f:
        line += f', waterMl: {f["waterMl"]}'
    line += " },"
    lines.append(line)

Path(__file__).with_name("food-db.generated.ts.txt").write_text("\n".join(lines) + f"\n// {len(lines)} entries\n", encoding="utf-8")
print(len(lines), "entries written")
