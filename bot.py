"""Telegram-bot: nomzodlarni kompetensiyalar bo'yicha Mini App va Webhook orqali qabul qilish (Technomart)."""
import asyncio
import json
import logging
import os
import re
import base64
from io import BytesIO

from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                         MessageHandler, PicklePersistence, filters)

import sheets
import store
from scoring import JOB, build_profile, evaluate, verdict_code

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("texnomart-bot")

TOKEN = os.environ.get("BOT_TOKEN", "")
RECRUITERS = {int(x) for x in re.split(r"[\s,;]+", os.environ.get("RECRUITER_IDS") or os.environ.get("RECRUITER_CHAT_ID", ""))
              if x.strip().lstrip("-").isdigit()}
EMOJI = {"QABUL": "🟢", "ZAXIRA": "🟡", "RAD": "🔴"}
VERDICT_ARGS = {"qabul": "QABUL", "zaxira": "ZAXIRA", "rad": "RAD"}

MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://uzkhan9669-ai.github.io/texnomart/")

GREETING = (
    "Assalomu alaykum! Bu %s kompaniyasidagi «%s» vakansiyasi uchun anketa.\n\n"
    "Shartlar:\n"
    "- %s\n"
    "- Grafik: %s\n"
    "- Daromad: %s\n"
    "- Tajriba shart emas, ustoz bilan o'rgatamiz.\n\n"
    "Iltimos, quyidagi tugmani bosib Mini App orqali anketani to'ldiring."
) % (JOB["company"], JOB["position"], JOB["training"], JOB["schedule"], JOB["income"])

HELP = (
    "Rekruter buyruqlari:\n"
    "/reyting - eng yuqori ballli nomzodlar (/reyting qabul, /reyting zaxira, /reyting rad)\n"
    "/songgi - oxirgi kelgan anketalar\n"
    "/stat - umumiy statistika\n"
    "/csv - barcha nomzodlar jadvali (Excel uchun)\n"
    "/nomzod 12 yoki /n_12 - to'liq profil\n"
    "/holat 12 chaqirildi - holatni o'zgartirish (%s)\n"
    "/anketa - anketani ochish tugmasini chiqarish"
) % ", ".join(store.STATUSES)


def is_rec(update):
    ids = set()
    if update.effective_user:
        ids.add(update.effective_user.id)
    if update.effective_chat:
        ids.add(update.effective_chat.id)
    return bool(ids & RECRUITERS)


def only_rec(fn):
    async def wrapper(update, context):
        if not is_rec(update):
            await update.effective_message.reply_text("Bu buyruq faqat rekruter uchun.")
            return
        return await fn(update, context)
    return wrapper


def split_text(text, limit=4000):
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = line
        else:
            cur = line if not cur else cur + "\n" + line
    parts.append(cur)
    return parts


async def send_long(bot, chat_id, text, markup=None):
    parts = split_text(text)
    for n, part in enumerate(parts):
        await bot.send_message(chat_id, part, reply_markup=markup if n == len(parts) - 1 else None)


async def sync_sheet(cid):
    if not sheets.enabled():
        return
    row = store.get(cid)
    if row:
        await asyncio.to_thread(sheets.push_row, dict(row))


def status_markup(cid, with_profile=False):
    rows = []
    if with_profile:
        rows.append([InlineKeyboardButton("To'liq profil", callback_data="p:%d" % cid)])
    rows.append([InlineKeyboardButton("✅ Chaqirish", callback_data="s:%d:chaqirildi" % cid),
                 InlineKeyboardButton("⭐ Zaxira", callback_data="s:%d:zaxira" % cid),
                 InlineKeyboardButton("❌ Rad", callback_data="s:%d:rad" % cid)])
    return InlineKeyboardMarkup(rows)


async def process_candidate_data(data: dict, user_id=0, username=""):
    """Общий процессор анкет (и из Telegram tg.sendData, и из Webhook/Google Apps Script)"""
    try:
        answers = data.get("answers", data)
        ev = evaluate(answers)
        code = verdict_code(ev["verdict"])
        red = sum(1 for f in ev["flags"] if f[0] == "🔴")
        yellow = sum(1 for f in ev["flags"] if f[0] == "🟡")
        flags = " | ".join(f[1] for f in ev["flags"])
        
        fio = data.get("fio") or data.get("name") or answers.get("fio") or "-"
        phone = data.get("phone") or answers.get("phone") or "-"
        age = data.get("age") or answers.get("age") or "-"
        marital = data.get("marital_status") or answers.get("marital_status") or "-"

        # Сохранение в SQLite
        cid = store.save(
            user_id, username, 
            json.dumps(answers, ensure_ascii=False), 
            fio, phone, 
            ev["pct"], code, red, yellow, flags
        )

        # Текст карточки для рекрутера
        card = (
            "🆕 <b>Yangi nomzod #%d</b>\n\n"
            "👤 <b>F.I.Sh:</b> %s\n"
            "🎂 <b>Yosh:</b> %s\n"
            "📞 <b>Tel:</b> %s\n"
            "💍 <b>Oilaviy ahvoli:</b> %s\n\n"
            "📊 <b>Natija:</b> %s %d%% (%s)\n"
            "🔴 <b>Qizil:</b> %d   🟡 <b>Sariq:</b> %d\n\n"
            "/n_%d - to'liq profil"
            % (cid, fio, age, phone, marital, EMOJI.get(code, "⚪"), ev["pct"], code, red, yellow, cid)
        )

        photo_base64 = data.get("photo") or answers.get("photo")

        # Отправка всем рекрутерам
        for rid in RECRUITERS:
            try:
                # Если у кандидата есть селфи (base64) — отправляем фото с подписью
                if photo_base64 and "," in photo_base64:
                    base64_data = photo_base64.split(",")[1]
                    image_bytes = BytesIO(base64.b64decode(base64_data))
                    image_bytes.name = f"selfie_{cid}.jpg"
                    await tg_app.bot.send_photo(
                        chat_id=rid,
                        photo=image_bytes,
                        caption=card,
                        parse_mode="HTML",
                        reply_markup=status_markup(cid, with_profile=True)
                    )
                else:
                    await tg_app.bot.send_message(
                        chat_id=rid,
                        text=card,
                        parse_mode="HTML",
                        reply_markup=status_markup(cid, with_profile=True)
                    )
            except Exception:
                log.exception("Rekruterga yuborib bo'lmadi: %s", rid)
                
        await sync_sheet(cid)
        return True
    except Exception as e:
        log.error("Xatolik nomzodni qayta ishlashda: %s", e)
        return False


# ---------------------------------------------------------------- Nomzod tomoni (Mini App / Webhook)
async def send_anketa_button(update_or_message):
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 ANKETA", web_app=WebAppInfo(url=MINI_APP_URL))
    ]])
    await update_or_message.reply_text(GREETING, reply_markup=markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rec(update):
        await update.effective_message.reply_text(HELP)
        return
    await send_anketa_button(update.effective_message)


async def anketa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rec(update):
        return
    await send_anketa_button(update.effective_message)


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mini App tg.sendData orqali kelsa"""
    message = update.effective_message
    if not message or not message.web_app_data:
        return

    try:
        data = json.loads(message.web_app_data.data)
        user = update.effective_user
        await process_candidate_data(data, user_id=user.id, username=user.username or "")
        await message.reply_text("✅ Rahmat! Anketa muvaffaqiyatli qabul qilindi.")
    except Exception as e:
        log.error("Web app data error: %s", e)
        await message.reply_text("⚠️ Xatolik yuz berdi. Qaytadan urinib ko'ring.")


# ---------------------------------------------------------------- Webhook Server (HTTP endpoint)
async def handle_http_post(request):
    """Google Apps Script или Mini App direct fetch зарос прилетает сюда"""
    try:
        data = await request.json()
        asyncio.create_task(process_candidate_data(data))
        return web.json_response({"status": "ok"})
    except Exception as e:
        log.error("HTTP Webhook error: %s", e)
        return web.json_response({"status": "error", "message": str(e)}, status=400)


# ---------------------------------------------------------------- Rekruter tomoni
async def send_profile(bot, chat_id, cid):
    row = store.get(cid)
    if not row:
        await bot.send_message(chat_id, "Nomzod #%d topilmadi." % cid)
        return
    text = build_profile(json.loads(row["answers"]), row["ts"])
    text += "\n\nTelegram: %s\nHolat: %s\n#%d" % (("@" + row["username"]) if row["username"] else "-", row["status"], cid)
    await send_long(bot, chat_id, text, markup=status_markup(cid))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    if not is_rec(update):
        await cq.answer("Ruxsat yo'q", show_alert=True)
        return
    await cq.answer()
    parts = cq.data.split(":")
    if parts[0] == "p" and len(parts) == 2 and parts[1].isdigit():
        await send_profile(context.bot, cq.message.chat_id, int(parts[1]))
    elif parts[0] == "s" and len(parts) == 3 and parts[1].isdigit():
        ok = store.set_status(int(parts[1]), parts[2])
        await cq.message.reply_text("#%s holati: %s" % (parts[1], parts[2]) if ok else "Holatni o'zgartirib bo'lmadi.")
        if ok:
            await sync_sheet(int(parts[1]))


def row_line(r):
    return "%d. %s %s - %d%% (🔴%d 🟡%d) %s | %s /n_%d" % (
        r["id"], EMOJI.get(r["verdict"], ""), r["fio"] or "-", r["pct"], r["red"], r["yellow"],
        r["status"], r["verdict"], r["id"])


async def list_reply(update, context, rows, title):
    if not rows:
        await update.effective_message.reply_text("Hozircha nomzodlar yo'q.")
        return
    await send_long(context.bot, update.effective_chat.id, title + "\n\n" + "\n".join(row_line(r) for r in rows))


@only_rec
async def reyting(update, context):
    arg = (context.args[0].lower() if context.args else "")
    verdict = VERDICT_ARGS.get(arg)
    await list_reply(update, context, store.listing(verdict=verdict, limit=20),
                     "Reyting (ball bo'yicha)" + (": " + verdict if verdict else ""))


@only_rec
async def songgi(update, context):
    await list_reply(update, context, store.listing(newest=True, limit=15), "Oxirgi anketalar")


@only_rec
async def stat(update, context):
    by_v, by_s = store.stats()
    total = sum(by_v.values())
    lines = ["Jami nomzodlar: %d" % total, ""]
    lines += ["%s %s: %d" % (EMOJI[k], k, by_v.get(k, 0)) for k in ("QABUL", "ZAXIRA", "RAD")]
    lines += ["", "Holatlar: " + ", ".join("%s %d" % (k, by_s.get(k, 0)) for k in store.STATUSES)]
    await update.effective_message.reply_text("\n".join(lines))


@only_rec
async def csv_export(update, context):
    await update.effective_message.reply_document(document=store.export_csv(), filename="nomzodlar.csv")


@only_rec
async def nomzod(update, context):
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Masalan: /nomzod 12")
        return
    await send_profile(context.bot, update.effective_chat.id, int(context.args[0]))


@only_rec
async def open_profile(update, context):
    m = re.match(r"^/n_(\d+)", update.effective_message.text or "")
    if m:
        await send_profile(context.bot, update.effective_chat.id, int(m.group(1)))


@only_rec
async def holat(update, context):
    if len(context.args) != 2 or not context.args[0].isdigit():
        await update.effective_message.reply_text("Masalan: /holat 12 chaqirildi\nHolatlar: " + ", ".join(store.STATUSES))
        return
    ok = store.set_status(int(context.args[0]), context.args[1].lower())
    await update.effective_message.reply_text("Holat o'zgartirildi." if ok else "Nomzod yoki holat noto'g'ri.")
    if ok:
        await sync_sheet(int(context.args[0]))


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    log.error("Telegram error:", exc_info=context.error)


# Глобальная переменная для обращения из aiohttp
tg_app = None

async def start_web_server():
    """Фоновый HTTP-сервер для приема POST запросов из Mini App/Google Apps Script"""
    web_app = web.Application()
    web_app.router.add_post('/', handle_http_post)
    web_app.router.add_post('/webhook', handle_http_post)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    try:
        await site.start()
        log.info(f"HTTP Server runs on port {port}")
    except Exception as e:
        log.warning(f"Could not bind HTTP server on port {port}: {e}")


def main():
    global tg_app
    if not TOKEN:
        raise SystemExit("BOT_TOKEN o'rnatilmagan.")
    if not RECRUITERS:
        log.warning("RECRUITER_IDS bo'sh!")
    
    store.init()
    
    persistence = PicklePersistence(filepath=os.environ.get("STATE_PATH", "state.pkl"))
    tg_app = Application.builder().token(TOKEN).persistence(persistence).build()
    
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("anketa", anketa))
    tg_app.add_handler(CommandHandler("reyting", reyting))
    tg_app.add_handler(CommandHandler("songgi", songgi))
    tg_app.add_handler(CommandHandler("stat", stat))
    tg_app.add_handler(CommandHandler("csv", csv_export))
    tg_app.add_handler(CommandHandler("nomzod", nomzod))
    tg_app.add_handler(CommandHandler("holat", holat))
    
    tg_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    tg_app.add_handler(MessageHandler(filters.Regex(r"^/n_\d+"), open_profile))
    tg_app.add_handler(CallbackQueryHandler(on_button))
    tg_app.add_error_handler(error_handler)
    
    # Запуск фонового веб-сервера вместе с лонг-поллингом бота
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    
    log.info("Bot started...")
    tg_app.run_polling()


if __name__ == "__main__":
    main()
