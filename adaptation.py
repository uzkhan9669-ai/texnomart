"""Адаптация нового сотрудника: чек-лист на 3 месяца (продавец и кассир), рассылка в боте и отметки.

Источник пунктов: «Чек-лист для нового сотрудника» (Приложения № 6 и № 7). Русский текст из них,
узбекский и английский переведены. Порядок блоков и номера пунктов в базе менять нельзя: отметки хранятся по id пункта.

Как работает:
- сотрудник попадает в адаптацию, когда его переводят на этап «Принят» (ishda); день 1 = первый рабочий день;
- сразу после приёма (или в 9:00 первого рабочего дня, если он позже) бот присылает чек-лист, сотрудник нажимает номер пункта;
- в последний день этапа в 15:00 бот напоминает о неотмеченном; через 1 и 3 дня после срока ещё раз, а рекрутер получает «просрочено»;
- на 7-й день в 15:00 опрос «Как прошла первая неделя?», после 3 месяцев рекрутер отмечает итог в панели.
Сотруднику бот пишет только с 9:00 до 18:00 по Ташкенту.
Модуль ничего не отправляет сам: plan() возвращает список сообщений, бот их отправляет и вызывает mark().
"""
import datetime
import json

import i18n
import store

TZ = datetime.timezone(datetime.timedelta(hours=5))   # Ташкент, без перехода на летнее время
SEND_HOUR, REMIND_HOUR, QUIET_HOUR = 9, 15, 18          # сотруднику пишем только с 9:00 до 18:00; напоминание в последний день этапа в 15:00
LATE_DAYS = (1, 3)                                       # через сколько дней после срока напомнить сотруднику о неотмеченном
TOTAL_DAYS = 91                                          # 3 месяца
SURVEY_DAY = 6                                           # 7-й день (счёт с нуля)

# Блоки: ключ, название, день отправки и последний день (счёт с нуля от первого рабочего дня)
BLOCKS = [
    ("staj", {"ru": "Этап стажировки", "uz": "Stajirovka bosqichi", "en": "Internship stage"}, 0, 0),
    ("d1", {"ru": "1-й рабочий день", "uz": "1-ish kuni", "en": "First working day"}, 0, 1),
    ("w1", {"ru": "1-я рабочая неделя", "uz": "1-ish haftasi", "en": "First working week"}, 1, 6),
    ("m1", {"ru": "Конец 1-го месяца испытательного срока", "uz": "Sinov muddatining 1-oyi oxiri", "en": "End of month 1 of probation"}, 26, 34),
    ("m2", {"ru": "Конец 2-го месяца испытательного срока", "uz": "Sinov muddatining 2-oyi oxiri", "en": "End of month 2 of probation"}, 55, 61),
    ("m3", {"ru": "Конец 3-го месяца испытательного срока", "uz": "Sinov muddatining 3-oyi oxiri", "en": "End of month 3 of probation"}, 84, 90),
]
BLOCK = {b[0]: b for b in BLOCKS}
OWNER = {"HR": {"ru": "HR", "uz": "HR", "en": "HR"}, "IT": {"ru": "IT", "uz": "IT", "en": "IT"},
         "MENTOR": {"ru": "наставник", "uz": "murabbiy", "en": "mentor"}}
OWNER_RU = {"HR": "HR", "IT": "IT", "MENTOR": "Наставник"}


def _t(ru, uz, en):
    return {"ru": ru, "uz": uz, "en": en}


# Общие пункты (одинаковые у продавца и кассира)
DOCS = _t("Оформление и подписание документов на приём", "Ishga qabul hujjatlarini rasmiylashtirish va imzolash",
          "Preparing and signing the employment documents")
TEAM = _t("Знакомство с командой магазина", "Do'kon jamoasi bilan tanishish", "Meeting the store team")
SCHEDULE = _t("Ознакомление с графиком работы", "Ish jadvali bilan tanishish", "Getting to know the work schedule")
ACCOUNTS_1C = _t("Открытие учётных записей в 1С и Broker", "1C va Broker'da hisob ochish", "Opening accounts in 1C and Broker")
BONUS = _t("Ознакомление с приказом о бонусных схемах и ЛУН (лист учёта нарушений): Bitrix, база знаний",
           "Bonus tizimlari va LUN (qoidabuzarliklar hisobi varaqasi) to'g'risidagi buyruq bilan tanishish: Bitrix, bilimlar bazasi",
           "Reading the order on bonus schemes and the violations record sheet (LUN): Bitrix, knowledge base")
SOCIAL = _t("Подписка на соцсети компании (texnomart_careers)", "Kompaniyaning ijtimoiy tarmoqlariga obuna bo'lish (texnomart_careers)",
            "Following the company's social media (texnomart_careers)")
GUIDE = _t("Изучить TexnoGuide в базе знаний", "Bilimlar bazasida TexnoGuide bilan tanishish", "Reading TexnoGuide in the knowledge base")
MENTOR_START = _t("Начало работы с наставником для ввода в работу", "Ishga kirishish uchun murabbiy bilan ishlashni boshlash",
                  "Starting work with your mentor")
SAFETY = _t("Инструктаж по охране труда и технике безопасности", "Mehnat muhofazasi va texnika xavfsizligi bo'yicha yo'riqnomadan o'tish",
            "Occupational health and safety briefing")
WELCOME_ONLINE = _t("Онлайн Welcome-тренинг", "Onlayn Welcome-treningda qatnashish", "Online Welcome training")
BOSS = _t("Индивидуальная встреча с непосредственным руководителем", "Bevosita rahbar bilan yakkama-yakka uchrashuv",
          "One-to-one meeting with your line manager")
BUDDY_CALL = _t("Звонок TexnoBuddy", "TexnoBuddy qo'ng'irog'i", "Call with your TexnoBuddy")
SURVEY30 = _t("Опрос адаптации на 30-й рабочий день", "30-ish kunida moslashuv so'rovnomasidan o'tish", "Adaptation survey on working day 30")
ZOOM_BUDDY = _t("Zoom-встреча с руководителем и TexnoBuddy", "Rahbar va TexnoBuddy bilan Zoom-uchrashuv", "Zoom meeting with your manager and TexnoBuddy")
ZOOM_HR_BOSS = _t("Zoom-встреча с руководителем и HR", "Rahbar va HR bilan Zoom-uchrashuv", "Zoom meeting with your manager and HR")
ZOOM_HR = _t("Zoom-встреча с HR", "HR bilan Zoom-uchrashuv", "Zoom meeting with HR")
WELCOME_PACK = _t("Welcome-тренинг и получение Welcome pack", "Welcome-treningda qatnashish va Welcome pack olish",
                  "Welcome training and receiving the Welcome pack")
FINAL_FORM = _t("Онлайн-опросник о прохождении испытательного срока", "Sinov muddati bo'yicha onlayn so'rovnomani to'ldirish",
                "Online questionnaire about your probation period")

# Чек-листы: блок -> [(владелец, текст)]. Владелец показывается подсказкой: кто помогает выполнить пункт.
SELLER = {
    "staj": [("MENTOR", _t("Стажировка в магазине (до 3 дней): знакомство с командой магазина",
                           "Do'konda stajirovka (3 kungacha): do'kon jamoasi bilan tanishish",
                           "Internship in the store (up to 3 days): meeting the store team")),
             ("", SCHEDULE),
             ("", _t("Правила поведения: одежда и внешний вид, общение с клиентами, конфиденциальность, работа в команде",
                     "Xulq-atvor qoidalari: kiyim va tashqi ko'rinish, mijozlar bilan muloqot, maxfiylik, jamoada ishlash",
                     "Code of conduct: dress and appearance, communication with customers, confidentiality, teamwork"))],
    "d1": [("HR", DOCS),
           ("HR", _t("Ознакомление с должностной инструкцией, политиками и процедурами компании, добавление Face ID",
                     "Lavozim yo'riqnomasi, kompaniya siyosati va tartiblari bilan tanishish, Face ID'ga qo'shilish",
                     "Reading the job description, company policies and procedures; Face ID registration")),
           ("HR", _t("Открытие учётной записи в iSpring", "iSpring'da hisob ochish", "Opening an iSpring account")),
           ("IT", _t("Доступ в Bitrix", "Bitrix tizimiga kirish huquqini olish", "Access to Bitrix")),
           ("", BONUS),
           ("", ACCOUNTS_1C)],
    "w1": [("", SOCIAL), ("", GUIDE), ("", MENTOR_START), ("", SAFETY), ("", WELCOME_ONLINE),
           ("", _t("Начало 24-дневного обучения по товарам и продажам", "Mahsulotlar va savdo bo'yicha 24 kunlik o'qishni boshlash",
                   "Starting the 24-day product and sales training")),
           ("", BOSS), ("", BUDDY_CALL)],
    "m1": [("", _t("Тестирование после 24 дней обучения", "24 kunlik o'qishdan keyin test topshirish", "Test after the 24-day training")),
           ("", SURVEY30), ("", ZOOM_BUDDY)],
    "m2": [("", ZOOM_HR_BOSS)],
    "m3": [("HR", _t("Аттестация", "Attestatsiyadan o'tish", "Certification")), ("", ZOOM_HR), ("", WELCOME_PACK), ("", FINAL_FORM)],
}
CASHIER = {
    "staj": [("MENTOR", _t("Обучение в магазине: правила и сервис, кассовые проводки", "Do'konda o'qish: qoidalar va xizmat ko'rsatish, kassa operatsiyalari",
                           "Training in the store: rules and service, cash transactions")),
             ("HR", _t("Открытие учебной записи в iSpring", "iSpring'da o'quv hisobini ochish", "Opening a training account in iSpring")),
             ("MENTOR", _t("Стажировка в магазине (до 2 дней): знакомство с командой магазина",
                           "Do'konda stajirovka (2 kungacha): do'kon jamoasi bilan tanishish",
                           "Internship in the store (up to 2 days): meeting the store team")),
             ("", SCHEDULE),
             ("", _t("Правила поведения: одежда и внешний вид, общение, кассовые операции, конфиденциальность, работа в команде",
                     "Xulq-atvor qoidalari: kiyim va tashqi ko'rinish, muloqot, kassa operatsiyalari, maxfiylik, jamoada ishlash",
                     "Code of conduct: dress and appearance, communication, cash operations, confidentiality, teamwork")),
             ("HR", _t("Мини-экзамен на соответствие должности", "Lavozimga moslik bo'yicha mini-imtihon", "Mini exam for the position"))],
    "d1": [("HR", DOCS),
           ("HR", _t("Ознакомление с должностной инструкцией, политиками и процедурами компании",
                     "Lavozim yo'riqnomasi, kompaniya siyosati va tartiblari bilan tanishish",
                     "Reading the job description, company policies and procedures")),
           ("", ACCOUNTS_1C), ("", BONUS),
           ("", _t("Добавление в систему доступа (отпечаток пальца, Face ID) и в Bitrix",
                   "Kirish tizimiga (barmoq izi, Face ID) va Bitrix'ga qo'shilish",
                   "Registration in the access system (fingerprint, Face ID) and in Bitrix"))],
    "w1": [("", _t("Знакомство со всеми коллегами своего отдела", "Bo'limdagi barcha hamkasblar bilan tanishish", "Meeting all colleagues in your department")),
           ("", GUIDE), ("", SOCIAL), ("", MENTOR_START), ("", SAFETY),
           ("", _t("Ознакомление с инструкцией наставника и стажёра", "Murabbiy va stajyor yo'riqnomasi bilan tanishish",
                   "Reading the mentor and trainee guide")),
           ("", WELCOME_ONLINE), ("", BOSS), ("", BUDDY_CALL)],
    "m1": [("", _t("Первая часть экзамена: знания и навыки", "Bilim va ko'nikmalar imtihonining birinchi qismini topshirish",
                   "Exam part 1: knowledge and skills")),
           ("", SURVEY30), ("", ZOOM_BUDDY)],
    "m2": [("", _t("Вторая часть экзамена на соответствие должности", "Lavozimga moslik imtihonining ikkinchi qismini topshirish",
                   "Exam part 2: fitness for the position")),
           ("", ZOOM_HR_BOSS)],
    "m3": [("", ZOOM_HR), ("", WELCOME_PACK), ("", FINAL_FORM)],
}

TEXT = {
    "intro": _t(
        "🌟 Добро пожаловать в команду Texnomart, {name}!\n\nПервые 3 месяца — период адаптации. Это нормально, если:\n"
        "✓ эмоции то вверх, то вниз;\n✓ новой информации очень много;\n✓ вы сравниваете старое и новое место работы.\n\n"
        "Я буду присылать чек-лист по этапам. Когда пункт выполнен, нажмите его номер под сообщением. "
        "Если что-то непонятно, нажмите «❓ Задать вопрос».",
        "🌟 Texnomart jamoasiga xush kelibsiz, {name}!\n\nDastlabki 3 oy — moslashuv davri. Quyidagilar normal holat:\n"
        "✓ kayfiyat goh ko'tarilib, goh tushadi;\n✓ yangi ma'lumot juda ko'p;\n✓ eski va yangi ish joyini solishtirasiz.\n\n"
        "Men sizga bosqichma-bosqich chek-list yuboraman. Band bajarilgach, xabar ostidagi uning raqamini bosing. "
        "Biror narsa tushunarsiz bo'lsa, «❓ Savol berish» tugmasini bosing.",
        "🌟 Welcome to the Texnomart team, {name}!\n\nThe first 3 months are your adaptation period. It is normal if:\n"
        "✓ your mood goes up and down;\n✓ there is a lot of new information;\n✓ you compare your old and new workplace.\n\n"
        "I will send you a checklist step by step. When an item is done, tap its number under the message. "
        "If something is unclear, tap “❓ Ask a question”."),
    "head": _t("📋 {title}", "📋 {title}", "📋 {title}"),
    "due": _t("Срок: до {date}", "Muddat: {date} gacha", "Due: {date}"),
    "hint": _t("Нажмите номер пункта, когда он выполнен.", "Bajarilgan band raqamini bosing.", "Tap the number of an item when it is done."),
    "all_done": _t("🎉 Всё отмечено, спасибо!", "🎉 Hammasi belgilandi, rahmat!", "🎉 All done, thank you!"),
    "remind": _t("⏰ Напоминание: сегодня последний день этапа. Отметьте, что уже сделано.",
                 "⏰ Eslatma: bugun bosqichning oxirgi kuni. Bajarilganlarini belgilang.",
                 "⏰ Reminder: today is the last day of this stage. Please mark what is done."),
    "late": _t("⚠️ Срок этапа прошёл. Отметьте, что уже сделано. Если что-то мешает, нажмите «❓ Задать вопрос».",
               "⚠️ Bosqich muddati o'tdi. Bajarilganlarini belgilang. Biror narsa xalaqit bersa, «❓ Savol berish» ni bosing.",
               "⚠️ The deadline for this stage has passed. Please mark what is done. If something is in the way, tap “❓ Ask a question”."),
    "ask_btn": _t("❓ Задать вопрос", "❓ Savol berish", "❓ Ask a question"),
    "ask": _t("Напишите вопрос одним сообщением. Его получит рекрутер.", "Savolingizni bitta xabarda yozing. Uni rekruter oladi.",
              "Write your question in one message. A recruiter will receive it."),
    "asked": _t("Спасибо! Вопрос передан, вам ответят.", "Rahmat! Savolingiz yuborildi, sizga javob berishadi.",
                "Thank you! Your question has been passed on, you will get an answer."),
    "survey": _t("Как прошла ваша первая неделя в Texnomart? Оцените от 1 (плохо) до 5 (отлично).",
                 "Texnomartdagi birinchi haftangiz qanday o'tdi? 1 (yomon) dan 5 (a'lo) gacha baholang.",
                 "How was your first week at Texnomart? Rate it from 1 (bad) to 5 (excellent)."),
    "hard": _t("Спасибо! Что было самым сложным? Напишите одним сообщением или нажмите «Пропустить».",
               "Rahmat! Eng qiyini nima bo'ldi? Bitta xabarda yozing yoki «O'tkazib yuborish» ni bosing.",
               "Thank you! What was the hardest part? Write it in one message or tap “Skip”."),
    "skip": _t("Пропустить", "O'tkazib yuborish", "Skip"),
    "thanks": _t("Спасибо за ответ!", "Javobingiz uchun rahmat!", "Thank you for your answer!"),
    "reply": _t("✉️ Ответ рекрутера:\n{text}", "✉️ Rekruter javobi:\n{text}", "✉️ Reply from the recruiter:\n{text}"),
    "not_yours": _t("Этот чек-лист не ваш.", "Bu chek-list sizniki emas.", "This checklist is not yours."),
    "none": _t("Сейчас открытых пунктов нет.", "Hozircha ochiq bandlar yo'q.", "There are no open items right now."),
}


def tx(key, lang, **kw):
    return TEXT[key][i18n.lang_ok(lang)].format(**kw)


# ------------------------------------------------------------------ данные кандидата
def _answers(row):
    try:
        a = json.loads(row["answers"] or "{}")
        return a if isinstance(a, dict) else {}
    except (TypeError, ValueError):
        return {}


def pos_of(row):
    return 1 if _answers(row).get("position_i") == 1 else 0


def lang_of(row):
    return i18n.lang_ok(_answers(row).get("ui_lang"))


def items(pos):
    """[(id, блок, владелец, тексты)] в порядке чек-листа."""
    plan = CASHIER if pos == 1 else SELLER
    return [("%s.%d" % (b, n + 1), b, owner, text) for b, *_ in BLOCKS for n, (owner, text) in enumerate(plan.get(b, []))]


def block_items(pos, block):
    return [i for i in items(pos) if i[1] == block]


COMPANY = ("HR", "IT")   # эти пункты делает компания: отмечаются автоматически, сотруднику в боте не показываются


def emp_items(pos, block):
    """Пункты, которые отмечает сам сотрудник."""
    return [i for i in block_items(pos, block) if i[2] not in COMPANY]


# ------------------------------------------------------------------ база
def now():
    return datetime.datetime.now(TZ)


def _iso(dt=None):
    return (dt or now()).replace(tzinfo=None).isoformat(timespec="seconds")


def parse_date(s):
    """«15.11.2026» или «2026-11-15» -> date. Иначе None."""
    s = (s or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:10], fmt).date()
        except ValueError:
            pass
    return None


def get(cid):
    return store._run("SELECT * FROM adapt WHERE cid=?", (cid,), "one")


def start(cid, date=None, by="system"):
    """Включает адаптацию (или меняет дату начала, если указана). День 1 = date (по умолчанию сегодня)."""
    d = parse_date(date) if isinstance(date, str) else date
    row = get(cid)
    if row:
        if d:
            store._run("UPDATE adapt SET start=? WHERE cid=?", (d.isoformat(), cid))
            event(cid, "start", d.strftime("%d.%m.%Y"), by)
        if row["state"] != "active" and d:
            store._run("UPDATE adapt SET state='active', reason='', closed=NULL WHERE cid=?", (cid,))
        return
    d = d or now().date()
    store._run("INSERT INTO adapt (cid, start, created) VALUES (?,?,?)", (cid, d.isoformat(), _iso()))
    event(cid, "start", d.strftime("%d.%m.%Y"), by)


def ensure_all():
    """Каждый на этапе «Принят» получает адаптацию; дата начала: день перевода на этап."""
    for r in store._run("SELECT c.id, c.stage_ts, c.ts FROM candidates c LEFT JOIN adapt a ON a.cid=c.id "
                        "WHERE c.status='ishda' AND a.cid IS NULL", (), "all"):
        start(r["id"], parse_date((r["stage_ts"] or r["ts"] or "")[:10]))


def event(cid, kind, text="", by=""):
    store._run("INSERT INTO adapt_event (cid, ts, kind, text, by) VALUES (?,?,?,?,?)", (cid, _iso(), kind, (text or "")[:1500], by or ""))


def events(cid):
    return store._run("SELECT ts, kind, text, by FROM adapt_event WHERE cid=? ORDER BY id", (cid,), "all")


def checks(cid):
    return {r["item"]: dict(r) for r in store._run("SELECT item, ts, by FROM adapt_check WHERE cid=?", (cid,), "all")}


def set_check(cid, item, done, by):
    """Ставит или снимает отметку. Возвращает True, если что-то изменилось."""
    row = store.get(cid)
    if not row or item not in {i[0] for i in items(pos_of(row))}:
        return False
    had = item in checks(cid)
    if done and not had:
        store._run("INSERT INTO adapt_check (cid, item, ts, by) VALUES (?,?,?,?)", (cid, item, _iso(), by))
    elif not done and had:
        store._run("DELETE FROM adapt_check WHERE cid=? AND item=?", (cid, item))
    else:
        return False
    event(cid, "check" if done else "uncheck", item, by)
    if by == "employee":
        store._run("UPDATE adapt SET last_seen=? WHERE cid=?", (_iso(), cid))
    return True


def set_mentor(cid, mentor, by):
    store._run("UPDATE adapt SET mentor=? WHERE cid=?", ((mentor or "").strip()[:80], cid))
    event(cid, "mentor", (mentor or "").strip()[:80], by)


RESULTS = {"active": "Идёт", "done": "Адаптацию прошёл", "left": "Ушёл"}
LEAVE_REASONS = ["Ушёл сам", "Не прошёл аттестацию или экзамен", "Нарушения", "Не вышел на работу", "Другое"]


def finish(cid, result, reason, by):
    if result not in RESULTS:
        return False
    store._run("UPDATE adapt SET state=?, reason=?, closed=? WHERE cid=?",
               (result, (reason or "")[:120] if result == "left" else "", None if result == "active" else _iso(), cid))
    event(cid, "result", RESULTS[result] + (": " + reason if result == "left" and reason else ""), by)
    return True


def set_rating(cid, score):
    store._run("UPDATE adapt SET rating=?, last_seen=? WHERE cid=?", (score, _iso(), cid))
    event(cid, "rating", str(score), "employee")


def first_date(cid, kind):
    r = store._run("SELECT ts FROM adapt_event WHERE cid=? AND kind=? ORDER BY id LIMIT 1", (cid, kind), "one")
    try:
        return datetime.date.fromisoformat(r["ts"][:10]) if r else None
    except ValueError:
        return None


def has(cid, kind):
    return bool(store._run("SELECT 1 FROM adapt_event WHERE cid=? AND kind=? LIMIT 1", (cid, kind), "one"))


# ------------------------------------------------------------------ состояние для панели и бота
def day_of(a, today=None):
    try:
        return ((today or now().date()) - datetime.date.fromisoformat(a["start"])).days
    except (TypeError, ValueError):
        return 0


def due_date(a, block):
    return datetime.date.fromisoformat(a["start"]) + datetime.timedelta(days=BLOCK[block][3])


def view(row, today=None):
    """Всё для карточки кандидата в панели. None, если адаптации нет."""
    a = get(row["id"])
    if not a:
        return None
    today = today or now().date()
    day, done, pos = day_of(a, today), checks(row["id"]), pos_of(row)
    blocks, total, n_done, late, current = [], 0, 0, 0, None
    for key, title, send_day, due_day in BLOCKS:
        its = block_items(pos, key)
        if not its:
            continue
        rows = []
        is_late = a["state"] == "active" and day > due_day
        for iid, _b, owner, text in its:
            d = done.get(iid)
            rows.append({"id": iid, "text": text["ru"], "owner": OWNER_RU.get(owner, ""), "done": bool(d),
                         "by": ({"employee": "сотрудник в боте", "auto": "автоматически"}.get(d["by"], d["by"]) if d else ""), "ts": d["ts"] if d else "",
                         "auto": owner in COMPANY,
                         "late": is_late and not d})
        k_done = sum(1 for r in rows if r["done"])
        total += len(rows)
        n_done += k_done
        late += sum(1 for r in rows if r["late"])
        if current is None and day <= due_day:
            current = title["ru"]
        blocks.append({"key": key, "title": title["ru"], "due": due_date(a, key).strftime("%d.%m.%Y"), "from": send_day + 1, "to": due_day + 1,
                       "open": send_day <= day, "items": rows, "done": k_done, "total": len(rows),
                       "sent": has(row["id"], "sent:" + key)})
    log = []
    for e in events(row["id"]):
        if e["kind"] in ("q", "hard", "reply", "rating", "result", "fail", "start", "mentor") or e["kind"].startswith(("sent:", "remind:", "late:")):
            log.append({"ts": e["ts"], "kind": e["kind"], "text": e["text"], "by": e["by"]})
    return {"start": a["start"], "start_ru": datetime.date.fromisoformat(a["start"]).strftime("%d.%m.%Y"), "day": day + 1, "days": TOTAL_DAYS,
            "mentor": a["mentor"] or "", "state": a["state"], "state_ru": RESULTS.get(a["state"], a["state"]), "reason": a["reason"] or "",
            "rating": a["rating"], "last_seen": a["last_seen"] or "", "done": n_done, "total": total, "late": late,
            "current": current or "Испытательный срок окончен", "blocks": blocks, "log": log[-40:], "reasons": LEAVE_REASONS,
            "failed": has(row["id"], "fail")}


def message(row, block, remind=None):
    """Сообщение блока для сотрудника: (текст, кнопки [[(подпись, данные)]]). remind: None, "remind" (последний день) или "late" (срок прошёл)."""
    a, lang, pos = get(row["id"]), lang_of(row), pos_of(row)
    its, done = emp_items(pos, block), checks(row["id"])
    lines = [tx("late" if remind == "late" else "remind", lang)] if remind else []
    lines += [tx("head", lang, title=BLOCK[block][1][lang]), tx("due", lang, date=due_date(a, block).strftime("%d.%m.%Y")), ""]
    for n, (iid, _b, owner, text) in enumerate(its, 1):
        tag = " (%s)" % OWNER[owner][lang] if owner else ""
        lines.append("%s %d. %s%s" % ("✅" if iid in done else "▫️", n, text[lang], tag))
    all_done = all(i[0] in done for i in its)
    lines += ["", tx("all_done", lang) if all_done else tx("hint", lang)]
    buttons = [("%d %s" % (n, "✅" if iid in done else "☐"), "ad:t:%d:%s" % (row["id"], iid)) for n, (iid, *_r) in enumerate(its, 1)]
    kb = [buttons[k:k + 5] for k in range(0, len(buttons), 5)] + [[(tx("ask_btn", lang), "ad:q:%d" % row["id"])]]
    return "\n".join(lines), kb


def open_blocks(row, today=None):
    """Блоки, которые сейчас идут (для кнопки «Отправить чек-лист» и команды /checklist)."""
    a = get(row["id"])
    if not a:
        return []
    day = day_of(a, today)
    pos, done = pos_of(row), checks(row["id"])
    out = [b[0] for b in BLOCKS if emp_items(pos, b[0]) and b[2] <= day <= b[3]]
    # плюс начавшиеся раньше этапы, где сотрудник ещё не всё отметил
    old = [b[0] for b in BLOCKS if emp_items(pos, b[0]) and b[3] < day and any(i[0] not in done for i in emp_items(pos, b[0]))]
    return old + out


def undone(row, block):
    done = checks(row["id"])
    return [i for i in emp_items(pos_of(row), block) if i[0] not in done]


def auto_fill(row, day):
    """Пункты HR и IT отмечаются сами, когда начинается их этап (если рекрутер не снял отметку вручную)."""
    cid, done, pos = row["id"], checks(row["id"]), pos_of(row)
    for iid, block, owner, _t in items(pos):
        if owner in COMPANY and BLOCK[block][2] <= day and iid not in done and not store._run(
                "SELECT 1 FROM adapt_event WHERE cid=? AND kind='uncheck' AND text=? AND by!='auto' LIMIT 1", (cid, iid), "one"):
            set_check(cid, iid, True, "auto")


def count_today(cid, prefixes, today):
    rows = store._run("SELECT kind FROM adapt_event WHERE cid=? AND ts LIKE ?", (cid, today.isoformat() + "%"), "all")
    return sum(1 for r in rows if r["kind"].startswith(prefixes))


RESET = "2026-11-19"   # перезапуск адаптации для всех (по просьбе владельца): отметки и рассылка с начала, даты и наставники сохраняются


def reset_once():
    store._run("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    if store._run("SELECT 1 FROM meta WHERE key=?", ("adapt_reset", ), "one") and \
            store._run("SELECT value FROM meta WHERE key=?", ("adapt_reset",), "one")["value"] >= RESET:
        return
    for r in store._run("SELECT cid FROM adapt WHERE state='active'", (), "all"):
        store._run("DELETE FROM adapt_check WHERE cid=?", (r["cid"],))
        store._run("DELETE FROM adapt_event WHERE cid=? AND kind NOT IN ('start','mentor','q','hard','reply')", (r["cid"],))
        store._run("UPDATE adapt SET rating=NULL, last_seen=NULL WHERE cid=?", (r["cid"],))
        event(r["cid"], "restart", "", "system")
    store._run("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", ("adapt_reset", RESET))


def find_by_tg(tg_id):
    return store._run("SELECT * FROM candidates WHERE CAST(tg_id AS TEXT)=?", (str(tg_id),), "one")


def who(row):
    pos = ["Консультант", "Кассир"][pos_of(row)]
    return "#%d %s (%s%s)" % (row["id"], row["fio"] or "-", pos, ", " + row["branch"] if row["branch"] else "")


# ------------------------------------------------------------------ расписание
def plan(at=None):
    """Что отправить сейчас. Возвращает список действий:
    {"to": "emp", "cid", "chat", "text", "kb", "key"} сотруднику; {"to": "rec", "cid", "text", "key"} рекрутерам.
    После отправки вызвать mark(cid, key, ok). Вне времени 9:00–18:00 ничего не отправляется."""
    at = at or now()
    if not SEND_HOUR <= at.hour < QUIET_HOUR:
        return []
    reset_once()
    ensure_all()
    out, today = [], at.date()
    rows = store._run("SELECT c.* FROM candidates c JOIN adapt a ON a.cid=c.id WHERE c.status='ishda' AND a.state='active'", (), "all")
    for row in rows:
        a, cid = get(row["id"]), row["id"]
        day, lang = day_of(a, today), lang_of(row)
        if day < 0 or not row["tg_id"]:
            continue
        emp = lambda text, key, kb=None: out.append({"to": "emp", "cid": cid, "chat": row["tg_id"], "text": text, "kb": kb, "key": key})
        if not has(cid, "intro") and day <= 30:
            emp(tx("intro", lang, name=(row["fio"] or "").strip() or "-"), "intro")
        pos = pos_of(row)
        auto_fill(row, day)
        mine = [blk for blk in BLOCKS if emp_items(pos, blk[0])]
        first_contact = not any(has(cid, "sent:" + k) for k, *_r in mine)
        late_emp = count_today(cid, ("late1:", "late3:"), today)   # о просрочке сотруднику не больше одного сообщения в день
        late_rec = []
        for key, title, send_day, due_day in mine:
            sent, just = has(cid, "sent:" + key), False
            if not sent and not has(cid, "skip:" + key):
                # идущий этап присылается сразу; при первом контакте (принят задним числом или перезапуск)
                # приходят и прошедшие этапы, где сотруднику есть что отметить
                if send_day <= day <= due_day or (first_contact and day > due_day and undone(row, key)):
                    text, kb = message(row, key)
                    emp(text, "sent:" + key, kb)
                    sent = just = True
                elif day > due_day:
                    event(cid, "skip:" + key)
            if not sent or just:
                continue
            left = undone(row, key)
            fresh = (first_date(cid, "sent:" + key) or today) >= today   # этап пришёл сегодня: о просрочке напомним не раньше завтра
            if left and day == due_day and at.hour >= REMIND_HOUR and not has(cid, "remind:" + key):
                text, kb = message(row, key, remind="remind")
                emp(text, "remind:" + key, kb)
            for n in LATE_DAYS:   # срок прошёл: напоминание сотруднику через 1 и 3 дня
                if left and not fresh and not late_emp and day >= due_day + n and not has(cid, "late%d:%s" % (n, key)) \
                        and not has(cid, "late%d:%s" % (LATE_DAYS[-1], key)):
                    text, kb = message(row, key, remind="late")
                    emp(text, "late%d:%s" % (n, key), kb)
                    late_emp += 1
                    break
            if left and not fresh and day > due_day and not has(cid, "late:" + key):
                late_rec.append((key, title, left))
        if late_rec:   # рекрутерам одно сообщение на сотрудника, по всем просроченным этапам
            out.append({"to": "rec", "cid": cid, "key": "|".join("late:" + k for k, *_r in late_rec),
                        "text": "⚠️ Адаптация %s: не отмечено в срок.\n%s\nПодробно: /n_%d" % (who(row), "\n".join(
                            "«%s» (срок %s), пунктов: %d\n%s" % (t["ru"], due_date(a, k).strftime("%d.%m.%Y"), len(left),
                                                               "\n".join("• " + i[3]["ru"] for i in left[:6])) for k, t, left in late_rec), cid)})
        if SURVEY_DAY <= day <= SURVEY_DAY + 7 and at.hour >= REMIND_HOUR and not has(cid, "survey"):
            emp(tx("survey", lang), "survey", [[(str(n), "ad:r:%d:%d" % (cid, n)) for n in range(1, 6)]])
        if day >= TOTAL_DAYS and not has(cid, "end"):
            out.append({"to": "rec", "cid": cid, "key": "end",
                        "text": "🏁 %s: 3 месяца адаптации прошли (с %s). Отметьте итог в панели: «Адаптацию прошёл» или «Ушёл»." % (
                            who(row), datetime.date.fromisoformat(a["start"]).strftime("%d.%m.%Y"))})
    return out


def mark(cid, key, ok=True):
    """Записывает, что действие выполнено (даже если сообщение не доставлено: повторно не шлём, в панели видно)."""
    for k in key.split("|"):
        event(cid, k)
    if not ok:
        event(cid, "fail", key)


# ------------------------------------------------------------------ список для панели
def overview(today=None):
    ensure_all()
    out = []
    for r in store._run("SELECT c.* FROM candidates c JOIN adapt a ON a.cid=c.id", (), "all"):
        v = view(r, today)
        a = get(r["id"])
        out.append({"id": r["id"], "fio": r["fio"] or "", "phone": r["phone"] or "", "pos": ["Консультант", "Кассир"][pos_of(r)],
                    "branch": r["branch"] or "", "photo": bool(r["photo_file_id"]), "status": r["status"],
                    "state": a["state"], "start": v["start_ru"], "day": v["day"], "current": v["current"], "done": v["done"],
                    "total": v["total"], "late": v["late"], "rating": v["rating"], "mentor": v["mentor"], "reason": v["reason"],
                    "last_seen": v["last_seen"], "failed": v["failed"], "ts": a["start"],
                    "blocks": [[b["key"], b["done"], b["total"], any(i["late"] for i in b["items"])] for b in v["blocks"]]})
    return out
