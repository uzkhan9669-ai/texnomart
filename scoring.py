"""Анкета, оценка и профиль кандидата: продавец-консультант и кассир, Texnomart.

Тексты вопросов на трёх языках лежат в i18n.py. Всё, что видит рекрутер (флаги, оценки, профиль), на русском.
Условия вакансии: 14 дней обучения; график 6/1, смены 09:00-18:00 и 13:00-22:00; оклад + KPI-бонус.
Перед запуском сверьте блок JOB с реальными условиями (в том числе для кассира).

НЕ влияют на оценку и вердикт: возраст (кроме пометки «младше 18»), семейное положение, дети.
Они показываются рекрутеру отдельным блоком «Анкетные данные».
"""
import datetime
import re

import i18n

JOB = {
    "company": "Texnomart",
    "training": i18n.JOB_TR["training"]["ru"],
    "schedule": i18n.JOB_TR["schedule"]["ru"],
    "income": [x["ru"] for x in i18n.JOB_TR["income_pos"]],   # по должности: консультант, кассир
    "income_max_mln": [8, 5],
}
POSITIONS = i18n.Q["position"]["ru"][1]   # position_i: 0 консультант, 1 кассир
POS_SHORT = ["Консультант", "Кассир"]

# type: text | number | choice. "pos": вопрос только для этой должности. "when": вопрос задаётся только
# после указанного ответа ("i": номер варианта или "in": список номеров). "scores": баллы по вариантам.
# "info": анкетные данные, в оценке не участвуют.
_STUDENT = {"key": "student", "i": 1}
_SPEC = [
    {"key": "position", "block": "b1", "type": "choice", "info": True},
    {"key": "fio", "type": "text"},
    {"key": "age", "type": "number"},
    {"key": "phone", "type": "text"},
    {"key": "district", "type": "text"},
    {"key": "commute", "type": "choice"},
    {"key": "lang", "type": "choice"},
    {"key": "student", "type": "choice"},
    {"key": "study_place", "type": "text", "when": _STUDENT},
    {"key": "course", "type": "choice", "when": _STUDENT},
    {"key": "study_form", "type": "choice", "when": _STUDENT},
    {"key": "marital_status", "type": "choice", "info": True},
    {"key": "children", "type": "choice", "info": True},
    {"key": "children_count", "type": "choice", "info": True, "when": {"key": "children", "i": 1}},
    {"key": "children_ages", "type": "text", "info": True, "when": {"key": "children", "i": 1}},
    {"key": "health", "type": "choice"},
    {"key": "health_note", "type": "text", "when": {"key": "health", "in": [1, 2]}},
    {"key": "schedule", "type": "choice"},
    {"key": "evening", "type": "choice"},
    {"key": "training", "type": "choice"},
    {"key": "start", "type": "choice"},
    {"key": "income", "type": "choice"},
    {"key": "kpi", "pos": 0, "type": "choice"},
    {"key": "pay_fix", "pos": 1, "type": "choice"},
    {"key": "workload", "type": "choice"},
    {"key": "change", "type": "choice"},
    {"key": "exp", "block": "b2", "type": "choice"},
    {"key": "tech_exp", "type": "choice"},
    {"key": "jobs_year", "type": "choice"},
    {"key": "last_job", "type": "text"},
    {"key": "reason", "type": "choice"},
    {"key": "reason_text", "type": "text"},
    {"key": "reference", "type": "choice"},
    {"key": "other_jobs", "type": "choice"},
    {"key": "other_jobs_where", "type": "text", "when": {"key": "other_jobs", "in": [1, 2, 3]}},
    {"key": "calc_change", "block": "b3", "type": "number"},
    {"key": "calc_discount", "type": "number"},
    {"key": "calc_total", "pos": 1, "type": "number"},
    {"key": "cash_shortage", "pos": 1, "type": "text"},
    {"key": "needs", "pos": 0, "type": "text"},
    {"key": "objection", "pos": 0, "type": "text"},
    {"key": "conflict", "block": "b4", "type": "text"},
    {"key": "sjt_cash_honesty", "pos": 1, "type": "choice", "scores": [2, 5, 1, 1]},
    {"key": "sjt_cash_queue", "pos": 1, "type": "choice", "scores": [1, 5, 2, 1]},
    {"key": "sjt_customer", "pos": 0, "type": "choice", "scores": [1, 5, 4, 2]},
    {"key": "sjt_team", "type": "choice", "scores": [1, 5, 3, 3]},
    {"key": "sjt_learn", "type": "choice", "scores": [1, 5, 4, 2]},
    {"key": "sjt_stress", "type": "choice", "scores": [1, 5, 3, 2]},
    {"key": "late", "type": "choice"},
    {"key": "motive", "block": "b5", "type": "choice"},
]
QUESTIONS = []
for _q in _SPEC:
    _q = dict(_q)
    _q["text"] = i18n.q_text(_q["key"], i18n.REC_LANG)          # рекрутерский (русский) текст
    if _q["type"] == "choice":
        _q["options"] = i18n.q_options(_q["key"], i18n.REC_LANG)
    QUESTIONS.append(_q)
QMAP = {q["key"]: q for q in QUESTIONS}


def applies(q, a):
    """Задаётся ли вопрос этому кандидату (должность и условные вопросы). a: уже данные ответы."""
    if "pos" in q and a.get("position_i", 0) != q["pos"]:
        return False
    w = q.get("when")
    if w:
        v = a.get(w["key"] + "_i")
        if ("i" in w and v != w["i"]) or ("in" in w and v not in w["in"]):
            return False
    return True


def clean_answers(a):
    """Убирает ответы на вопросы, которые к кандидату не относятся (например, после смены должности)."""
    out = {}
    for q in QUESTIONS:
        if not applies(q, out):
            continue
        for k in (q["key"], q["key"] + "_i"):
            if k in a:
                out[k] = a[k]
    for k in ("slot", "ui_lang"):
        if k in a:
            out[k] = a[k]
    return out


def _norm(s):
    """Нижний регистр, без апострофов (o'/oʻ/o` пишут по-разному)."""
    return re.sub(r"[ʻʼ’‘`']", "", (s or "").lower())


def _digits(s):
    return re.sub(r"\D", "", s or "")


def _hits(text, groups):
    t = _norm(text)
    return sum(1 for g in groups if any(k in t for k in g))


def _hits_to_score(hits, text):
    if len((text or "").strip()) < 20:
        return 1
    return {0: 1, 1: 2, 2: 3, 3: 4}.get(hits, 5)


# Ключевые слова: узбекский (без апострофов), русский, английский. Кандидат пишет на любом языке.
OBJECTION_GROUPS = [
    ["ehtiyoj", "nima uchun", "kim uchun", "qaysi", "byudjet", "tanlab", "aniqlash", "oila",
     "потребност", "для чего", "для кого", "какой", "бюджет", "подбер", "уточн", "семь",
     "need", "what for", "who is it for", "which", "budget", "family", "choose"],
    ["muddatli", "bolib", "nasiya", "rassrochka", "oyiga", "tolov", "рассрочк", "частями", "в месяц", "платеж", "платёж",
     "installment", "monthly", "in parts", "payment plan"],
    ["muqobil", "variant", "arzonroq", "boshqa model", "analog", "oxshash",
     "альтернатив", "вариант", "аналог", "дешевле", "другую модель", "похож",
     "alternative", "option", "cheaper", "another model", "similar"],
    ["kafolat", "afzallik", "sifat", "foyda", "aksiya", "chegirma", "sovga", "elektr", "energiya",
     "гаранти", "преимуществ", "качеств", "выгод", "акци", "скидк", "подар", "энерго",
     "warranty", "advantage", "quality", "benefit", "promo", "discount", "gift", "energy"],
    ["raqam", "telefon", "bron", "qoldiring", "kontakt", "keling", "qaytib",
     "контакт", "номер", "телефон", "заброни", "зарезерв", "приходите", "вернётесь", "вернетесь",
     "phone number", "contact", "reserve", "hold it", "come back", "leave your"],
]
NEEDS_GROUPS = [
    ["oila", "necha kishi", "kishilik", "семь", "человек", "family", "how many people", "members"],
    ["byudjet", "narx", "qancha", "бюджет", "цена", "сумм", "budget", "price", "how much"],
    ["litr", "hajm", "olcham", "razmer", "размер", "объём", "объем", "литр", "size", "volume", "litre", "liter", "capacity"],
    ["elektr", "energiya", "энерго", "nofrost", "no frost", "morozil", "морозил", "energy", "freezer"],
    ["brend", "model", "marka", "rang", "бренд", "марка", "цвет", "brand", "color", "colour"],
]
CONFLICT_GROUPS = [
    ["tinglay", "xotirjam", "sabr", "gapini", "aniqlay", "выслуш", "спокойно", "не перебив", "уточн",
     "listen", "calm", "patient", "clarify", "ask what"],
    ["uzr", "kechirim", "tushunaman", "afsus", "извин", "понимаю", "сожале", "приношу", "sorry", "apolog", "understand", "regret"],
    ["yechim", "qaytar", "almashtir", "tuzat", "tamir", "kafolat", "servis", "chek", "tekshir",
     "решени", "вернуть", "обмен", "замен", "ремонт", "гаранти", "сервис", "проверим", "проверить", "чек",
     "solution", "refund", "exchange", "replace", "repair", "warranty", "service", "receipt", "check"],
    ["rahbar", "administrator", "katta", "menejer", "boshliq", "руковод", "администратор", "старш", "менеджер", "управляющ",
     "manager", "supervisor", "senior"],
    ["xushmuomala", "hissiyotsiz", "bahslashmayman", "vazmin", "вежлив", "без эмоци", "не спорю", "сохраня",
     "polite", "respectful", "not argue", "stay calm"],
]
CASH_GROUPS = [
    ["rahbar", "administrator", "menejer", "xabar ber", "malum qil", "руковод", "администратор", "менеджер", "сообщ",
     "manager", "supervisor", "report", "inform"],
    ["qayta sana", "qayta hisobla", "tekshir", "chek", "jurnal", "пересчит", "провер", "чек", "журнал", "отчёт", "отчет",
     "recount", "check", "receipt", "audit"],
    ["yashirm", "halol", "ochiq ayt", "не скры", "честно", "открыто", "hide", "honest", "transparent"],
    ["sabab", "kamera", "tahlil", "aniqla", "korib chiq", "причин", "камер", "разбер", "анализ", "выясн",
     "reason", "camera", "cctv", "investigat", "find out", "analy"],
    ["javobgar", "masuliyat", "ответствен", "responsib", "accountab"],
]
OWN_POCKET = ["ozimdan", "ozim to", "oz hisobimdan", "oz cho", "своих", "из своего", "своими деньгами",
              "my own money", "own pocket", "from my pocket", "pay it myself"]

# Вопросы для интервью: код флага -> вопрос
INTERVIEW_BY_CODE = {
    "schedule": "Какие выходные и смены вам неудобны и почему?",
    "evening": "Как вы будете добираться домой после смены до 22:00? Не станет ли это проблемой?",
    "training": "В какие дни 14-дневного обучения вы не сможете прийти и почему?",
    "conflict": "Что именно произошло на прошлом месте работы? Что бы вы сделали иначе?",
    "reference": "Почему вы не хотите, чтобы мы позвонили вашему бывшему руководителю?",
    "turnover": "Сколько вы планируете у нас работать и что должно быть, чтобы вы остались?",
    "income": "Какой доход вам нужен и почему? Насколько вам подходят наши условия оплаты на этой должности?",
    "kpi": "Что вы думаете о системе KPI-бонусов? Что будете делать, если план не выполнен?",
    "workload": "Представьте самый тяжёлый день: касса, приёмка товара и клиенты одновременно. С чего начнёте?",
    "change": "Что вы сделали, когда в последний раз на работе что-то неожиданно изменилось?",
    "lang": "Давайте 1-2 минуты поговорим с «клиентом» на обоих языках.",
    "study": "Какое у вас расписание занятий? В какие дни и часы вы на учёбе и как совместите это с графиком 6/1?",
    "health": "Какие рабочие задачи вам выполнять нельзя или тяжело? Что поможет вам работать полную смену?",
    "other": "В какие компании вы ещё откликались и на каком вы этапе? Что для вас решит выбор в нашу пользу?",
    "cash": "Была ли у вас неприятная ситуация с деньгами в кассе (недостача или излишек)? Что именно вы сделали?",
    "sjt_customer": "Был ли случай, когда вы продали клиенту то, что выгодно вам, а ему не нужно? Как поступили?",
    "sjt_cash_queue": "Вспомните длинную очередь и недовольного клиента. Что вы сказали и сделали?",
    "sjt_team": "Вспомните случай, когда вы помогли коллеге в рабочее время. Вас об этом кто-то просил?",
    "sjt_learn": "Как вы в последний раз осваивали новое на работе? Приведите пример.",
    "sjt_stress": "Опишите самый тяжёлый и срочный рабочий день. С чего вы начали и чем всё закончилось?",
}

SJT_LABELS = {"sjt_customer": "Клиентоориентированность", "sjt_cash_honesty": "Честность и работа с деньгами",
              "sjt_cash_queue": "Общение с клиентом в очереди", "sjt_team": "Работа в команде",
              "sjt_learn": "Обучаемость", "sjt_stress": "Стрессоустойчивость"}
SJT_FLAGS = {
    "sjt_customer": "Может ставить свой бонус выше интереса клиента (риск нечестной продажи)",
    "sjt_cash_honesty": "Может неправильно поступить с излишком в кассе (риск по честности)",
    "sjt_cash_queue": "Не умеет спокойно работать с очередью и торопящимся клиентом",
    "sjt_team": "Не готов(а) помогать коллеге в команде",
    "sjt_learn": "Не готов(а) самостоятельно изучать новый товар или программу",
    "sjt_stress": "Под давлением может действовать неправильно",
}
L_SALES, L_NUM, L_EXP = "Техника продаж (возражение, выявление потребности)", "Счёт (сдача, скидка)", "Опыт в торговле"
L_CASHNUM, L_CASH = "Счёт и касса (сдача, сумма, скидка)", "Работа с недостачей и излишком"
L_COMM, L_CONF, L_RESP = "Коммуникация", "Работа с недовольным клиентом", "Ответственность и дисциплина"
L_STAB, L_MOT = "Стабильность (смена работы, другие отклики)", "Мотивация и KPI"
L_MOT_CASH = "Мотивация и отношение к окладу"
L_ADAPT, L_LANG = "Адаптивность к изменениям", "Языки (узбекский + русский)"
WEIGHTS = {
    L_SALES: 2, L_NUM: 1, L_EXP: 1, L_CASHNUM: 2, L_CASH: 2,
    L_COMM: 1, L_CONF: 1, L_RESP: 1, L_STAB: 1.5, L_MOT: 1, L_MOT_CASH: 1, L_ADAPT: 1, L_LANG: 1.5,
    "Клиентоориентированность": 1.5, "Честность и работа с деньгами": 2, "Общение с клиентом в очереди": 1.5,
    "Работа в команде": 1, "Обучаемость": 1, "Стрессоустойчивость": 1,
}
VERDICT_RU = {"QABUL": "ПРИНЯТЬ", "ZAXIRA": "РЕЗЕРВ", "RAD": "ОТКАЗ"}


def verdict_code(v):
    return "QABUL" if v.startswith("ПРИНЯТЬ") else ("ZAXIRA" if v.startswith("РЕЗЕРВ") else "RAD")


def _clamp(x, lo=1, hi=5):
    return max(lo, min(hi, x))


def evaluate(a):
    """a: словарь ответов. Для вопросов с выбором есть <key>_i (номер варианта)."""
    flags = []  # (уровень, текст, код)

    def red(t, c=None): flags.append(("🔴", t, c))
    def yellow(t, c=None): flags.append(("🟡", t, c))

    i = lambda k: a.get(k + "_i", 0)
    cashier = i("position") == 1

    # --- Соответствие условиям вакансии
    if i("lang") == 2:
        red("Свободно владеет только одним языком, вакансия требует узбекский и русский", "lang")
    elif i("lang") == 1:
        yellow("Один из языков на разговорном уровне, проверить на интервью", "lang")
    if i("schedule") == 2:
        red("График 6/1 с плавающими сменами не подходит", "schedule")
    elif i("schedule") == 1:
        yellow("Не может работать во все выходные, уточнить, какие дни нужны", "schedule")
    if i("evening") == 2:
        red("Не может работать в вечернюю смену (13:00-22:00)", "evening")
    elif i("evening") == 1:
        yellow("Сложно возвращаться домой после вечерней смены, уточнить дорогу", "evening")
    if i("training") == 2:
        red("Не может пройти 14-дневное обучение", "training")
    elif i("training") == 1:
        yellow("Не сможет прийти в некоторые дни обучения", "training")
    if i("workload") == 2:
        red("Не готов(а) к большому объёму работы", "workload")
    elif i("workload") == 1:
        yellow("К большому объёму готов(а), но ждёт условий и помощи", "workload")
    if i("health") == 2:
        red("Сообщил(а), что физические требования работы (на ногах, подъём груза) не подходят", "health")
    elif i("health") == 1:
        yellow("Есть ограничения для работы на ногах или с грузом: уточнить, какие задачи выполнимы", "health")
    if i("change") == 2:
        yellow("Негативно относится к изменениям, проверить адаптивность", "change")
    if not cashier and i("kpi") == 2:
        yellow("Хочет только фиксированный оклад, система KPI-бонусов может не подойти", "kpi")
    if cashier and i("pay_fix") == 2:
        red("Фиксированный оклад кассира (2,5 млн на обучении, затем 5 млн сум) не подходит", "income")
    elif cashier and i("pay_fix") == 1:
        yellow("Оклад кассира подходит, но хочет больше: риск ухода из-за оплаты", "income")
    if i("commute") == 2:
        yellow("Дорога до магазина больше 60 минут: риск опозданий и ухода")
    if i("start") == 2:
        yellow("Сможет выйти на работу позже чем через 2 недели")
    if i("income") >= (2 if cashier else 3):
        yellow("Ожидаемый доход выше, чем даёт вакансия (до %d млн сум)" % JOB["income_max_mln"][1 if cashier else 0], "income")
    try:
        age = int(_digits(a.get("age")) or 0)
    except ValueError:
        age = 0
    if age and age < 18:
        yellow("Возраст %d: для несовершеннолетних действуют ограничения по сменам и нагрузке" % age)
    if i("student") == 1 and i("study_form") == 0:
        yellow("Учится очно: расписание занятий может не совпасть с графиком 6/1", "study")

    # --- Другие отклики (риск ухода во время обучения и испытательного срока)
    if i("other_jobs") == 3:
        yellow("Уже есть оффер от другой компании: высокий риск ухода во время обучения или испытательного срока", "other")
    elif i("other_jobs") == 2:
        yellow("Параллельно ходит на собеседования в другие компании: риск ухода на испытательном сроке", "other")

    # --- Задачи на счёт
    ch_ok = _digits(a.get("calc_change")) == "1260000"
    di_ok = _digits(a.get("calc_discount")) == "4320000"
    if cashier:
        n_ok = sum([ch_ok, di_ok, _digits(a.get("calc_total")) == "2498000"])
        if n_ok == 0:
            red("Счёт для кассира: все три задачи решены неверно")
        elif n_ok < 3:
            yellow("Ошибка в задачах на счёт: неверно %d из 3 (для кассира важно)" % (3 - n_ok))
        numeracy = [1, 2, 4, 5][n_ok]
    else:
        if not ch_ok and not di_ok:
            red("Обе задачи на счёт решены неверно")
        elif not ch_ok or not di_ok:
            yellow("В одной из задач на счёт ошибка")
        numeracy = 5 if ch_ok and di_ok else (3 if ch_ok or di_ok else 1)

    # --- Hard skills
    obj_hits = need_hits = cash_hits = 0
    obj_score = cash_score = sales = None
    if cashier:
        cash_hits = _hits(a.get("cash_shortage"), CASH_GROUPS)
        cash_score = _hits_to_score(cash_hits, a.get("cash_shortage"))
        if any(k in _norm(a.get("cash_shortage")) for k in OWN_POCKET):
            yellow("Склонен(на) закрывать недостачу из своих денег: риск нарушения порядка и сокрытия", "cash")
            cash_score = min(cash_score, 2)
    else:
        obj_hits = _hits(a.get("objection"), OBJECTION_GROUPS)
        obj_score = _hits_to_score(obj_hits, a.get("objection"))
        need_hits = _hits(a.get("needs"), NEEDS_GROUPS)
        need_score = _hits_to_score(need_hits, a.get("needs"))
        sales = _clamp(round((obj_score + need_score) / 2))
    exp = [2, 3, 4, 5][i("exp")]
    if i("tech_exp") == 0:
        exp = min(5, exp + 1)

    # --- Soft skills
    con_hits = _hits(a.get("conflict"), CONFLICT_GROUPS)
    stress = _hits_to_score(con_hits, a.get("conflict"))
    resp = [5, 3, 2, 1][i("late")]
    if i("late") >= 2:
        yellow("Слабое отношение к дисциплине в вопросе опозданий")
    langs = [5, 3, 1][i("lang")]
    sjt = {}
    for q in QUESTIONS:
        if "scores" in q and (q["key"] + "_i") in a and applies(q, a):
            sjt[q["key"]] = q["scores"][i(q["key"])]
    comm = _clamp(round(((sjt.get("sjt_cash_queue", stress) if cashier else obj_score) + stress) / 2))
    for key, text in SJT_FLAGS.items():
        if key == "sjt_cash_honesty" and sjt.get(key, 5) <= 1:
            red("Выбрал(а) ответ, где излишек из кассы присваивается", "cash")
        elif key in sjt and sjt[key] <= 2:
            yellow(text, "cash" if key == "sjt_cash_honesty" else key)
    adapt = [5, 3, 1][i("change")]
    if cashier:   # у кассира KPI нет: учитывается отношение к фиксированному окладу
        motive = round(([5, 5, 4, 2, 1][i("motive")] + [5, 3, 1][i("pay_fix")]) / 2)
    else:
        motive = round(([5, 5, 4, 2, 1][i("motive")] + [5, 3, 1][i("kpi")]) / 2)
    if i("motive") == 4:
        yellow("«Пока ищу другую работу»: высокий риск быстрого ухода", "turnover")

    stab = 5
    if i("jobs_year") == 1:
        stab -= 1
    elif i("jobs_year") == 2:
        stab -= 2
        yellow("3 и более мест работы за год: риск текучести", "turnover")
    if i("reason") in (4, 5):
        stab -= 1
        yellow("Причина ухода: конфликт или штрафы. Выяснить, чья это была вина", "conflict")
    elif i("reason") == 3:
        yellow("Ушёл(ла) из-за оплаты: проверить, совпадают ли ожидания с вилкой", "income")
    elif i("reason") == 2:
        yellow("Ушёл(ла) из-за графика: у нас плавающий 6/1, риск повторения", "schedule")
    if i("reference") == 1 and i("exp") > 0:
        stab -= 1
        yellow("Опыт есть, но контакт для рекомендации давать отказывается", "reference")
    if i("other_jobs") in (2, 3):
        stab -= 1
    stab = _clamp(stab)

    if len((a.get("last_job") or "").strip()) < 10 and i("exp") > 0:
        yellow("Опыт заявлен, но о последнем месте работы написано слишком коротко")
    if len((a.get("reason_text") or "").strip()) < 15:
        yellow("Причина ухода описана слишком коротко, нужен разговор")

    if cashier:
        hard = {L_CASHNUM: numeracy, L_CASH: cash_score, L_EXP: exp}
    else:
        hard = {L_SALES: sales, L_NUM: numeracy, L_EXP: exp}
    soft = {L_COMM: comm, L_CONF: stress, L_RESP: resp, L_STAB: stab, (L_MOT_CASH if cashier else L_MOT): motive, L_ADAPT: adapt, L_LANG: langs}
    for key, label in SJT_LABELS.items():
        if key in sjt:
            soft[label] = sjt[key]
    allsc = {**hard, **soft}
    wsum = sum(WEIGHTS[k] for k in allsc)
    pct = round(sum(v * WEIGHTS[k] for k, v in allsc.items()) / (5 * wsum) * 100)

    has_red = any(f[0] == "🔴" for f in flags)
    yellow_count = sum(1 for f in flags if f[0] == "🟡")
    capped = stab <= 2 or yellow_count >= 3  # высокий балл не отменяет риски
    if has_red or pct < 45:
        verdict = "ОТКАЗ или ручной разбор рекрутером (серьёзный флаг или низкий балл)"
    elif pct >= 70 and not capped:
        verdict = "ПРИНЯТЬ: пригласить на интервью"
    else:
        verdict = "РЕЗЕРВ: пригласить при нехватке кандидатов или после прояснения жёлтых флагов"

    return {"scores": {"hard": hard, "soft": soft}, "pct": pct, "flags": flags, "verdict": verdict,
            "keyword_hits": {"objection": obj_hits, "needs": need_hits, "conflict": con_hits, "cash": cash_hits}}


def _bar(v):
    return "■" * v + "□" * (5 - v)


def answer_ru(a, key):
    """Ответ в виде, понятном рекрутеру: вариант выбора всегда на русском, свободный текст как написал кандидат."""
    q = QMAP.get(key)
    idx = a.get(key + "_i")
    if q and q["type"] == "choice" and isinstance(idx, int) and 0 <= idx < len(q["options"]):
        return q["options"][idx]
    return a.get(key, "-")


def position_name(a, short=False):
    p = a.get("position_i", 0)
    p = p if p in (0, 1) else 0
    return (POS_SHORT if short else POSITIONS)[p]


def build_profile(a, ts=None):
    r = evaluate(a)
    g = lambda k: answer_ru(a, k)
    cashier = a.get("position_i") == 1
    out = []
    out.append("ПРОФИЛЬ КАНДИДАТА: %s, %s" % (position_name(a), JOB["company"]))
    try:
        d = datetime.datetime.fromisoformat(ts) if ts else datetime.datetime.now()
    except (TypeError, ValueError):
        d = datetime.datetime.now()
    out.append("Дата анкеты: %s" % d.strftime("%d.%m.%Y %H:%M"))
    if a.get("ui_lang"):
        out.append("Язык анкеты: %s" % i18n.LANG_NAMES.get(a["ui_lang"], a["ui_lang"]))
    out.append("")
    out.append("КАНДИДАТ")
    out.append("%s, %s лет" % (g("fio"), g("age")))
    out.append("Телефон: %s" % g("phone"))
    if a.get("slot"):
        out.append("Удобное время для собеседования: %s" % a["slot"])
    out.append("Район: %s, дорога: %s" % (g("district"), g("commute")))
    if a.get("student_i") == 1:
        out.append("Учёба: %s, %s, форма: %s" % (g("study_place"), g("course"), g("study_form")))
    else:
        out.append("Учёба: не учится")
    out.append("")
    out.append("АНКЕТНЫЕ ДАННЫЕ (на оценку и вердикт не влияют)")
    out.append("Семейное положение: %s" % g("marital_status"))
    if a.get("children_i") == 1:
        out.append("Дети: %s, возраст: %s" % (g("children_count"), g("children_ages")))
    else:
        out.append("Дети: нет")
    out.append("")
    out.append("СООТВЕТСТВИЕ УСЛОВИЯМ ВАКАНСИИ")
    out.append("График (%s): %s" % (JOB["schedule"], g("schedule")))
    out.append("Вечерняя смена (до 22:00): %s" % g("evening"))
    out.append("Обучение 14 дней: %s" % g("training"))
    out.append("Языки: %s" % g("lang"))
    out.append("Физические требования: %s%s" % (g("health"), (" (%s)" % g("health_note")) if a.get("health_note") else ""))
    out.append("Выход на работу: %s" % g("start"))
    out.append("Ожидаемый доход: %s (условия: %s)" % (g("income"), JOB["income"][1 if cashier else 0]))
    if cashier:
        out.append("Фиксированный оклад кассира: %s" % g("pay_fix"))
    else:
        out.append("Отношение к KPI-бонусу: %s" % g("kpi"))
    out.append("Большой объём работы: %s" % g("workload"))
    out.append("Отношение к изменениям: %s" % g("change"))
    out.append("")
    out.append("ОПЫТ И ПРИЧИНЫ УХОДА")
    out.append("Опыт: %s, магазин техники: %s" % (g("exp"), g("tech_exp")))
    out.append("Мест работы за последний год: %s" % g("jobs_year"))
    out.append("Последнее место: %s" % g("last_job"))
    out.append("Причина ухода: %s" % g("reason"))
    out.append("Комментарий: %s" % g("reason_text"))
    out.append("Рекомендация: %s" % g("reference"))
    out.append("Другие отклики: %s%s" % (g("other_jobs"), (" (%s)" % g("other_jobs_where")) if a.get("other_jobs_where") else ""))
    out.append("")
    out.append("ОЦЕНКА HARD SKILLS (1-5)")
    for k, v in r["scores"]["hard"].items():
        out.append("%s %d  %s" % (_bar(v), v, k))
    out.append("")
    out.append("ОЦЕНКА SOFT SKILLS (1-5)")
    for k, v in r["scores"]["soft"].items():
        out.append("%s %d  %s" % (_bar(v), v, k))
    out.append("")
    out.append("ИТОГ: соответствие %d%%" % r["pct"])
    out.append("РЕКОМЕНДАЦИЯ: %s" % r["verdict"])
    allsc = {**r["scores"]["hard"], **r["scores"]["soft"]}
    strong = [k for k, v in sorted(allsc.items(), key=lambda kv: -kv[1]) if v >= 4][:3]
    weak = [k for k, v in sorted(allsc.items(), key=lambda kv: kv[1]) if v <= 3][:3]
    out.append("Сильные стороны: %s" % (", ".join(strong) if strong else "явно не видны"))
    out.append("Слабые стороны: %s" % (", ".join(weak) if weak else "нет"))
    out.append("")
    out.append("РИСКИ И ФЛАГИ")
    if r["flags"]:
        for lvl, t, _c in r["flags"]:
            out.append("%s %s" % (lvl, t))
    else:
        out.append("По анкете серьёзных рисков не выявлено")
    out.append("")
    out.append("ОТКРЫТЫЕ ОТВЕТЫ (оценка по ключевым словам, просмотрите сами)")
    if cashier:
        out.append("Недостача в кассе (200 000 сум): %s" % g("cash_shortage"))
        out.append("Счёт: сдача %s, скидка %s, сумма %s" % (g("calc_change"), g("calc_discount"), g("calc_total")))
    else:
        out.append("Выявление потребности (холодильник): %s" % g("needs"))
        out.append("Возражение «дорого»: %s" % g("objection"))
    out.append("Недовольный клиент: %s" % g("conflict"))
    out.append("")
    out.append("ВОПРОСЫ ДЛЯ ИНТЕРВЬЮ")
    qs, seen = [], set()
    for _lvl, _t, code in r["flags"]:
        q = INTERVIEW_BY_CODE.get(code)
        if q and q not in seen:
            seen.add(q)
            qs.append(q)
    if cashier:
        qs.append("Посчитайте на кассе сумму трёх товаров и дайте сдачу с 5 000 000 сум (ролевая игра).")
    else:
        qs.append("Продайте мне любой товар из магазина за 2 минуты (ролевая игра).")
    out.extend("- " + q for q in qs)
    return "\n".join(out)
