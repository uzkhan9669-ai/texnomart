"""Nomzod anketasi, baholash va profil: sotuvchi-konsultant, Texnomart (o'zbek tilida).

Vakansiya shartlari:
- 14 kunlik o'qish (kompaniya hisobidan, ustoz bilan);
- grafik 6/1, suzuvchi smenalar: 1-smena 09:00-18:00, 2-smena 13:00-22:00;
- daromad: oylik + KPI bonus tizimi; ochiq e'lonlarda vilka 2 000 000 - 8 000 000 so'm;
- talablar: o'zbek va rus tili, muloqotchanlik, e'tiborlilik, o'rganuvchanlik,
  katta hajmdagi ish, o'zgarishlarga tayyorlik; tajriba shart emas.
Ishga tushirishdan oldin JOB blokini haqiqiy do'kon bilan solishtiring.
"""
import re
import datetime

JOB = {
    "company": "Texnomart",
    "position": "Sotuvchi-konsultant",
    "training": "14 kunlik o'qish (kompaniya hisobidan)",
    "schedule": "6/1, suzuvchi smenalar: 1-smena 09:00-18:00, 2-smena 13:00-22:00",
    "income": "2 000 000 - 8 000 000 so'm (oylik + KPI bonus), oyiga 2 marta to'lanadi",
    "income_max_mln": 8,
}

# type: text | number | choice. choice uchun baho variant raqami bo'yicha beriladi.
QUESTIONS = [
    {"key": "fio", "block": "1/5 · Tanishuv va ish shartlari", "type": "text", "text": "Ismingiz va familiyangiz? (F.I.Sh.)"},
    {"key": "age", "type": "number", "text": "Yoshingiz nechada?"},
    {"key": "phone", "type": "text", "text": "Bog'lanish uchun telefon raqamingiz (masalan, +998 90 123 45 67)"},
    {"key": "district", "type": "text", "text": "Qaysi tuman yoki shaharda yashaysiz? Mo'ljalni ham yozing."},
    {"key": "commute", "type": "choice", "text": "Do'konga yetib borish uchun qancha vaqt ketadi?",
     "options": ["30 daqiqagacha", "30-60 daqiqa", "60 daqiqadan ko'p"]},
    {"key": "lang", "type": "choice", "text": "O'zbek va rus tillarini qanday bilasiz?",
     "options": ["Ikkala tilni erkin bilaman", "Bittasini erkin, ikkinchisini suhbat darajasida", "Faqat bitta tilni erkin bilaman"]},
    {"key": "schedule", "type": "choice",
     "text": "Ish tartibi: haftada 6 kun ish, 1 kun dam. Smenalar suzuvchi: 1-smena 09:00-18:00, 2-smena 13:00-22:00. Dam olish va bayram kunlari ham grafik bo'yicha ishlanadi. Sizga mos keladimi?",
     "options": ["Ha, mos keladi", "Mos, lekin barcha dam olish kunlari emas", "Boshqa grafik kerak (2/2, 5/2, yarim kun)"]},
    {"key": "evening", "type": "choice",
     "text": "2-smena soat 22:00 gacha davom etadi. Kechqurun uyga qaytish sizga muammo bo'lmaydimi?",
     "options": ["Muammo emas", "Qiyin, lekin hal qilsam bo'ladi", "Kechki smenada ishlay olmayman"]},
    {"key": "training", "type": "choice",
     "text": "Ishni boshlashdan oldin 14 kunlik o'qish bor (kompaniya hisobidan, ustoz bilan). Unda to'liq qatnasha olasizmi?",
     "options": ["Ha, to'liq qatnashaman", "Ba'zi kunlari kela olmayman", "Yo'q, o'qishga vaqtim yo'q"]},
    {"key": "start", "type": "choice", "text": "Qachon ishga chiqa olasiz?",
     "options": ["Darhol", "1-2 hafta ichida", "2 haftadan keyin"]},
    {"key": "income", "type": "choice", "text": "Oylik daromad bo'yicha kutganingiz qancha?",
     "options": ["3 mln so'mgacha", "3-5 mln so'm", "5-8 mln so'm", "8 mln so'mdan yuqori"]},
    {"key": "kpi", "type": "choice",
     "text": "Daromadning bir qismi KPI (sotuv rejasi) bo'yicha bonusga bog'liq. Bu sizga qanday?",
     "options": ["Yoqadi, ko'proq sotsam, ko'proq topaman", "Maqbul, lekin qat'iy oylik ham muhim", "Faqat qat'iy oylik istayman"]},
    {"key": "workload", "type": "choice",
     "text": "Ish hajmi katta: mijozlarga xizmat, tovarni joylashtirish, kassa, inventarizatsiya, tozalik. Shunday hajm sizga to'g'ri keladimi?",
     "options": ["Ha, ko'p ishlashga tayyorman", "Tayyorman, lekin sharoit va yordam muhim", "Menga qiyin bo'ladi"]},
    {"key": "change", "type": "choice",
     "text": "Do'konda o'zgarishlar tez-tez bo'ladi: yangi aksiyalar, tovarlar, jarayonlar, smenalar. Siz bunga qanday qaraysiz?",
     "options": ["Tez moslashaman, yangilikni yoqtiraman", "Moslashaman, lekin vaqt kerak", "O'zgarishlar menga yoqmaydi"]},
    {"key": "exp", "block": "2/5 · Tajriba va ketish sabablari", "type": "choice", "text": "Savdo sohasidagi tajribangiz?",
     "options": ["Tajriba yo'q", "1 yilgacha", "1-3 yil", "3 yildan ortiq"]},
    {"key": "tech_exp", "type": "choice", "text": "Maishiy texnika yoki elektronika sotish tajribangiz bo'lganmi?",
     "options": ["Ha", "Yo'q"]},
    {"key": "jobs_year", "type": "choice", "text": "So'nggi 1 yilda nechta ish joyida ishlagansiz?",
     "options": ["0-1", "2", "3 va undan ko'p"]},
    {"key": "last_job", "type": "text",
     "text": "So'nggi ish joyingiz haqida yozing: kompaniya, lavozim, qancha ishlagansiz, nima bilan shug'ullangansiz. Ishlamagan bo'lsangiz, «ishlamaganman» deb yozing."},
    {"key": "reason", "type": "choice", "text": "So'nggi ish joyidan ketishingizning (yoki ketmoqchi bo'lishingizning) asosiy sababi?",
     "options": ["O'sish, boshqa ish formati", "Ko'chish, o'qish, oila", "Grafik mos kelmadi", "Kam to'lashdi, kechiktirishdi",
                 "Rahbar yoki jamoa bilan nizo", "Jarimalar, bosim", "Qisqartirishdi, do'kon yopildi",
                 "Bu birinchi ish joyim", "Boshqa"]},
    {"key": "reason_text", "type": "text",
     "text": "Bir-ikki gap bilan yozing: aynan nima bo'lgan va o'sha joyda nimani o'zgartirgan bo'lardingiz?"},
    {"key": "reference", "type": "choice", "text": "Sobiq rahbaringizga tavsiya uchun qo'ng'iroq qilsak bo'ladimi?",
     "options": ["Ha, kontakt beraman", "Yo'q", "Tegishli emas, tajriba yo'q"]},
    {"key": "calc_change", "block": "3/5 · Hisob va sotuv ko'nikmalari", "type": "number",
     "text": "1-masala. Xarid 3 740 000 so'm, mijoz 5 000 000 so'm berdi. Qaytim qancha (so'mda)?"},
    {"key": "calc_discount", "type": "number",
     "text": "2-masala. Televizor 4 800 000 so'm turadi, chegirma 10%. Mijoz qancha to'laydi (so'mda)?"},
    {"key": "needs", "type": "text",
     "text": "Mijoz oilasi uchun muzlatgich tanlayapti. Eng to'g'ri modelni topish uchun unga qanday savollar berasiz? Kamida 3 ta savol yozing."},
    {"key": "objection", "type": "text",
     "text": "Mijoz muzlatgich oldida: «Qimmat ekan, o'ylab ko'raman» dedi. Siz nima deb javob berasiz? Mijozga aytadigan gapingizni yozing."},
    {"key": "conflict", "block": "4/5 · Vaziyatli savollar: mijoz, jamoa, bosim", "type": "text",
     "text": "Mijoz sotib olgan texnikasi bilan qaytib keldi va norozi: «U nosoz, siz meni aldadingiz!» Qadamma-qadam nima qilasiz?"},
    {"key": "sjt_customer", "type": "choice", "scores": [1, 5, 4, 2],
     "text": "Vaziyat: mijoz arzon telefon so'rayapti. Sizda bonusi yuqori bo'lgan qimmatroq model ham bor. Nima qilasiz?",
     "options": ["Eng qimmat modelni tavsiya qilaman: bonusim ko'proq bo'ladi",
                 "Mijoz byudjetiga mos modelni ko'rsataman va ustunliklarini tushuntiraman",
                 "Ikkala variantni ko'rsataman, tanlovni mijozga qoldiraman",
                 "Mijoz nima so'rasa, shuni beraman, ortiqcha gapirmayman"]},
    {"key": "sjt_team", "type": "choice", "scores": [1, 5, 3, 3],
     "text": "Vaziyat: kassada navbat uzayib ketdi, hamkasbingiz yolg'iz qoldi, sizda esa hozir mijoz yo'q. Nima qilasiz?",
     "options": ["Mijozim yo'q, demak bu mening ishim emas",
                 "Darhol yordamga boraman: kassaga o'taman yoki mijozlarni boshqa kassaga yo'naltiraman",
                 "Faqat so'rashsa yordam beraman",
                 "Rahbarga xabar beraman va o'z joyimda qolaman"]},
    {"key": "sjt_learn", "type": "choice", "scores": [1, 5, 4, 2],
     "text": "Vaziyat: do'konga yangi model keldi, siz uning xususiyatlarini bilmaysiz, mijoz esa so'rayapti. Nima qilasiz?",
     "options": ["Taxminan o'zim o'ylab javob beraman",
                 "Ko'rsatma va ustozdan o'rganaman, smenadan oldin modelni ko'rib chiqaman",
                 "Hamkasbdan so'rayman, keyin o'zim ham o'qib chiqaman",
                 "Mijozga «bilmayman» deb, boshqa xodimga yo'naltiraman"]},
    {"key": "sjt_stress", "type": "choice", "scores": [1, 5, 3, 2],
     "text": "Vaziyat: soat 19:00, do'konda mijozlar ko'p, kassa ishlamay qoldi, rahbar hozir yo'q. Nima qilasiz?",
     "options": ["Hech narsa qilmayman, rahbar kelishini kutaman",
                 "Mijozlarni ogohlantiraman, rahbar yoki texnik xodimni chaqiraman, mijozlarni boshqa kassaga yo'naltiraman",
                 "Xotirjam turaman va mijozlardan biroz kutishni so'rayman",
                 "Mijozlarga «kassa buzilgan, men aybdor emasman» deyman"]},
    {"key": "late", "type": "choice", "text": "Smenaga kechikayotganingizni tushundingiz. Qanday harakat qilasiz?",
     "options": ["Oldindan rahbarga xabar beraman va imkon qadar tez yetib boraman",
                 "Qachon yetsam, o'shanda kelaman, hamkasblarga yozaman",
                 "Joyida tushuntiraman", "Bu qo'rqinchli emas, do'konga zarar yo'q"]},
    {"key": "motive", "block": "5/5 · Motivatsiya", "type": "choice", "text": "Ishda siz uchun eng muhimi nima?",
     "options": ["Daromad va sotuvdan foiz", "O'qish va karyera o'sishi", "Barqarorlik va rasmiy ish haqi",
                 "Qulay grafik", "Hozircha boshqa ish qidiryapman, bu vaqtinchalik"]},
]


def _norm(s):
    """Kichik harf, apostrof turlarini olib tashlash (o'/oʻ/o` yozilishi farq qilmasin)."""
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


# Kalit so'zlar: o'zbek (apostrofsiz) va rus tilida, nomzod istalgan tilda yozishi mumkin.
OBJECTION_GROUPS = [
    ["ehtiyoj", "nima uchun", "kim uchun", "qaysi", "byudjet", "tanlab", "aniqlash", "oila",
     "потребност", "для чего", "для кого", "какой", "бюджет", "подбер", "уточн", "семь"],
    ["muddatli", "bolib", "nasiya", "rassrochka", "oyiga", "tolov", "рассрочк", "частями", "в месяц", "платеж", "платёж"],
    ["muqobil", "variant", "arzonroq", "boshqa model", "analog", "oxshash",
     "альтернатив", "вариант", "аналог", "дешевле", "другую модель", "похож"],
    ["kafolat", "afzallik", "sifat", "foyda", "aksiya", "chegirma", "sovga", "elektr", "energiya",
     "гаранти", "преимуществ", "качеств", "выгод", "акци", "скидк", "подар", "энерго"],
    ["raqam", "telefon", "bron", "qoldiring", "kontakt", "keling", "qaytib",
     "контакт", "номер", "телефон", "заброни", "зарезерв", "приходите", "вернётесь", "вернетесь"],
]
NEEDS_GROUPS = [
    ["oila", "necha kishi", "kishilik", "семь", "человек"],
    ["byudjet", "narx", "qancha", "бюджет", "цена", "сумм"],
    ["litr", "hajm", "olcham", "razmer", "размер", "объём", "объем", "литр"],
    ["elektr", "energiya", "энерго", "nofrost", "no frost", "morozil", "морозил"],
    ["brend", "model", "marka", "rang", "бренд", "марка", "цвет"],
]
CONFLICT_GROUPS = [
    ["tinglay", "xotirjam", "sabr", "gapini", "aniqlay", "выслуш", "спокойно", "не перебив", "уточн"],
    ["uzr", "kechirim", "tushunaman", "afsus", "извин", "понимаю", "сожале", "приношу"],
    ["yechim", "qaytar", "almashtir", "tuzat", "tamir", "kafolat", "servis", "chek", "tekshir",
     "решени", "вернуть", "обмен", "замен", "ремонт", "гаранти", "сервис", "проверим", "проверить", "чек"],
    ["rahbar", "administrator", "katta", "menejer", "boshliq", "руковод", "администратор", "старш", "менеджер", "управляющ"],
    ["xushmuomala", "hissiyotsiz", "bahslashmayman", "vazmin", "вежлив", "без эмоци", "не спорю", "сохраня"],
]

# Intervyu savollari: flag kodi -> savol
INTERVIEW_BY_CODE = {
    "schedule": "Qaysi dam olish kunlari va smenalar sizga noqulay va nima uchun?",
    "evening": "22:00 gacha bo'lgan smenada uyga qanday qaytasiz? Bu muammo bo'lmaydimi?",
    "training": "14 kunlik o'qishda qaysi kunlari qatnasha olmaysiz va nima uchun?",
    "conflict": "Oldingi ish joyida aynan nima bo'lgan? Siz nimani boshqacha qilgan bo'lardingiz?",
    "reference": "Nega sobiq rahbaringizga qo'ng'iroq qilishimizni xohlamaysiz?",
    "turnover": "Bizda qancha ishlashni rejalashtiryapsiz va qolishingiz uchun nima bo'lishi kerak?",
    "income": "Bizda daromad nimalardan tashkil topadi va sizning raqamingizga erishish uchun qanday natija kerak?",
    "kpi": "KPI bonus tizimi haqida nima deb o'ylaysiz? Sotuv rejasi bajarilmasa nima qilasiz?",
    "workload": "Eng og'ir ish kuningizni tasavvur qiling: kassa, tovar qabul qilish va mijozlar bir vaqtda. Nimadan boshlaysiz?",
    "change": "Oxirgi marta ishda kutilmagan o'zgarish bo'lganda nima qildingiz?",
    "lang": "Mijoz bilan 1-2 daqiqa ikkala tilda ham suhbatlashib ko'raylik.",
    "sjt_customer": "Mijozga o'zingiz uchun foydaliroq, lekin unga kerak bo'lmagan tovarni sotgan vaziyat bo'lganmi? Nima qildingiz?",
    "sjt_team": "Hamkasbingizga ish vaqtida yordam bergan holatni eslang. Buning uchun sizga hech kim aytmaganmi?",
    "sjt_learn": "Oxirgi marta ishda yangi narsani qanday o'rgandingiz? Misol keltiring.",
    "sjt_stress": "Eng qiyin va shoshilinch ish kuningizni tasvirlang. Nimadan boshladingiz va natija qanday bo'ldi?",
}


SJT_LABELS = {"sjt_customer": "Mijozga yo'naltirilganlik", "sjt_team": "Jamoada ishlash",
              "sjt_learn": "O'rganuvchanlik", "sjt_stress": "Stressga chidamlilik"}
SJT_FLAGS = {
    "sjt_customer": "Mijoz manfaatidan ko'ra o'z bonusini ustun qo'yishi mumkin (sotuvda halollik xavfi)",
    "sjt_team": "Jamoada hamkasbga yordam berishga tayyor emas",
    "sjt_learn": "Yangi mahsulotni mustaqil o'rganishga tayyor emas",
    "sjt_stress": "Bosim ostida noto'g'ri harakat qilishi mumkin",
}
WEIGHTS = {
    "Sotuv texnikasi (e'tiroz, ehtiyojni aniqlash)": 2, "Hisob (qaytim, chegirma)": 1, "Savdo tajribasi": 1,
    "Muloqot": 1, "Norozi mijoz bilan ishlash": 1, "Mas'uliyat va intizom": 1,
    "Barqarorlik (ish joyini almashtirish)": 1.5, "Motivatsiya va KPI": 1,
    "O'zgarishlarga moslashuvchanlik": 1, "Tillar (o'zbek + rus)": 1.5,
    "Mijozga yo'naltirilganlik": 1.5, "Jamoada ishlash": 1, "O'rganuvchanlik": 1, "Stressga chidamlilik": 1,
}


def verdict_code(v):
    return "QABUL" if v.startswith("QABUL") else ("ZAXIRA" if v.startswith("ZAXIRA") else "RAD")


def _clamp(x, lo=1, hi=5):
    return max(lo, min(hi, x))


def evaluate(a):
    """a: javoblar lug'ati. choice savollar uchun <key>_i (variant raqami) bor."""
    flags = []  # (daraja, matn, kod)

    def red(t, c=None): flags.append(("🔴", t, c))
    def yellow(t, c=None): flags.append(("🟡", t, c))

    i = lambda k: a.get(k + "_i", 0)

    # --- Vakansiya shartlariga moslik
    if i("lang") == 2:
        red("Faqat bitta tilni erkin biladi, vakansiya esa o'zbek va rus tillarini talab qiladi", "lang")
    elif i("lang") == 1:
        yellow("Tillardan biri suhbat darajasida, intervyuda tekshirish kerak", "lang")
    if i("schedule") == 2:
        red("6/1 suzuvchi smenali grafik mos emas", "schedule")
    elif i("schedule") == 1:
        yellow("Barcha dam olish kunlarida ishlay olmaydi, qaysi kunlar kerakligini aniqlang", "schedule")
    if i("evening") == 2:
        red("Kechki (13:00-22:00) smenada ishlay olmaydi", "evening")
    elif i("evening") == 1:
        yellow("Kechki smenadan uyga qaytish qiyin, yo'lni aniqlang", "evening")
    if i("training") == 2:
        red("14 kunlik o'qishda qatnasha olmaydi", "training")
    elif i("training") == 1:
        yellow("O'qishning ba'zi kunlarida kela olmaydi", "training")
    if i("workload") == 2:
        red("Katta hajmdagi ishga tayyor emas", "workload")
    elif i("workload") == 1:
        yellow("Katta ish hajmiga tayyor, lekin sharoit va yordam talab qiladi", "workload")
    if i("change") == 2:
        yellow("O'zgarishlarga salbiy munosabat, moslashuvchanlikni tekshiring", "change")
    if i("kpi") == 2:
        yellow("Faqat qat'iy oylik istaydi, KPI bonus tizimi unga mos kelmasligi mumkin", "kpi")
    if i("commute") == 2:
        yellow("Do'konga yo'l 60 daqiqadan ko'p: kechikish va ketib qolish xavfi")
    if i("start") == 2:
        yellow("2 haftadan keyin ishga chiqa oladi")
    if i("income") == 3:
        yellow("Kutilgan daromad vakansiya vilkasidan yuqori (%d mln so'mgacha)" % JOB["income_max_mln"], "income")
    try:
        age = int(_digits(a.get("age")) or 0)
    except ValueError:
        age = 0
    if age and (age < 18 or age > 55):
        yellow("Yosh %d: vakansiya talablariga mosligini tekshiring" % age)

    # --- Hisob masalalari
    ch_ok = _digits(a.get("calc_change")) == "1260000"
    di_ok = _digits(a.get("calc_discount")) == "4320000"
    if not ch_ok and not di_ok:
        red("Hisob bo'yicha ikkala masala ham noto'g'ri yechilgan")
    elif not ch_ok or not di_ok:
        yellow("Hisob masalalaridan birida xato bor")
    numeracy = 5 if ch_ok and di_ok else (3 if ch_ok or di_ok else 1)

    # --- Hard skills
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
    comm = _clamp(round((obj_score + stress) / 2))
    resp = [5, 3, 2, 1][i("late")]
    if i("late") >= 2:
        yellow("Kechikish masalasida intizomga bo'sh yondashuv")
    langs = [5, 3, 1][i("lang")]
    sjt = {}
    for q in QUESTIONS:
        if "scores" in q and (q["key"] + "_i") in a:
            sjt[q["key"]] = q["scores"][i(q["key"])]
    for key, text in SJT_FLAGS.items():
        if key in sjt and sjt[key] <= 2:
            yellow(text, key)
    adapt = [5, 3, 1][i("change")]
    kpi_score = [5, 3, 1][i("kpi")]
    motive = round(([5, 5, 4, 2, 1][i("motive")] + kpi_score) / 2)
    if i("motive") == 4:
        yellow("«Hozircha boshqa ish qidiryapman»: tez ketib qolish xavfi yuqori")

    stab = 5
    if i("jobs_year") == 1:
        stab -= 1
    elif i("jobs_year") == 2:
        stab -= 2
        yellow("1 yilda 3 va undan ko'p ish joyi: kadrlar oqimi xavfi", "turnover")
    if i("reason") in (4, 5):
        stab -= 1
        yellow("Ketish sababi: nizo yoki jarimalar. Bu kimning aybi bo'lganini aniqlang", "conflict")
    elif i("reason") == 3:
        yellow("To'lov sababli ketgan: kutganlari vilkaga mosligini tekshiring", "income")
    elif i("reason") == 2:
        yellow("Grafik sababli ketgan: bizda 6/1 suzuvchi grafik, takrorlanish xavfi", "schedule")
    if i("reference") == 1 and i("exp") > 0:
        stab -= 1
        yellow("Tajribasi bor, lekin tavsiya uchun kontakt berishdan bosh tortadi", "reference")
    stab = _clamp(stab)

    if len((a.get("last_job") or "").strip()) < 10 and i("exp") > 0:
        yellow("Tajriba bor deyilgan, lekin oxirgi ish joyi juda qisqa yozilgan")
    if len((a.get("reason_text") or "").strip()) < 15:
        yellow("Ketish sababi juda qisqa yozilgan, suhbat kerak")

    hard = {"Sotuv texnikasi (e'tiroz, ehtiyojni aniqlash)": sales, "Hisob (qaytim, chegirma)": numeracy,
            "Savdo tajribasi": exp}
    soft = {"Muloqot": comm, "Norozi mijoz bilan ishlash": stress, "Mas'uliyat va intizom": resp,
            "Barqarorlik (ish joyini almashtirish)": stab, "Motivatsiya va KPI": motive,
            "O'zgarishlarga moslashuvchanlik": adapt, "Tillar (o'zbek + rus)": langs}
    for key, label in SJT_LABELS.items():
        if key in sjt:
            soft[label] = sjt[key]
    scores = {"hard": hard, "soft": soft}
    allsc = {**hard, **soft}
    wsum = sum(WEIGHTS[k] for k in allsc)
    pct = round(sum(v * WEIGHTS[k] for k, v in allsc.items()) / (5 * wsum) * 100)

    has_red = any(f[0] == "🔴" for f in flags)
    yellow_count = sum(1 for f in flags if f[0] == "🟡")
    capped = stab <= 2 or yellow_count >= 3  # yuqori ball xavflarni bekor qilmaydi
    if has_red or pct < 45:
        verdict = "RAD ETISH yoki rekruter qo'lda ko'rib chiqadi (jiddiy flag yoki past ball)"
    elif pct >= 70 and not capped:
        verdict = "QABUL QILAMIZ: intervyuga taklif qilish"
    else:
        verdict = "ZAXIRA: nomzod yetishmasa yoki sariq flaglar aniqlangach taklif qilish"

    return {"scores": scores, "pct": pct, "flags": flags, "verdict": verdict,
            "keyword_hits": {"objection": obj_hits, "needs": need_hits, "conflict": con_hits}}


def _bar(v):
    return "■" * v + "□" * (5 - v)


def build_profile(a, ts=None):
    r = evaluate(a)
    g = lambda k: a.get(k, "-")
    out = []
    out.append("NOMZOD PROFILI: %s, %s" % (JOB["position"], JOB["company"]))
    try:
        d = datetime.datetime.fromisoformat(ts) if ts else datetime.datetime.now()
    except (TypeError, ValueError):
        d = datetime.datetime.now()
    out.append("Anketa sanasi: %s" % d.strftime("%d.%m.%Y %H:%M"))
    out.append("")
    out.append("NOMZOD")
    out.append("%s, %s yosh" % (g("fio"), g("age")))
    out.append("Telefon: %s" % g("phone"))
    out.append("Hudud: %s, yo'l: %s" % (g("district"), g("commute")))
    out.append("")
    out.append("VAKANSIYA SHARTLARIGA MOSLIK")
    out.append("Grafik (%s): %s" % (JOB["schedule"], g("schedule")))
    out.append("Kechki smena (22:00 gacha): %s" % g("evening"))
    out.append("14 kunlik o'qish: %s" % g("training"))
    out.append("Tillar: %s" % g("lang"))
    out.append("Ishga chiqish: %s" % g("start"))
    out.append("Kutilgan daromad: %s (vakansiya vilkasi: %s)" % (g("income"), JOB["income"]))
    out.append("KPI bonus tizimiga munosabat: %s" % g("kpi"))
    out.append("Katta ish hajmi: %s" % g("workload"))
    out.append("O'zgarishlarga munosabat: %s" % g("change"))
    out.append("")
    out.append("TAJRIBA VA KETISH SABABLARI")
    out.append("Savdo tajribasi: %s, texnika: %s" % (g("exp"), g("tech_exp")))
    out.append("So'nggi 1 yilda ish joylari soni: %s" % g("jobs_year"))
    out.append("Oxirgi ish joyi: %s" % g("last_job"))
    out.append("Ketish sababi: %s" % g("reason"))
    out.append("Izoh: %s" % g("reason_text"))
    out.append("Tavsiya: %s" % g("reference"))
    out.append("")
    out.append("HARD SKILLS BAHOSI (1-5)")
    for k, v in r["scores"]["hard"].items():
        out.append("%s %d  %s" % (_bar(v), v, k))
    out.append("")
    out.append("SOFT SKILLS BAHOSI (1-5)")
    for k, v in r["scores"]["soft"].items():
        out.append("%s %d  %s" % (_bar(v), v, k))
    out.append("")
    out.append("NATIJA: moslik %d%%" % r["pct"])
    out.append("TAVSIYA: %s" % r["verdict"])
    allsc = {**r["scores"]["hard"], **r["scores"]["soft"]}
    strong = [k for k, v in sorted(allsc.items(), key=lambda kv: -kv[1]) if v >= 4][:3]
    weak = [k for k, v in sorted(allsc.items(), key=lambda kv: kv[1]) if v <= 3][:3]
    out.append("Kuchli tomonlar: %s" % (", ".join(strong) if strong else "aniq ko'rinmaydi"))
    out.append("Zaif tomonlar: %s" % (", ".join(weak) if weak else "yo'q"))
    out.append("")
    out.append("XAVFLAR VA FLAGLAR")
    if r["flags"]:
        for lvl, t, _c in r["flags"]:
            out.append("%s %s" % (lvl, t))
    else:
        out.append("Anketa bo'yicha jiddiy xavf aniqlanmadi")
    out.append("")
    out.append("OCHIQ JAVOBLAR (baho kalit so'zlar bo'yicha berilgan, o'zingiz ko'zdan kechiring)")
    out.append("Ehtiyojni aniqlash (muzlatgich): %s" % g("needs"))
    out.append("«Qimmat» e'tirozi: %s" % g("objection"))
    out.append("Norozi mijoz: %s" % g("conflict"))
    out.append("")
    out.append("INTERVYU UCHUN SAVOLLAR")
    qs, seen = [], set()
    for _lvl, _t, code in r["flags"]:
        q = INTERVIEW_BY_CODE.get(code)
        if q and q not in seen:
            seen.add(q)
            qs.append(q)
    qs.append("Menga do'kondagi istalgan tovarni 2 daqiqada soting (rolli o'yin).")
    out.extend("- " + q for q in qs)
    return "\n".join(out)
