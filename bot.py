"""Telegram-bot: nomzodlarni kompetensiyalar bo'yicha so'rovdan o'tkazish va baholash (Texnomart, sotuvchi-konsultant).

Ishga tushirish:
    pip install -r requirements.txt
    export BOT_TOKEN="@BotFather bergan token"
    export RECRUITER_IDS="123456789,987654321"     # rekruterlarning Telegram ID lari (@userinfobot dan bilib oling)
    python bot.py

Nomzod anketani to'ldiradi va hech qanday baho ko'rmaydi. Rekruterga qisqa karta keladi (ball, tavsiya, flaglar)
va tugmalar: to'liq profil, chaqirish, zaxira, rad. Hamma nomzodlar candidates.db bazasida saqlanadi.
Rekruter buyruqlari: /reyting, /songgi, /stat, /csv, /nomzod, /holat (/start yozsangiz ro'yxat chiqadi).
"""
import asyncio
import json
import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, PicklePersistence, filters)

import sheets
import store
import webapi
from scoring import JOB, QUESTIONS, build_profile, evaluate, verdict_code

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("texnomart-bot")

TOKEN = os.environ.get("BOT_TOKEN", "")
RECRUITERS = {int(x) for x in re.split(r"[\s,;]+", os.environ.get("RECRUITER_IDS") or os.environ.get("RECRUITER_CHAT_ID", ""))
              if x.strip().lstrip("-").isdigit()}
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
EMOJI = {"QABUL": "🟢", "ZAXIRA": "🟡", "RAD": "🔴"}
VERDICT_ARGS = {"qabul": "QABUL", "zaxira": "ZAXIRA", "rad": "RAD"}

GREETING = (
    "Assalomu alaykum! Bu %s kompaniyasidagi «%s» vakansiyasi uchun anketa.\n\n"
    "Shartlar:\n"
    "- %s\n"
    "- Grafik: %s\n"
    "- Daromad: %s\n"
    "- Tajriba shart emas, ustoz bilan o'rgatamiz.\n\n"
    "Anketa taxminan 15 daqiqa oladi. Iltimos, rost va o'z so'zlaringiz bilan javob bering. "
    "Oldingi savolga qaytish uchun /orqaga ni yozing.\n\n"
    "Anketani boshlash tugmasini bosib, ism, telefon, javoblaringiz va selfie suratingiz ishga qabul qilish "
    "maqsadida qayta ishlanishiga rozilik bildirasiz."
) % (JOB["company"], JOB["position"], JOB["training"], JOB["schedule"], JOB["income"])

HELP = (
    "Rekruter buyruqlari:\n"
    "/reyting - eng yuqori ballli nomzodlar (/reyting qabul, /reyting zaxira, /reyting rad)\n"
    "/songgi - oxirgi kelgan anketalar\n"
    "/stat - umumiy statistika\n"
    "/csv - barcha nomzodlar jadvali (Excel uchun)\n"
    "/nomzod 12 yoki /n_12 - to'liq profil\n"
    "/holat 12 chaqirildi - holatni o'zgartirish (%s)\n"
    "/anketa - anketani o'zingiz sinab ko'rish"
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
    """Telegram limiti 4096 belgi: matnni qator chegarasida bo'laklarga ajratadi."""
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # juda uzun bitta qator
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
    """Nomzod yozuvini Google Tablitsaga yuboradi (agar SHEETS_URL berilgan bo'lsa). Botni to'xtatmaydi."""
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


# ---------------------------------------------------------------- nomzod tomoni
async def send_question(chat_id, context):
    st = context.user_data
    q = QUESTIONS[st["i"]]
    if q.get("block"):
        await context.bot.send_message(chat_id, "— %s —" % q["block"])
    text = "(%d/%d) %s" % (st["i"] + 1, len(QUESTIONS), q["text"])
    markup = None
    if q["type"] == "choice":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(o, callback_data="a:%d:%d" % (st["i"], n))]
                                       for n, o in enumerate(q["options"])])
    await context.bot.send_message(chat_id, text, reply_markup=markup)


async def begin(update, context):
    context.user_data.clear()
    context.user_data.update({"i": -1, "answers": {}})
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton("📝 Anketani to'ldirish (selfie bilan)", web_app=WebAppInfo(url=WEBAPP_URL))])
    rows.append([InlineKeyboardButton("💬 Chatda to'ldirish", callback_data="go")])
    await update.effective_message.reply_text(GREETING, reply_markup=InlineKeyboardMarkup(rows))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rec(update):
        await update.effective_message.reply_text(HELP)
        return
    await begin(update, context)


async def anketa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await begin(update, context)


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data
    if "i" not in st or st["i"] <= 0:
        await update.effective_message.reply_text("Orqaga qaytib bo'lmaydi.")
        return
    st["i"] -= 1
    await send_question(update.effective_chat.id, context)


async def advance(chat_id, context, user):
    st = context.user_data
    st["i"] += 1
    if st["i"] >= len(QUESTIONS):
        await finish(chat_id, context, user)
    else:
        await send_question(chat_id, context)


async def publish(bot, user_id, username, a, photo=None):
    """Javoblarni baholaydi, bazaga saqlaydi, rekruterga karta (selfie bilan) yuboradi va jadvalga yozadi."""
    ev = evaluate(a)
    code = verdict_code(ev["verdict"])
    red = sum(1 for f in ev["flags"] if f[0] == "🔴")
    yellow = sum(1 for f in ev["flags"] if f[0] == "🟡")
    flags = " | ".join(f[1] for f in ev["flags"])
    cid = store.save(user_id, username or "", json.dumps(a, ensure_ascii=False), a.get("fio", ""),
                     a.get("phone", ""), ev["pct"], code, red, yellow, flags)
    card = ("🆕 Yangi nomzod #%d\n%s, %s yosh, %s\n%s %d%%  %s\n🔴 %d   🟡 %d\n/n_%d - to'liq profil"
            % (cid, a.get("fio", "-"), a.get("age", "-"), a.get("phone", "-"),
               EMOJI[code], ev["pct"], code, red, yellow, cid))
    markup = status_markup(cid, with_profile=True)
    photo_ref = photo  # birinchi rekruterga baytlar, keyin Telegram file_id
    for rid in sorted(RECRUITERS):
        try:
            if photo_ref is not None:
                msg = await bot.send_photo(rid, photo_ref, caption=card, reply_markup=markup)
                if isinstance(photo_ref, (bytes, bytearray)) and getattr(msg, "photo", None):
                    photo_ref = msg.photo[-1].file_id
                    store.set_photo(cid, photo_ref)
            else:
                await bot.send_message(rid, card, reply_markup=markup)
        except Exception:  # rekruter botni bloklagan bo'lishi mumkin
            log.exception("Rekruterga yuborib bo'lmadi: %s", rid)
    await sync_sheet(cid)
    return cid


async def finish(chat_id, context, user):
    a = dict(context.user_data["answers"])
    context.user_data.clear()
    await context.bot.send_message(chat_id, "Rahmat! Anketa yuborildi. Rekruter siz ko'rsatgan raqam orqali bog'lanadi.")
    await publish(context.bot, user.id, user.username, a)


async def accept_web(bot, user, answers, photo):
    """Mini App dan kelgan anketa (webapi tekshirgan)."""
    await publish(bot, user["id"], user.get("username"), answers, photo)
    try:
        await bot.send_message(user["id"], "Rahmat! Anketangiz qabul qilindi. Rekruter siz ko'rsatgan raqam orqali bog'lanadi.")
    except Exception:
        log.exception("Nomzodga javob yuborib bo'lmadi")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    data = cq.data or ""
    if data.startswith(("p:", "s:")):
        await rec_button(update, context)
        return
    await cq.answer()
    st = context.user_data
    if "i" not in st:
        await cq.message.reply_text("Anketani boshlash uchun /start ni bosing.")
        return
    if data == "go":
        if st["i"] == -1:
            st["i"] = 0
            await send_question(cq.message.chat_id, context)
        return
    m = re.fullmatch(r"a:(\d+):(\d+)", data)
    if not m:
        return
    qi, n = int(m.group(1)), int(m.group(2))
    if qi != st["i"] or not 0 <= qi < len(QUESTIONS):  # eski tugma bosildi
        return
    q = QUESTIONS[qi]
    if q["type"] != "choice" or n >= len(q["options"]):
        return
    st["answers"][q["key"]] = q["options"][n]
    st["answers"][q["key"] + "_i"] = n
    await advance(cq.message.chat_id, context, cq.from_user)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data
    msg = update.effective_message
    if "i" not in st or st["i"] < 0:
        await msg.reply_text("Anketani boshlash uchun /start ni bosing.")
        return
    q = QUESTIONS[st["i"]]
    if q["type"] == "choice":
        await msg.reply_text("Iltimos, savol ostidagi tugma orqali variantni tanlang.")
        return
    text = (msg.text or "").strip()
    digits = re.sub(r"\D", "", text)
    if q["type"] == "number" and not digits:
        await msg.reply_text("Iltimos, raqam kiriting.")
        return
    if q["key"] == "phone" and not 9 <= len(digits) <= 12:
        await msg.reply_text("Raqam noto'g'ri. Masalan: +998 90 123 45 67")
        return
    if q["key"] == "age" and not 14 <= int(digits[:3]) <= 80:
        await msg.reply_text("Yoshni to'g'ri kiriting.")
        return
    st["answers"][q["key"]] = text[:1500]
    await advance(update.effective_chat.id, context, update.effective_user)


# ---------------------------------------------------------------- rekruter tomoni
async def send_profile(bot, chat_id, cid):
    row = store.get(cid)
    if not row:
        await bot.send_message(chat_id, "Nomzod #%d topilmadi." % cid)
        return
    text = build_profile(json.loads(row["answers"]), row["ts"])
    text += "\n\nTelegram: %s\nHolat: %s\n#%d" % (("@" + row["username"]) if row["username"] else "-", row["status"], cid)
    if row["photo_file_id"]:
        try:
            await bot.send_photo(chat_id, row["photo_file_id"], caption="#%d %s" % (cid, row["fio"] or ""))
        except Exception:
            log.exception("Selfieni yuborib bo'lmadi")
    await send_long(bot, chat_id, text, markup=status_markup(cid))


async def rec_button(update, context):
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


async def on_error(update, context):
    log.error("Xatolik", exc_info=context.error)


def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN o'rnatilmagan.")
    if not RECRUITERS:
        log.warning("RECRUITER_IDS bo'sh: nomzod kartalari hech kimga yuborilmaydi!")
    store.init()
    persistence = PicklePersistence(filepath=os.environ.get("STATE_PATH", "state.pkl"))
    async def post_init(application):
        port = int(os.environ.get("PORT", "8080"))
        webapi.start_server(asyncio.get_running_loop(),
                            lambda user, answers, photo: accept_web(application.bot, user, answers, photo),
                            TOKEN, port, os.environ.get("WEBAPP_ORIGIN", ""))
        if not WEBAPP_URL:
            log.warning("WEBAPP_URL bo'sh: Mini App tugmasi ko'rsatilmaydi (faqat chat rejimi).")

    app = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("anketa", anketa))
    app.add_handler(CommandHandler("orqaga", back))
    app.add_handler(CommandHandler("reyting", reyting))
    app.add_handler(CommandHandler("songgi", songgi))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("csv", csv_export))
    app.add_handler(CommandHandler("nomzod", nomzod))
    app.add_handler(CommandHandler("holat", holat))
    app.add_handler(MessageHandler(filters.Regex(r"^/n_\d+"), open_profile))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    app.run_polling()


if __name__ == "__main__":
    main()
