"""Этапы воронки и сообщения кандидату при смене этапа (на языке его анкеты).

Контакт для вопросов берётся из переменной окружения HR_CONTACT (телефон или @username отдела кадров).
В шаблонах часть в [[...]] выпадает, если поле внутри неё пустое.
"""
import datetime
import json
import os
import re

import i18n
import store
import stores

STAGE_RU = store.STAGE_RU
ORDER = store.STAGES
# Поля, которые рекрутер заполняет перед отправкой: обязательные и необязательные
FIELDS = {"sozvon": ((), ("time",)), "sobes": (("date", "time", "place"), ()), "staj": (("date", "place"), ("time",)),
          "offer": ((), ("date", "place")), "ishda": ((), ("date", "place")), "zaxira": ((), ()), "rad": ((), ())}
FIELD_RU = {"date": "Дата", "time": "Время", "place": "Магазин"}
REASONS = ["Не подошёл график", "Не вышел на связь", "Отказался сам", "Не прошёл собеседование", "Не прошёл стажировку", "Другое"]
ALIASES = dict({v.lower(): k for k, v in STAGE_RU.items()}, **{k: k for k in STAGE_RU},
               **{"новый": "yangi", "новая": "yangi", "собес": "sobes", "стаж": "staj", "chaqirildi": "sobes", "qabul": "offer"})

TEXT = {
    "sozvon": {
        "uz": "Assalomu alaykum, {name}! Texnomart kompaniyasidagi «{position}» lavozimi uchun anketangiz uchun rahmat. Anketangizni ko'rib chiqdik va siz bilan telefon orqali gaplashmoqchimiz.[[ Qo'ng'iroq vaqti: {time}.]]\nIltimos, anketada ko'rsatgan raqamingiz orqali aloqada bo'ling.",
        "ru": "Здравствуйте, {name}! Спасибо за анкету на должность «{position}» в Texnomart. Мы её рассмотрели и хотим созвониться с вами.[[ Время звонка: {time}.]]\nПожалуйста, будьте на связи по номеру, который вы указали в анкете.",
        "en": "Hello, {name}! Thank you for applying for the “{position}” position at Texnomart. We have reviewed your application and would like to call you.[[ Call time: {time}.]]\nPlease stay available at the number you provided."},
    "sobes": {
        "uz": "Assalomu alaykum, {name}! Sizni Texnomart kompaniyasiga «{position}» lavozimi bo'yicha suhbatga taklif qilamiz.\nSana: {date}\nVaqt: {time}\nManzil: {place}\nPasportingizni olib keling. Kela olmasangiz, iltimos, oldindan xabar bering.",
        "ru": "Здравствуйте, {name}! Приглашаем вас на собеседование на должность «{position}» в Texnomart.\nДата: {date}\nВремя: {time}\nАдрес: {place}\nВозьмите с собой паспорт. Если не сможете прийти, пожалуйста, предупредите заранее.",
        "en": "Hello, {name}! We invite you to an interview for the “{position}” position at Texnomart.\nDate: {date}\nTime: {time}\nAddress: {place}\nPlease bring your passport. If you cannot come, please let us know in advance."},
    "staj": {
        "uz": "Assalomu alaykum, {name}! Siz suhbatdan muvaffaqiyatli o'tdingiz. Sizni Texnomartda stajirovkaga taklif qilamiz.\nBoshlanishi: {date}[[, {time}]]\nManzil: {place}\nPasportingizni olib keling.",
        "ru": "Здравствуйте, {name}! Вы успешно прошли собеседование. Приглашаем вас на стажировку в Texnomart.\nНачало: {date}[[, {time}]]\nАдрес: {place}\nВозьмите с собой паспорт.",
        "en": "Hello, {name}! You have passed the interview. We invite you to an internship at Texnomart.\nStart: {date}[[, {time}]]\nAddress: {place}\nPlease bring your passport."},
    "offer": {
        "uz": "Assalomu alaykum, {name}! Tabriklaymiz: sizga Texnomart kompaniyasida «{position}» lavozimida ishlashni taklif qilamiz.[[\nIshga chiqish sanasi: {date}]][[\nIsh joyi: {place}]]\nRekruter siz bilan bog'lanib, keyingi qadamlar va hujjatlar haqida aytib beradi.",
        "ru": "Здравствуйте, {name}! Поздравляем: мы рады предложить вам работу в Texnomart на должности «{position}».[[\nДата выхода: {date}]][[\nМесто работы: {place}]]\nРекрутер свяжется с вами и расскажет о следующих шагах и документах.",
        "en": "Hello, {name}! Congratulations: we are pleased to offer you the “{position}” position at Texnomart.[[\nStart date: {date}]][[\nWorkplace: {place}]]\nA recruiter will contact you about the next steps and documents."},
    "ishda": {
        "uz": "Assalomu alaykum, {name}! Tabriklaymiz: siz Texnomart kompaniyasiga «{position}» lavozimiga ishga qabul qilindingiz. Jamoamizga xush kelibsiz![[\nBirinchi ish kuni: {date}]][[\nIsh joyi: {place}]]\nO'zingiz bilan pasportingizni oling.",
        "ru": "Здравствуйте, {name}! Поздравляем: вы приняты на работу в Texnomart на должность «{position}». Добро пожаловать в команду![[\nПервый рабочий день: {date}]][[\nМесто работы: {place}]]\nВозьмите с собой паспорт.",
        "en": "Hello, {name}! Congratulations: you have been hired at Texnomart as “{position}”. Welcome to the team![[\nFirst working day: {date}]][[\nWorkplace: {place}]]\nPlease bring your passport."},
    "zaxira": {
        "uz": "Assalomu alaykum, {name}! Texnomartga qiziqish bildirganingiz uchun rahmat. Hozircha mos bo'sh o'rin yo'q, lekin anketangizni saqlab qo'ydik va o'rin paydo bo'lganda siz bilan bog'lanamiz.",
        "ru": "Здравствуйте, {name}! Спасибо за интерес к Texnomart. Сейчас подходящих мест нет, но мы сохранили вашу анкету и свяжемся с вами, когда появится вакансия.",
        "en": "Hello, {name}! Thank you for your interest in Texnomart. There is no suitable opening right now, but we have kept your application and will contact you when one appears."},
    "rad": {
        "uz": "Assalomu alaykum, {name}! Texnomartdagi «{position}» lavozimiga murojaat qilganingiz va anketani to'ldirishga vaqt ajratganingiz uchun rahmat. Afsuski, hozir sizni keyingi bosqichga taklif qila olmaymiz. Ish izlashda omad tilaymiz.",
        "ru": "Здравствуйте, {name}! Спасибо, что откликнулись на вакансию «{position}» в Texnomart и нашли время заполнить анкету. К сожалению, сейчас мы не готовы пригласить вас на следующий этап. Желаем вам успехов в поиске работы.",
        "en": "Hello, {name}! Thank you for applying for the “{position}” position at Texnomart and for taking the time to fill in the form. Unfortunately, we are not able to invite you to the next stage at this time. We wish you success in your job search."},
}
CONTACT = {"uz": "\nSavollar bo'lsa: {contact}", "ru": "\nПо вопросам: {contact}", "en": "\nQuestions: {contact}"}


def contact():
    return os.environ.get("HR_CONTACT", "").strip()[:80]


def parse_stage(word):
    return ALIASES.get((word or "").strip().lower())


def clean_fields(stage, fields):
    """Проверяет поля этапа. Возвращает (поля, список недостающих обязательных)."""
    req, opt = FIELDS.get(stage, ((), ()))
    out = {}
    for k in req + opt:
        v = str((fields or {}).get(k) or "").strip()[:120]
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)   # дата из календаря панели -> 15.11.2026
        if k == "date" and m:
            try:
                v = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%d.%m.%Y")
            except ValueError:
                v = ""
        out[k] = v
    # магазин из списка: адрес подставляется в сообщение, а магазин становится филиалом кандидата
    code = stores.resolve((fields or {}).get("store")) or stores.resolve(out.get("place"))
    if code and "place" in out:
        out["place"] = stores.place(code)
        out["store"] = stores.label(code)
    return out, [k for k in req if not out[k]]


def with_branch(row, stage, fields):
    """Если магазин не указан, для стажировки и оффера берётся филиал кандидата (тот же, что на собеседовании)."""
    f = dict(fields or {})
    if stage in ("staj", "offer", "ishda") and "store" not in f and not f.get("place") and stores.resolve(row["branch"]):
        f["store"] = row["branch"]
    return f


def note_of(fields):
    """Короткая запись для истории: дата, время, магазин (или адрес, введённый вручную)."""
    f = dict(fields or {})
    if f.get("store"):
        f["place"] = f.pop("store")
    return "; ".join(v for k, v in f.items() if v and k != "store")


def answers_of(row):
    try:
        a = json.loads(row["answers"] or "{}")
        return a if isinstance(a, dict) else {}
    except ValueError:
        return {}


def build_text(row, stage, fields=None):
    """Текст сообщения кандидату для этапа (на языке его анкеты) или None, если этапу сообщение не положено."""
    if stage not in TEXT:
        return None
    a = answers_of(row)
    lang = i18n.lang_ok(a.get("ui_lang"))
    pos = a.get("position_i", 0) if a.get("position_i") in (0, 1) else 0
    vals, _missing = clean_fields(stage, fields)
    vals.update(name=(row["fio"] or "").strip() or "-", position=i18n.q_options("position", lang)[pos], contact=contact())

    def keep(m):   # необязательная часть остаётся, только если все её поля заполнены
        return m.group(1) if all(vals.get(k) for k in re.findall(r"\{(\w+)\}", m.group(1))) else ""

    tmpl = re.sub(r"\[\[(.*?)\]\]", keep, TEXT[stage][lang] + "[[" + CONTACT[lang] + "]]", flags=re.S)
    # один проход подстановки: фигурные скобки в данных кандидата или рекрутера не обрабатываются повторно
    return re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m.group(1), "")), tmpl)


def is_forward(old, new):
    """Движение вперёд по воронке (или уход в резерв/отказ): по умолчанию с сообщением. Назад: без него."""
    if new in ("zaxira", "rad"):
        return True
    if old in ORDER and new in ORDER:
        return ORDER.index(new) > ORDER.index(old)
    return True
