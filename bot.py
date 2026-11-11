"""Telegram-бот Texnomart: анкета кандидата (Mini App или чат), оценка и карточка для рекрутера.

Запуск:
    pip install -r requirements.txt
    BOT_TOKEN, RECRUITER_IDS, WEBAPP_URL, WEBAPP_ORIGIN (и при желании SHEETS_URL, SHEETS_SECRET) задаются
    переменными окружения; затем python bot.py

Кандидат выбирает язык (uz/ru/en), заполняет анкету и оценку не видит. Рекрутеру всё приходит на русском:
карточка с селфи, баллом, вердиктом, флагами и кнопками статуса. Кандидаты хранятся в candidates.db.
Команды рекрутера: /reyting, /songgi, /stat, /csv, /nomzod, /holat (список по /start).
"""
import asyncio
import json
import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, PicklePersistence, filters)

import dashboard
import i18n
import notices
import sheets
import store
import webapi
from scoring import (JOB, QUESTIONS, VERDICT_RU, applies, build_profile, clean_answers, evaluate,
                     position_name, verdict_code)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("texnomart-bot")

TOKEN = os.environ.get("BOT_TOKEN", "")
RECRUITERS = {int(x) for x in re.split(r"[\s,;]+", os.environ.get("RECRUITER_IDS") or os.environ.get("RECRUITER_CHAT_ID", ""))
              if x.strip().lstrip("-").isdigit()}
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
EMOJI = {"QABUL": "🟢", "ZAXIRA": "🟡", "RAD": "🔴"}
VERDICT_ARGS = {"qabul": "QABUL", "zaxira": "ZAXIRA", "rad": "RAD", "принять": "QABUL", "резерв": "ZAXIRA", "отказ": "RAD"}
POS_ARGS = {"konsultant": 0, "консультант": 0, "kassir": 1, "кассир": 1}
STATUS_RU = {k: v.lower() for k, v in notices.STAGE_RU.items()}

HELP = (
    "Команды рекрутера:\n"
    "/reyting - лучшие кандидаты по баллу (можно: /reyting qabul, zaxira, rad, kassir, konsultant)\n"
    "/songgi - последние анкеты\n"
    "/stat - общая статистика\n"
    "/csv - таблица всех кандидатов (для Excel)\n"
    "/otchet - отчёт для руководства в Excel за месяц (/otchet 30 - за последние 30 дней)\n"
    "/nomzod 12 или /n_12 - полный профиль\n"
    "/pdf_12 - анкета кандидата файлом PDF\n"
    "/holat 12 sozvon - перевести на этап (%s). Кандидату уйдёт сообщение после вашего подтверждения.\n"
    "   собеседование: /holat 12 sobes 15.11.2026; 14:00; адрес\n"
    "   стажировка: /holat 12 staj 20.11.2026; адрес\n"
    "/anketa - пройти анкету самому"
) % ", ".join("%s = %s" % (k, v) for k, v in STATUS_RU.items())


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
            await update.effective_message.reply_text("Эта команда только для рекрутера.")
            return
        return await fn(update, context)
    return wrapper


def split_text(text, limit=4000):
    """Лимит Telegram 4096 символов: делит текст на части по границам строк."""
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:  # одна очень длинная строка
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
    """Отправляет запись кандидата в Google Таблицу (если задан SHEETS_URL). Бота не останавливает."""
    if not sheets.enabled():
        return
    row = store.get(cid)
    if row:
        await asyncio.to_thread(sheets.push_row, dict(row))


def status_markup(cid, with_profile=False):
    rows = []
    if with_profile:
        rows.append([InlineKeyboardButton("Полный профиль", callback_data="p:%d" % cid),
                     InlineKeyboardButton("📄 PDF", callback_data="f:%d" % cid)])
    rows.append([InlineKeyboardButton("📞 Созвон", callback_data="s:%d:sozvon" % cid),
                 InlineKeyboardButton("⭐ Резерв", callback_data="s:%d:zaxira" % cid),
                 InlineKeyboardButton("❌ Отказ", callback_data="s:%d:rad" % cid)])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------- сторона кандидата
def lang_of(st):
    return i18n.lang_ok(st.get("lang"))


def next_index(answers, start, step=1):
    """Ближайший вопрос, который относится к кандидату, начиная с start в направлении step. None, если нет."""
    j = start
    while 0 <= j < len(QUESTIONS):
        if applies(QUESTIONS[j], answers):
            return j
        j += step
    return None


async def send_question(chat_id, context):
    st = context.user_data
    lang, a = lang_of(st), st["answers"]
    q = QUESTIONS[st["i"]]
    if q.get("block"):
        await context.bot.send_message(chat_id, "— %s —" % i18n.block(q["block"], lang))
    active = [n for n, x in enumerate(QUESTIONS) if applies(x, a)]
    num = active.index(st["i"]) + 1 if st["i"] in active else st["i"] + 1
    text = "(%d/%d) %s" % (num, len(active), i18n.q_text(q["key"], lang, a.get("position_i", 0)))
    markup = None
    if q["type"] == "choice":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(o, callback_data="a:%d:%d" % (st["i"], n))]
                                       for n, o in enumerate(i18n.q_options(q["key"], lang, a.get("position_i", 0)))])
    await context.bot.send_message(chat_id, text, reply_markup=markup)


async def begin(update, context):
    context.user_data.clear()
    context.user_data.update({"i": -2, "answers": {}, "lang": "uz"})
    markup = InlineKeyboardMarkup([[InlineKeyboardButton(i18n.LANG_FLAGS[l] + " " + i18n.LANG_NAMES[l], callback_data="l:" + l)] for l in i18n.LANGS])
    await update.effective_message.reply_text(i18n.ui("choose_lang", "uz"), reply_markup=markup)


async def send_greeting(message, lang):
    rows = []
    if WEBAPP_URL:
        url = WEBAPP_URL + ("&" if "?" in WEBAPP_URL else "?") + "lang=" + lang
        rows.append([InlineKeyboardButton(i18n.ui("btn_web", lang), web_app=WebAppInfo(url=url))])
    rows.append([InlineKeyboardButton(i18n.ui("btn_chat", lang), callback_data="go")])
    await message.reply_text(i18n.greeting(lang, JOB["company"]), reply_markup=InlineKeyboardMarkup(rows))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rec(update):
        await update.effective_message.reply_text(HELP)
        return
    await begin(update, context)


async def anketa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await begin(update, context)


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data
    prev = next_index(st["answers"], st["i"] - 1, -1) if st.get("i", -1) > 0 else None
    if prev is None:
        await update.effective_message.reply_text(i18n.ui("no_back", lang_of(st)))
        return
    st["i"] = prev
    await send_question(update.effective_chat.id, context)


async def advance(chat_id, context, user):
    st = context.user_data
    nxt = next_index(st["answers"], st["i"] + 1)
    if nxt is None:
        await finish(chat_id, context, user)
    else:
        st["i"] = nxt
        await send_question(chat_id, context)


async def publish(bot, user_id, username, a, photo=None):
    """Оценивает ответы, сохраняет в базу, отправляет рекрутерам карточку (с селфи) и пишет в таблицу."""
    ev = evaluate(a)
    code = verdict_code(ev["verdict"])
    red = sum(1 for f in ev["flags"] if f[0] == "🔴")
    yellow = sum(1 for f in ev["flags"] if f[0] == "🟡")
    flags = " | ".join(f[1] for f in ev["flags"])
    cid = store.save(user_id, username or "", json.dumps(a, ensure_ascii=False), a.get("fio", ""),
                     a.get("phone", ""), ev["pct"], code, red, yellow, flags)
    card = ("🆕 Новый кандидат #%d · %s\n%s, %s лет, %s\n%s %d%%  %s\n🔴 %d   🟡 %d"
            % (cid, position_name(a), a.get("fio", "-"), a.get("age", "-"), a.get("phone", "-"),
               EMOJI[code], ev["pct"], VERDICT_RU[code], red, yellow))
    top = [f for f in ev["flags"] if f[0] == "🔴"][:3] or ev["flags"][:2]
    for lvl, text, _c in top:  # главные риски сразу в уведомлении
        card += "\n%s %s" % (lvl, text if len(text) <= 110 else text[:107] + "...")
    card += "\n/n_%d - полный профиль" % cid
    markup = status_markup(cid, with_profile=True)
    photo_ref = photo  # первому рекрутеру байты, остальным file_id Telegram
    for rid in sorted(RECRUITERS):
        try:
            if photo_ref is not None:
                msg = await bot.send_photo(rid, photo_ref, caption=card[:1024], reply_markup=markup)
                if isinstance(photo_ref, (bytes, bytearray)) and getattr(msg, "photo", None):
                    photo_ref = msg.photo[-1].file_id
                    store.set_photo(cid, photo_ref)
            else:
                await bot.send_message(rid, card, reply_markup=markup)
        except Exception:  # рекрутер мог заблокировать бота
            log.exception("Не удалось отправить рекрутеру: %s", rid)
    await sync_sheet(cid)
    return cid


async def finish(chat_id, context, user):
    st = context.user_data
    lang = lang_of(st)
    a = clean_answers(dict(st["answers"]))
    a["ui_lang"] = lang
    context.user_data.clear()
    await context.bot.send_message(chat_id, i18n.ui("thanks", lang))
    await publish(context.bot, user.id, user.username, a)


async def accept_web(bot, user, answers, photo):
    """Анкета из Mini App (уже проверена в webapi)."""
    await publish(bot, user["id"], user.get("username"), answers, photo)
    try:
        await bot.send_message(user["id"], i18n.ui("thanks", answers.get("ui_lang")))
    except Exception:
        log.exception("Не удалось ответить кандидату")


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cq = update.callback_query
    data = cq.data or ""
    if data.startswith(("p:", "s:", "f:", "m:")):
        await rec_button(update, context)
        return
    await cq.answer()
    st = context.user_data
    if "i" not in st:
        await cq.message.reply_text(i18n.ui("press_start", "uz"))
        return
    if data.startswith("l:"):
        if st["i"] <= -1:  # язык выбирается до начала анкеты
            st["lang"] = i18n.lang_ok(data[2:])
            st["i"] = -1
            await send_greeting(cq.message, st["lang"])
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
    if qi != st["i"] or not 0 <= qi < len(QUESTIONS):  # нажата старая кнопка
        return
    q = QUESTIONS[qi]
    if q["type"] != "choice" or n >= len(q["options"]):
        return
    st["answers"][q["key"]] = q["options"][n]   # в базе вариант хранится по-русски (для рекрутера)
    st["answers"][q["key"] + "_i"] = n
    await advance(cq.message.chat_id, context, cq.from_user)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = context.user_data
    msg = update.effective_message
    lang = lang_of(st)
    if "i" not in st or st["i"] < 0:
        await msg.reply_text(i18n.ui("press_start", lang))
        return
    q = QUESTIONS[st["i"]]
    if q["type"] == "choice":
        await msg.reply_text(i18n.ui("use_buttons", lang))
        return
    text = (msg.text or "").strip()
    digits = re.sub(r"\D", "", text)
    if q["type"] == "number" and not digits:
        await msg.reply_text(i18n.ui("need_number", lang))
        return
    if q["key"] == "phone" and not 9 <= len(digits) <= 12:
        await msg.reply_text(i18n.ui("bad_phone", lang))
        return
    if q["key"] == "age" and not 14 <= int(digits[:3]) <= 80:
        await msg.reply_text(i18n.ui("bad_age", lang))
        return
    st["answers"][q["key"]] = text[:1500]
    await advance(update.effective_chat.id, context, update.effective_user)


# ---------------------------------------------------------------- сторона рекрутера
async def send_profile(bot, chat_id, cid):
    row = store.get(cid)
    if not row:
        await bot.send_message(chat_id, "Кандидат #%d не найден." % cid)
        return
    text = build_profile(json.loads(row["answers"]), row["ts"])
    text += "\n\nTelegram: %s\nСтатус: %s\n#%d" % (("@" + row["username"]) if row["username"] else "-",
                                                 STATUS_RU.get(row["status"], row["status"]), cid)
    if row["photo_file_id"]:
        try:
            await bot.send_photo(chat_id, row["photo_file_id"], caption="#%d %s" % (cid, row["fio"] or ""))
        except Exception:
            log.exception("Не удалось отправить селфи")
    await send_long(bot, chat_id, text, markup=status_markup(cid))


async def send_pdf(bot, chat_id, cid):
    """Отправляет рекрутеру анкету кандидата файлом PDF (с селфи, если оно есть)."""
    row = store.get(cid)
    if not row:
        await bot.send_message(chat_id, "Кандидат #%d не найден." % cid)
        return
    try:
        import pdfgen
        a = json.loads(row["answers"])
        photo = None
        if row["photo_file_id"]:
            try:
                f = await bot.get_file(row["photo_file_id"])
                photo = bytes(await f.download_as_bytearray())
            except Exception:
                log.exception("Не удалось скачать селфи для PDF")
        raw = await asyncio.to_thread(pdfgen.make_pdf, a, row["ts"], cid, STATUS_RU.get(row["status"], row["status"]),
                                      row["username"] or "", row["branch"] or "", photo)
        await bot.send_document(chat_id, document=raw, filename=pdfgen.filename(a, cid), caption="Анкета #%d" % cid)
    except Exception:
        log.exception("Не удалось собрать PDF")
        await bot.send_message(chat_id, "Не удалось собрать PDF для #%d." % cid)


@only_rec
async def pdf_cmd(update, context):
    m = re.match(r"^/pdf_(\d+)", update.effective_message.text or "")
    if m:
        await send_pdf(context.bot, update.effective_chat.id, int(m.group(1)))


async def send_notice(bot, tg_id, text):
    """Сообщение кандидату. True, если доставлено (кандидат мог заблокировать бота)."""
    try:
        await bot.send_message(tg_id, text)
        return True
    except Exception:
        log.warning("Сообщение кандидату %s не доставлено", tg_id, exc_info=True)
        return False


async def propose_move(message, context, cid, stage, fields):
    """Показывает рекрутеру, что уйдёт кандидату, и просит подтвердить. Сам этап здесь не меняется."""
    row = store.get(cid)
    if not row or stage not in store.STATUSES:
        await message.reply_text("Кандидат или этап указан неверно.")
        return
    if row["status"] == stage:
        await message.reply_text("#%d уже на этапе «%s»." % (cid, notices.STAGE_RU[stage]))
        return
    fields, missing = notices.clean_fields(stage, fields)
    head = "#%d %s: %s → %s" % (cid, row["fio"] or "-", notices.STAGE_RU.get(row["status"], row["status"]), notices.STAGE_RU[stage])
    text = notices.build_text(dict(row), stage, fields)
    context.user_data["mv"] = {"cid": cid, "stage": stage, "fields": fields}
    if not text:   # возврат в «Новые»: сообщения нет
        kb = [[InlineKeyboardButton("Переместить", callback_data="m:%d:%s:0" % (cid, stage)),
               InlineKeyboardButton("Отмена", callback_data="m:%d:%s:x" % (cid, stage))]]
        await message.reply_text(head, reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = [[InlineKeyboardButton("Без сообщения", callback_data="m:%d:%s:0" % (cid, stage)),
           InlineKeyboardButton("Отмена", callback_data="m:%d:%s:x" % (cid, stage))]]
    if missing:
        example = {"sobes": "/holat %d sobes 15.11.2026; 14:00; адрес", "staj": "/holat %d staj 20.11.2026; адрес"}.get(stage, "/holat %d " + stage) % cid
        body = "Чтобы отправить кандидату сообщение, укажите: %s.\nНапример: %s" % (
            ", ".join(notices.FIELD_RU[k].lower() for k in missing), example)
    else:
        kb.insert(0, [InlineKeyboardButton("✉️ Отправить и переместить", callback_data="m:%d:%s:1" % (cid, stage))])
        body = "Сообщение кандидату:\n\n%s" % text
    await message.reply_text(head + "\n\n" + body, reply_markup=InlineKeyboardMarkup(kb))


async def do_move(message, context, cid, stage, notify, by):
    row = store.get(cid)
    if not row or stage not in store.STATUSES:
        await message.reply_text("Кандидат или этап указан неверно.")
        return
    if row["status"] == stage:   # повторное нажатие: второе сообщение кандидату не уходит
        await message.reply_text("#%d уже на этапе «%s»." % (cid, notices.STAGE_RU[stage]))
        return
    mv = context.user_data.pop("mv", None) or {}
    fields, missing = notices.clean_fields(stage, mv.get("fields") if mv.get("cid") == cid and mv.get("stage") == stage else {})
    text = notices.build_text(dict(row), stage, fields)
    delivered = None
    if notify:
        if not text or missing:
            await message.reply_text("Не хватает данных для сообщения. Повторите команду /holat с датой, временем и адресом.")
            return
        delivered = await send_notice(context.bot, row["tg_id"], text)
    store.set_status(cid, stage, by="tg:%s" % by, notified=delivered, note="; ".join(v for v in fields.values() if v))
    tail = {True: "Сообщение кандидату доставлено.", False: "Сообщение НЕ доставлено (кандидат мог заблокировать бота). Свяжитесь по телефону %s." % (row["phone"] or ""),
            None: "Сообщение кандидату не отправлялось."}[delivered]
    await message.reply_text("#%d этап: %s. %s" % (cid, notices.STAGE_RU[stage], tail))
    await sync_sheet(cid)


async def rec_button(update, context):
    cq = update.callback_query
    if not is_rec(update):
        await cq.answer("Нет доступа", show_alert=True)
        return
    await cq.answer()
    parts = cq.data.split(":")
    if parts[0] == "p" and len(parts) == 2 and parts[1].isdigit():
        await send_profile(context.bot, cq.message.chat_id, int(parts[1]))
    elif parts[0] == "f" and len(parts) == 2 and parts[1].isdigit():
        await send_pdf(context.bot, cq.message.chat_id, int(parts[1]))
    elif parts[0] == "s" and len(parts) == 3 and parts[1].isdigit():
        await propose_move(cq.message, context, int(parts[1]), parts[2], {})
    elif parts[0] == "m" and len(parts) == 4 and parts[1].isdigit():
        if parts[3] == "x":
            context.user_data.pop("mv", None)
            await cq.message.reply_text("Отменено, этап не изменён.")
        else:
            await do_move(cq.message, context, int(parts[1]), parts[2], parts[3] == "1", update.effective_user.id)


def row_pos(r):
    try:
        return json.loads(r["answers"] or "{}").get("position_i", 0)
    except (ValueError, TypeError):
        return 0


def row_line(r):
    return "%d. %s %s (%s) - %d%% (🔴%d 🟡%d) %s | %s /n_%d" % (
        r["id"], EMOJI.get(r["verdict"], ""), r["fio"] or "-", ["Консультант", "Кассир"][row_pos(r) if row_pos(r) in (0, 1) else 0],
        r["pct"], r["red"], r["yellow"], STATUS_RU.get(r["status"], r["status"]),
        VERDICT_RU.get(r["verdict"], r["verdict"]), r["id"])


async def list_reply(update, context, rows, title):
    if not rows:
        await update.effective_message.reply_text("Кандидатов пока нет.")
        return
    await send_long(context.bot, update.effective_chat.id, title + "\n\n" + "\n".join(row_line(r) for r in rows))


@only_rec
async def reyting(update, context):
    args = [x.lower() for x in (context.args or [])]
    verdict = next((VERDICT_ARGS[x] for x in args if x in VERDICT_ARGS), None)
    pos = next((POS_ARGS[x] for x in args if x in POS_ARGS), None)
    rows = store.listing(verdict=verdict, limit=20 if pos is None else 500)
    title = "Рейтинг по баллу"
    if pos is not None:
        rows = [r for r in rows if row_pos(r) == pos][:20]
        title += ", " + ["консультанты", "кассиры"][pos]
    if verdict:
        title += ": " + VERDICT_RU[verdict]
    await list_reply(update, context, rows, title)


@only_rec
async def songgi(update, context):
    await list_reply(update, context, store.listing(newest=True, limit=15), "Последние анкеты")


@only_rec
async def stat(update, context):
    by_v, by_s = store.stats()
    lines = ["Всего кандидатов: %d" % sum(by_v.values()), ""]
    lines += ["%s %s: %d" % (EMOJI[k], VERDICT_RU[k], by_v.get(k, 0)) for k in ("QABUL", "ZAXIRA", "RAD")]
    lines += ["", "Статусы: " + ", ".join("%s %d" % (STATUS_RU[k], by_s.get(k, 0)) for k in store.STATUSES)]
    await update.effective_message.reply_text("\n".join(lines))


@only_rec
async def otchet(update, context):
    """Отчёт для руководства в Excel: /otchet (текущий месяц) или /otchet 30 (последние N дней)."""
    import datetime
    import report
    d_from, d_to = report.default_period()
    if context.args and context.args[0].isdigit() and 1 <= int(context.args[0]) <= 1000:
        d_from = d_to - datetime.timedelta(days=int(context.args[0]) - 1)
    try:
        raw = await asyncio.to_thread(report.make_xlsx, d_from, d_to)
    except Exception:
        log.exception("Не удалось собрать отчёт")
        await update.effective_message.reply_text("Не удалось собрать отчёт.")
        return
    await update.effective_message.reply_document(document=raw, filename=report.filename(d_from, d_to),
                                                  caption="Отчёт по подбору: %s – %s" % (d_from.strftime("%d.%m.%Y"), d_to.strftime("%d.%m.%Y")))


@only_rec
async def csv_export(update, context):
    await update.effective_message.reply_document(document=store.export_csv(), filename="kandidaty.csv")


@only_rec
async def nomzod(update, context):
    if not context.args or not context.args[0].isdigit():
        await update.effective_message.reply_text("Например: /nomzod 12")
        return
    await send_profile(context.bot, update.effective_chat.id, int(context.args[0]))


@only_rec
async def open_profile(update, context):
    m = re.match(r"^/n_(\d+)", update.effective_message.text or "")
    if m:
        await send_profile(context.bot, update.effective_chat.id, int(m.group(1)))


@only_rec
async def holat(update, context):
    hint = ("Например: /holat 12 sozvon\nСобеседование: /holat 12 sobes 15.11.2026; 14:00; адрес\nСтажировка: /holat 12 staj 20.11.2026; адрес\n"
            "Этапы: " + ", ".join("%s (%s)" % (k, v) for k, v in STATUS_RU.items()))
    args = context.args or []
    stage = notices.parse_stage(args[1]) if len(args) >= 2 else None
    if len(args) < 2 or not args[0].isdigit() or not stage:
        await update.effective_message.reply_text(hint)
        return
    parts = [x.strip() for x in " ".join(args[2:]).split(";") if x.strip()]
    fields = {}
    if stage == "sobes" and len(parts) >= 3:
        fields = {"date": parts[0], "time": parts[1], "place": "; ".join(parts[2:])}
    elif stage == "staj" and len(parts) >= 3:
        fields = {"date": parts[0], "time": parts[1], "place": "; ".join(parts[2:])}
    elif stage == "staj" and len(parts) == 2:
        fields = {"date": parts[0], "place": parts[1]}
    elif stage == "sozvon" and parts:
        fields = {"time": parts[0]}
    elif stage == "offer" and parts:
        fields = {"date": parts[0]}
    await propose_move(update.effective_message, context, int(args[0]), stage, fields)


async def on_error(update, context):
    log.error("Ошибка", exc_info=context.error)


def main():
    if not TOKEN:
        raise SystemExit("Не задан BOT_TOKEN.")
    if not RECRUITERS:
        log.warning("RECRUITER_IDS пуст: карточки кандидатов никому не будут отправлены!")
    store.init()

    async def post_init(application):
        port = int(os.environ.get("PORT", "8080"))
        loop = asyncio.get_running_loop()
        dash = dashboard.Dashboard(
            TOKEN, on_change=lambda cid: asyncio.run_coroutine_threadsafe(sync_sheet(cid), loop),
            notify=lambda tg_id, text: asyncio.run_coroutine_threadsafe(send_notice(application.bot, tg_id, text), loop).result(timeout=25))
        if not dash.enabled:
            log.warning("Веб-панель выключена: задайте DASHBOARD_PASSWORD (не короче 8 символов).")
        webapi.start_server(loop, lambda user, answers, photo: accept_web(application.bot, user, answers, photo),
                            TOKEN, port, os.environ.get("WEBAPP_ORIGIN", ""), dash=dash)
        if not WEBAPP_URL:
            log.warning("WEBAPP_URL пуст: кнопка Mini App не показывается (только режим чата).")

    persistence = PicklePersistence(filepath=os.environ.get("STATE_PATH") or os.path.join(store.data_dir(), "state.pkl"))
    app = Application.builder().token(TOKEN).persistence(persistence).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("anketa", anketa))
    app.add_handler(CommandHandler("orqaga", back))
    app.add_handler(CommandHandler("reyting", reyting))
    app.add_handler(CommandHandler("songgi", songgi))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("csv", csv_export))
    app.add_handler(CommandHandler("otchet", otchet))
    app.add_handler(CommandHandler("nomzod", nomzod))
    app.add_handler(CommandHandler("holat", holat))
    app.add_handler(MessageHandler(filters.Regex(r"^/n_\d+"), open_profile))
    app.add_handler(MessageHandler(filters.Regex(r"^/pdf_\d+"), pdf_cmd))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)
    app.run_polling()


if __name__ == "__main__":
    main()
