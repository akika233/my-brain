# Nutrition

Daily diet tracking for the 45 kg body composition goal.

## Daily targets

| Macro | Target | Why |
|---|---|---|
| Calories | 1,400 kcal | Moderate deficit (~350 kcal below maintenance) |
| Protein | 95 g | Preserves muscle during fat loss |
| Carbs | 140 g | Energy for training |
| Fat | 45 g | Hormones + satiety |
| Water | 2,000 ml | Recovery + performance |

## Sample day (~1,400 kcal / 95g protein)

**Breakfast (~350 kcal, 25g protein)**
- Greek yogurt 150g + berries + 15g almonds

**Lunch (~450 kcal, 35g protein)**
- Grilled chicken 120g + rice 80g cooked + vegetables

**Snack (~150 kcal, 15g protein)**
- Protein shake or 2 boiled eggs

**Dinner (~450 kcal, 30g protein)**
- Fish or tofu 150g + sweet potato + salad

Adjust portions to hit targets. Weigh protein sources if unsure.

## How to log

1. **Canvas — text** — type what you ate, click "Add meal to today", overview updates live
2. **Canvas — photo** — attach meal photo, click "Analyze meal photo with AI", attach same photo in the chat that opens
3. **Tell the AI** — describe meals in chat; it updates `data/diet-log.json`
4. **Sync** — click "Sync today's log to vault" in the canvas to save totals to GitHub

## Logging format

Each day in `data/diet-log.json`:
```json
{
  "date": "2026-07-14",
  "calories": 1380,
  "protein_g": 92,
  "carbs_g": 135,
  "fat_g": 44,
  "water_ml": 1800,
  "meals": ["yogurt + berries", "chicken rice bowl", "protein shake", "salmon + potato"],
  "notes": ""
}
```

## Rules
- Hit protein first — everything else flexes around it
- Don't go below 1,200 kcal
- Training days: eat carbs around your workout
- Weekend treats are fine if weekly average stays on target

**See also:** [[progression-map]], [[body-composition]], [[gym-log]]

**Section:** [[health]]
