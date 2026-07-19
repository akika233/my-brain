"""Telegram bot for daily diet + InBody logging into the my-brain vault."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from diet_store import DietStore, format_day, today_str
from food_matcher import load_food_db
from inbody_store import InBodyStore, parse_inbody_quick
from nutrition_estimate import estimate_meal, estimate_with_ai, has_vision_api

ROOT = Path(__file__).resolve().parent.parent
BOT_DIR = Path(__file__).resolve().parent

load_dotenv(BOT_DIR / ".env")
load_dotenv(ROOT / ".env")

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("brain-bot")

# Conversation states for /inbody wizard
WEIGHT, SMM, PBF, ECW, CONFIRM = range(5)

HELP = """🧠 my-brain diet bot

Log food — send what you ate (free text OK):
  kipfilet 120g + rijst 80g
  I ate a cheese sandwich and melon
  lunch: tomato beef noodles ~500g

Or send a photo of your meal OR a food package / nutrition label.
  (Caption optional: "100g" or "hele bak" — needs GEMINI_API_KEY or OPENAI_API_KEY)

The bot estimates calories/protein/carbs/fat and adds them to today's diet log.

Commands
  /today — today's totals vs targets
  /week — last 7 logged days
  /water 300 — add water
  /undo — remove last meal today
  /inbody — log an InBody scan (step by step)
  /inbody_quick 49.2kg smm 20.8 pbf 25.1
  /note felt tired — set today's note
  /whoami — your Telegram user id
  /help — this message
"""


def vault_paths() -> tuple[Path, Path, Path, Path]:
    return (
        ROOT / "data" / "diet-log.json",
        ROOT / "data" / "food-db.json",
        ROOT / "data" / "progression.json",
        ROOT / "health" / "body-composition.md",
    )


def get_stores() -> tuple[DietStore, InBodyStore, list]:
    diet_path, food_path, prog_path, body_md = vault_paths()
    return DietStore(diet_path), InBodyStore(prog_path, body_md), load_food_db(food_path)


def allowed_user(user_id: int | None) -> bool:
    raw = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if not raw:
        return True  # open if not configured (local use)
    allowed = {int(x.strip()) for x in raw.split(",") if x.strip()}
    return user_id in allowed


async def guard(update: Update) -> bool:
    user = update.effective_user
    if user and allowed_user(user.id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("Unauthorized.")
    return False


def maybe_git_commit(message: str) -> str | None:
    if os.getenv("GIT_AUTO_COMMIT", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        subprocess.run(["git", "add", "data/", "health/body-composition.md"], cwd=ROOT, check=True)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            return None
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
        if os.getenv("GIT_AUTO_PUSH", "").lower() in ("1", "true", "yes"):
            subprocess.run(["git", "push"], cwd=ROOT, check=True)
            return "committed + pushed"
        return "committed"
    except subprocess.CalledProcessError as e:
        log.warning("git auto-commit failed: %s", e)
        return "git failed"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    await update.message.reply_text(HELP)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    diet, _, _ = get_stores()
    entry = diet.get_entry()
    await update.message.reply_text(format_day(entry, diet.targets()))


async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    diet, _, _ = get_stores()
    targets = diet.targets()
    days = diet.recent_days(7)
    if not days:
        await update.message.reply_text("No entries yet.")
        return
    lines = ["📊 Last logged days\n"]
    for e in days:
        c = e.get("calories") or 0
        p = e.get("protein_g") or 0
        lines.append(
            f"{e['date']}: {c:.0f}/{targets['calories']} kcal · "
            f"{p:.0f}/{targets['protein_g']}g P · {len(e.get('meals') or [])} meals"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /water 300")
        return
    try:
        ml = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("Need a number, e.g. /water 300")
        return
    diet, _, _ = get_stores()
    entry = diet.add_water(ml)
    git = maybe_git_commit(f"Log {ml:g}ml water via Telegram")
    extra = f"\n({git})" if git else ""
    await update.message.reply_text(
        f"💧 +{ml:g} ml → {entry.get('water_ml') or 0:.0f} ml today{extra}\n\n"
        + format_day(entry, diet.targets())
    )


async def cmd_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    note = " ".join(context.args).strip()
    if not note:
        await update.message.reply_text("Usage: /note felt low energy today")
        return
    diet, _, _ = get_stores()
    entry = diet.set_note(note)
    git = maybe_git_commit(f"Add diet note for {today_str()} via Telegram")
    extra = f"\n({git})" if git else ""
    await update.message.reply_text(f"Note saved.{extra}\n\n" + format_day(entry, diet.targets()))


async def cmd_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    diet, _, foods = get_stores()
    removed, entry = diet.undo_last_meal()
    if not removed:
        await update.message.reply_text("Nothing to undo today.")
        return
    # Best-effort: re-estimate removed label to subtract macros
    from nutrition_estimate import estimate_local

    parsed = estimate_local(removed.lstrip("~"), foods)
    entry = diet.subtract_macros(
        parsed.calories, parsed.protein, parsed.carbs, parsed.fat, parsed.water_ml
    )
    msg = (
        f"↩️ Removed: {removed}\n"
        f"−{parsed.calories:.0f} kcal · −{parsed.protein:.0f}g P"
    )
    git = maybe_git_commit(f"Undo meal via Telegram ({today_str()})")
    if git:
        msg += f"\n({git})"
    await update.message.reply_text(msg + "\n\n" + format_day(entry, diet.targets()))


def _format_log_reply(est, entry, targets) -> str:
    source_label = {
        "food-db": "food database",
        "mixed": "food database + estimate",
        "estimate": "estimated",
        "ai": "AI estimate",
    }.get(est.source, est.source)
    lines = [
        f"✅ Logged ({source_label}): {est.meal_label}",
        f"+{est.calories:.0f} kcal · +{est.protein:.0f}g P · "
        f"+{est.carbs:.0f}g C · +{est.fat:.0f}g F",
    ]
    for d in est.details[:8]:
        lines.append(f"  · {d}")
    if est.notes:
        lines.append(f"Note: {est.notes}")
    git = maybe_git_commit(f"Log meal via Telegram ({today_str()})")
    if git:
        lines.append(f"({git})")
    lines.append("")
    lines.append(format_day(entry, targets))
    return "\n".join(lines)


async def log_meal_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    await update.message.chat.send_action("typing")
    diet, _, foods = get_stores()
    est = await estimate_meal(text, foods)
    entry = diet.add_meal(
        est.meal_label,
        est.calories,
        est.protein,
        est.carbs,
        est.fat,
        est.water_ml,
    )
    await update.message.reply_text(_format_log_reply(est, entry, diet.targets()))


async def log_meal_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    if not update.message.photo:
        return

    caption = (update.message.caption or "").strip()
    await update.message.chat.send_action("typing")

    if not has_vision_api():
        diet, _, foods = get_stores()
        if caption:
            est = await estimate_meal(caption, foods, prefer_ai=False)
            entry = diet.add_meal(
                est.meal_label,
                est.calories,
                est.protein,
                est.carbs,
                est.fat,
                est.water_ml,
            )
            await update.message.reply_text(
                "Photo analysis needs a free Gemini key (or OpenAI).\n"
                "Add GEMINI_API_KEY to telegram-bot/.env — see README.\n"
                "Logged from caption only for now:\n\n"
                + _format_log_reply(est, entry, diet.targets())
            )
        else:
            await update.message.reply_text(
                "Got the photo — to estimate from meals or package labels, add a free "
                "Gemini API key:\n"
                "1. Open https://aistudio.google.com/apikey\n"
                "2. Create key → put in telegram-bot/.env as GEMINI_API_KEY=...\n"
                "3. Restart the bot\n\n"
                "Tip: you can also caption the photo, e.g. `magere kwark 150g`"
            )
        return

    photo = update.message.photo[-1]  # largest
    tg_file = await context.bot.get_file(photo.file_id)
    buf = await tg_file.download_as_bytearray()

    status = await update.message.reply_text("📸 Analyzing photo (meal / package / label)…")

    ai = await estimate_with_ai(
        text=caption or None,
        image_bytes=bytes(buf),
        image_mime="image/jpeg",
    )
    diet, _, foods = get_stores()

    if ai is None:
        await status.edit_text(
            "Couldn't analyze that photo. Try a clearer shot of the plate or "
            "voedingswaarden label, or send text like `kipfilet 120g`."
        )
        return

    entry = diet.add_meal(
        ai.meal_label,
        ai.calories,
        ai.protein,
        ai.carbs,
        ai.fat,
        ai.water_ml,
    )
    await status.edit_text(_format_log_reply(ai, entry, diet.targets()))


# --- InBody conversation ---


async def inbody_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard(update):
        return ConversationHandler.END
    context.user_data["inbody"] = {"date": today_str()}
    await update.message.reply_text(
        "InBody log — what's your weight in kg?\n"
        "(or /cancel)\n\n"
        "Tip: for one-shot paste use /inbody_quick"
    )
    return WEIGHT


async def inbody_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["inbody"]["weight_kg"] = float(
            update.message.text.replace(",", ".").replace("kg", "").strip()
        )
    except (ValueError, AttributeError):
        await update.message.reply_text("Send a number, e.g. 49.2")
        return WEIGHT
    await update.message.reply_text("SMM (skeletal muscle mass) in kg? Or send `-` to skip.")
    return SMM


async def inbody_smm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text not in ("-", "skip", ""):
        try:
            context.user_data["inbody"]["smm_kg"] = float(text.replace(",", ".").replace("kg", ""))
        except ValueError:
            await update.message.reply_text("Number or `-` to skip")
            return SMM
    await update.message.reply_text("PBF (body fat %) ? Or `-` to skip.")
    return PBF


async def inbody_pbf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text not in ("-", "skip", ""):
        try:
            context.user_data["inbody"]["pbf_percent"] = float(
                text.replace(",", ".").replace("%", "")
            )
        except ValueError:
            await update.message.reply_text("Number or `-` to skip")
            return PBF
    await update.message.reply_text("ECW ratio? Or `-` to skip.")
    return ECW


async def inbody_ecw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text not in ("-", "skip", ""):
        try:
            context.user_data["inbody"]["ecw_ratio"] = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Number or `-` to skip")
            return ECW

    d = context.user_data["inbody"]
    summary = (
        f"Save this InBody for {d['date']}?\n"
        f"Weight: {d.get('weight_kg')} kg\n"
        f"SMM: {d.get('smm_kg', '—')}\n"
        f"PBF: {d.get('pbf_percent', '—')}\n"
        f"ECW: {d.get('ecw_ratio', '—')}\n\n"
        "Reply yes / no"
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def inbody_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip().lower()
    if text not in ("yes", "y", "ja", "ok", "save"):
        await update.message.reply_text("Cancelled.")
        context.user_data.pop("inbody", None)
        return ConversationHandler.END

    d = context.user_data["inbody"]
    _, store, _ = get_stores()
    entry = store.add_checkin(
        weight_kg=d["weight_kg"],
        smm_kg=d.get("smm_kg"),
        pbf_percent=d.get("pbf_percent"),
        ecw_ratio=d.get("ecw_ratio"),
        day=d.get("date"),
    )
    git = maybe_git_commit(f"Log InBody {entry['date']} via Telegram")
    extra = f"\n({git})" if git else ""
    await update.message.reply_text(
        f"✅ InBody saved for {entry['date']}\n"
        f"{entry['weight_kg']} kg"
        + (f" · SMM {entry['smm_kg']}" if "smm_kg" in entry else "")
        + (f" · PBF {entry['pbf_percent']}%" if "pbf_percent" in entry else "")
        + extra
    )
    context.user_data.pop("inbody", None)
    return ConversationHandler.END


async def inbody_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("inbody", None)
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def cmd_inbody_quick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update):
        return
    raw = " ".join(context.args).strip()
    if not raw:
        await update.message.reply_text(
            "Usage:\n/inbody_quick 49.2kg smm 20.8 pbf 25.1 ecw 0.365"
        )
        return
    parsed = parse_inbody_quick(raw)
    if "weight_kg" not in parsed:
        await update.message.reply_text("Need at least a weight, e.g. `49.2kg`", parse_mode="Markdown")
        return
    _, store, _ = get_stores()
    entry = store.add_checkin(**parsed)
    git = maybe_git_commit(f"Log InBody {entry['date']} via Telegram")
    extra = f"\n({git})" if git else ""
    await update.message.reply_text(
        f"✅ InBody saved\n{entry}" + extra
    )


async def cmd_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"Your Telegram user id: `{user.id if user else '?'}`\n"
        "Put this in `.env` as TELEGRAM_ALLOWED_USER_ID",
        parse_mode="Markdown",
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN. Copy telegram-bot/.env.example to .env and fill it in."
        )

    app = Application.builder().token(token).build()

    inbody_conv = ConversationHandler(
        entry_points=[CommandHandler("inbody", inbody_start)],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, inbody_weight)],
            SMM: [MessageHandler(filters.TEXT & ~filters.COMMAND, inbody_smm)],
            PBF: [MessageHandler(filters.TEXT & ~filters.COMMAND, inbody_pbf)],
            ECW: [MessageHandler(filters.TEXT & ~filters.COMMAND, inbody_ecw)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, inbody_confirm)],
        },
        fallbacks=[CommandHandler("cancel", inbody_cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("water", cmd_water))
    app.add_handler(CommandHandler("note", cmd_note))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(CommandHandler("inbody_quick", cmd_inbody_quick))
    app.add_handler(CommandHandler("whoami", cmd_whoami))
    app.add_handler(inbody_conv)
    app.add_handler(MessageHandler(filters.PHOTO, log_meal_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, log_meal_text))

    log.info("Bot starting (vault root: %s)", ROOT)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
