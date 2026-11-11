"""Тексты анкеты на трёх языках (uz, ru, en) и строки интерфейса для кандидата.

Рекрутер видит всё на русском (REC_LANG). Кандидат выбирает язык сам.
Q[key][lang] = (текст вопроса, [варианты] или None). Порядок вариантов одинаков во всех языках:
оценка считается по номеру варианта, поэтому менять порядок нельзя.
"""
LANGS = ("uz", "ru", "en")
REC_LANG = "ru"
LANG_NAMES = {"uz": "O'zbekcha", "ru": "Русский", "en": "English"}
LANG_FLAGS = {"uz": "🇺🇿", "ru": "🇷🇺", "en": "🇬🇧"}

BLOCKS = {
    "b1": {"uz": "1/5 · Tanishuv va ish shartlari", "ru": "1/5 · Знакомство и условия работы", "en": "1/5 · About you and job terms"},
    "b2": {"uz": "2/5 · Tajriba va ketish sabablari", "ru": "2/5 · Опыт и причины ухода", "en": "2/5 · Experience and reasons for leaving"},
    "b3": {"uz": "3/5 · Hisob va ish vazifalari", "ru": "3/5 · Счёт и рабочие задачи", "en": "3/5 · Math and work tasks"},
    "b4": {"uz": "4/5 · Vaziyatli savollar: mijoz, jamoa, bosim", "ru": "4/5 · Ситуации: клиент, команда, давление", "en": "4/5 · Situations: customer, team, pressure"},
    "b5": {"uz": "5/5 · Motivatsiya", "ru": "5/5 · Мотивация", "en": "5/5 · Motivation"},
}

JOB_TR = {
    # Что предлагает компания (по странице работодателя Texnomart на hh.uz)
    "perks": {
        "uz": ["Tajribasiz karyera boshlash: o'qitish va ustoz", "Karyera o'sishi va turli hududlarda ishlash imkoniyati",
               "Barqaror, o'z vaqtida to'lanadigan oylik", "Rasmiy ishga joylashish", "21 kalendar kunlik haq to'lanadigan ta'til",
               "Texnomart do'konlarida xodimlar uchun chegirmalar", "Korporativ tadbirlar va bayram sovg'alari"],
        "ru": ["Старт карьеры без опыта: обучение и наставник", "Карьерный рост и возможность работать в разных регионах",
               "Стабильная зарплата без задержек", "Официальное трудоустройство", "21 календарный день оплачиваемого отпуска",
               "Скидки для сотрудников в магазинах Texnomart", "Корпоративные мероприятия и подарки к праздникам"],
        "en": ["Start your career with no experience: training and a mentor", "Career growth and the chance to work in different regions",
               "Stable salary paid on time", "Official employment", "21 calendar days of paid leave",
               "Employee discounts in Texnomart stores", "Corporate events and holiday gifts"]},
    "training": {"uz": "14 kunlik o'qish (kompaniya hisobidan)", "ru": "14 дней обучения (за счёт компании)",
                 "en": "14-day training (paid by the company)"},
    "schedule": {"uz": "6/1, suzuvchi smenalar: 1-smena 09:00-18:00, 2-smena 13:00-22:00",
                 "ru": "6/1, плавающие смены: 1-я смена 09:00-18:00, 2-я смена 13:00-22:00",
                 "en": "6/1, rotating shifts: 1st shift 09:00-18:00, 2nd shift 13:00-22:00"},
    "income": {"uz": "sotuvchi-konsultant: 2 000 000 - 8 000 000 so'm (oylik + KPI bonus); kassir: qat'iy oylik, o'qish davrida 2 500 000 so'm, o'qishni muvaffaqiyatli tugatgach 5 000 000 so'm",
               "ru": "продавец-консультант: 2 000 000 - 8 000 000 сум (оклад + KPI-бонус); кассир: фиксированный оклад, во время обучения 2 500 000 сум, после успешного обучения 5 000 000 сум",
               "en": "sales consultant: 2,000,000 - 8,000,000 UZS (salary + KPI bonus); cashier: fixed salary, 2,500,000 UZS during training and 5,000,000 UZS after successful training"},
    "income_pos": [
        {"uz": "2 000 000 - 8 000 000 so'm (oylik + KPI bonus)", "ru": "2 000 000 - 8 000 000 сум (оклад + KPI-бонус)", "en": "2,000,000 - 8,000,000 UZS (salary + KPI bonus)"},
        {"uz": "qat'iy oylik: o'qishda 2 500 000, keyin 5 000 000 so'm", "ru": "фиксированный оклад: 2 500 000 сум на обучении, затем 5 000 000 сум",
         "en": "fixed salary: 2,500,000 UZS in training, then 5,000,000 UZS"}],
}

Q = {
    "position": {
        "uz": ("Qaysi lavozimga murojaat qilyapsiz?", ["Sotuvchi-konsultant", "Kassir"]),
        "ru": ("На какую должность вы претендуете?", ["Продавец-консультант", "Кассир"]),
        "en": ("Which position are you applying for?", ["Sales consultant", "Cashier"])},
    "fio": {
        "uz": ("Ismingiz va familiyangiz? (F.I.Sh.)", None),
        "ru": ("Ваши имя и фамилия? (Ф.И.О.)", None),
        "en": ("Your first and last name?", None)},
    "age": {
        "uz": ("Yoshingiz nechada?", None),
        "ru": ("Сколько вам полных лет?", None),
        "en": ("How old are you?", None)},
    "phone": {
        "uz": ("Bog'lanish uchun telefon raqamingiz (masalan, +998 90 123 45 67)", None),
        "ru": ("Ваш контактный телефон (например, +998 90 123 45 67)", None),
        "en": ("Your contact phone number (e.g. +998 90 123 45 67)", None)},
    "district": {
        "uz": ("Qaysi tuman yoki shaharda yashaysiz? Mo'ljalni ham yozing.", None),
        "ru": ("В каком районе или городе вы живёте? Укажите также ориентир.", None),
        "en": ("Which district or city do you live in? Add a landmark too.", None)},
    "commute": {
        "uz": ("Do'konga yetib borish uchun qancha vaqt ketadi?", ["30 daqiqagacha", "30-60 daqiqa", "60 daqiqadan ko'p"]),
        "ru": ("Сколько времени занимает дорога до магазина?", ["До 30 минут", "30-60 минут", "Более 60 минут"]),
        "en": ("How long does it take you to get to the store?", ["Up to 30 minutes", "30-60 minutes", "More than 60 minutes"])},
    "lang": {
        "uz": ("O'zbek va rus tillarini qanday bilasiz?",
               ["Ikkala tilni erkin bilaman", "Bittasini erkin, ikkinchisini suhbat darajasida", "Faqat bitta tilni erkin bilaman"]),
        "ru": ("Как вы владеете узбекским и русским языками?",
               ["Свободно владею обоими", "Одним свободно, вторым на разговорном уровне", "Свободно владею только одним"]),
        "en": ("How well do you speak Uzbek and Russian?",
               ["Fluent in both", "Fluent in one, conversational in the other", "Fluent in only one"])},
    "student": {
        "uz": ("Hozir o'qiysizmi (universitet, kollej, litsey)?", ["Yo'q, o'qimayman", "Ha, o'qiyman"]),
        "ru": ("Вы сейчас учитесь (университет, колледж, лицей)?", ["Нет, не учусь", "Да, учусь"]),
        "en": ("Are you currently studying (university, college, lyceum)?", ["No, I am not studying", "Yes, I am studying"])},
    "study_place": {
        "uz": ("Qayerda o'qiysiz? O'quv yurti va yo'nalishni yozing.", None),
        "ru": ("Где вы учитесь? Укажите учебное заведение и направление.", None),
        "en": ("Where do you study? Write the institution and field of study.", None)},
    "course": {
        "uz": ("Nechanchi kursdasiz?", ["1-kurs", "2-kurs", "3-kurs", "4-kurs", "5-kurs va yuqori (magistratura)"]),
        "ru": ("На каком вы курсе?", ["1 курс", "2 курс", "3 курс", "4 курс", "5 курс и выше (магистратура)"]),
        "en": ("Which year are you in?", ["1st year", "2nd year", "3rd year", "4th year", "5th year or higher (master's)"])},
    "study_form": {
        "uz": ("O'qish shakli qanday?", ["Kunduzgi", "Sirtqi", "Kechki yoki masofaviy"]),
        "ru": ("Какая у вас форма обучения?", ["Очная", "Заочная", "Вечерняя или дистанционная"]),
        "en": ("What is your form of study?", ["Full-time", "Part-time (correspondence)", "Evening or remote"])},
    "marital_status": {
        "uz": ("Oilaviy ahvolingiz?", ["Uylangan / Turmushga chiqqan", "Uylanmagan / Turmushga chiqmagan", "Ajrashgan"]),
        "ru": ("Ваше семейное положение?", ["Женат / Замужем", "Не женат / Не замужем", "Разведён / Разведена"]),
        "en": ("What is your marital status?", ["Married", "Single", "Divorced"])},
    "children": {
        "uz": ("Farzandlaringiz bormi?", ["Yo'q", "Ha"]),
        "ru": ("Есть ли у вас дети?", ["Нет", "Да"]),
        "en": ("Do you have children?", ["No", "Yes"])},
    "children_count": {
        "uz": ("Nechta farzandingiz bor?", ["1", "2", "3", "4 va undan ko'p"]),
        "ru": ("Сколько у вас детей?", ["1", "2", "3", "4 и более"]),
        "en": ("How many children do you have?", ["1", "2", "3", "4 or more"])},
    "children_ages": {
        "uz": ("Farzandlaringiz necha yoshda? (masalan: 3 va 7 yosh)", None),
        "ru": ("Сколько лет вашим детям? (например: 3 и 7 лет)", None),
        "en": ("How old are your children? (e.g. 3 and 7 years)", None)},
    "health": {
        "uz": ("Ish butun smena davomida oyoqda turishni, ko'p yurishni va ba'zan 10-15 kg gacha yuk ko'tarishni talab qiladi. Sog'lig'ingiz bunga imkon beradimi?",
               ["Ha, cheklovlar yo'q", "Ba'zi cheklovlar bor", "Yo'q, bunday ish menga to'g'ri kelmaydi"]),
        "ru": ("Работа требует всю смену быть на ногах, много ходить и иногда поднимать до 10-15 кг. Позволяет ли вам это здоровье?",
               ["Да, ограничений нет", "Есть некоторые ограничения", "Нет, такая работа мне не подходит"]),
        "en": ("The job requires being on your feet the whole shift, walking a lot and sometimes lifting up to 10-15 kg. Does your health allow this?",
               ["Yes, no restrictions", "I have some restrictions", "No, this kind of work does not suit me"])},
    "health_note": {
        "uz": ("Qanday cheklovlar bor? Qaysi vazifalarni bajara olmaysiz? (tashxis yozish shart emas)", None),
        "ru": ("Какие есть ограничения? Какие задачи вы не сможете выполнять? (диагноз писать не нужно)", None),
        "en": ("What restrictions do you have? Which tasks can you not do? (no need to name a diagnosis)", None)},
    "schedule": {
        "uz": ("Ish tartibi: haftada 6 kun ish, 1 kun dam. Smenalar suzuvchi: 1-smena 09:00-18:00, 2-smena 13:00-22:00. Dam olish va bayram kunlari ham grafik bo'yicha ishlanadi. Sizga mos keladimi?",
               ["Ha, mos keladi", "Mos, lekin barcha dam olish kunlari emas", "Boshqa grafik kerak (2/2, 5/2, yarim kun)"]),
        "ru": ("График: 6 рабочих дней в неделю, 1 выходной. Смены плавающие: 1-я смена 09:00-18:00, 2-я смена 13:00-22:00. В выходные и праздники работа тоже по графику. Вам это подходит?",
               ["Да, подходит", "Подходит, но не во все выходные", "Нужен другой график (2/2, 5/2, неполный день)"]),
        "en": ("Schedule: 6 working days a week, 1 day off. Shifts rotate: 1st shift 09:00-18:00, 2nd shift 13:00-22:00. Weekends and public holidays are also worked by schedule. Does this suit you?",
               ["Yes, it suits me", "It suits me, but not every weekend", "I need a different schedule (2/2, 5/2, part-time)"])},
    "evening": {
        "uz": ("2-smena soat 22:00 gacha davom etadi. Kechqurun uyga qaytish sizga muammo bo'lmaydimi?",
               ["Muammo emas", "Qiyin, lekin hal qilsam bo'ladi", "Kechki smenada ishlay olmayman"]),
        "ru": ("2-я смена длится до 22:00. Не будет ли для вас проблемой возвращаться домой вечером?",
               ["Не проблема", "Сложно, но решаемо", "В вечернюю смену работать не смогу"]),
        "en": ("The 2nd shift lasts until 22:00. Would getting home in the evening be a problem for you?",
               ["No problem", "Difficult, but I can manage", "I cannot work the evening shift"])},
    "training": {
        "uz": ("Ishni boshlashdan oldin 14 kunlik o'qish bor (kompaniya hisobidan, ustoz bilan). Unda to'liq qatnasha olasizmi?",
               ["Ha, to'liq qatnashaman", "Ba'zi kunlari kela olmayman", "Yo'q, o'qishga vaqtim yo'q"]),
        "ru": ("Перед началом работы есть 14-дневное обучение (за счёт компании, с наставником). Сможете ли вы пройти его полностью?",
               ["Да, пройду полностью", "В некоторые дни прийти не смогу", "Нет, на обучение у меня нет времени"]),
        "en": ("Before starting there is a 14-day training (paid by the company, with a mentor). Can you attend it fully?",
               ["Yes, I will attend fully", "I cannot come on some days", "No, I have no time for training"])},
    "start": {
        "uz": ("Qachon ishga chiqa olasiz?", ["Darhol", "1-2 hafta ichida", "2 haftadan keyin"]),
        "ru": ("Когда вы сможете выйти на работу?", ["Сразу", "В течение 1-2 недель", "Позже чем через 2 недели"]),
        "en": ("When can you start work?", ["Immediately", "Within 1-2 weeks", "In more than 2 weeks"])},
    "income": {
        "uz": ("Oylik daromad bo'yicha kutganingiz qancha?", ["3 mln so'mgacha", "3-5 mln so'm", "5-8 mln so'm", "8 mln so'mdan yuqori"]),
        "ru": ("Какой ежемесячный доход вы ожидаете?", ["До 3 млн сум", "3-5 млн сум", "5-8 млн сум", "Более 8 млн сум"]),
        "en": ("What monthly income do you expect?", ["Up to 3 mln UZS", "3-5 mln UZS", "5-8 mln UZS", "More than 8 mln UZS"])},
    "kpi": {
        "uz": ("Daromadning bir qismi KPI (reja) bo'yicha bonusga bog'liq. Bu sizga qanday?",
               ["Yoqadi, yaxshi ishlasam, ko'proq topaman", "Maqbul, lekin qat'iy oylik ham muhim", "Faqat qat'iy oylik istayman"]),
        "ru": ("Часть дохода зависит от KPI-бонуса (выполнение плана). Как вы к этому относитесь?",
               ["Нравится: лучше работаю, больше зарабатываю", "Приемлемо, но важен и фиксированный оклад", "Хочу только фиксированный оклад"]),
        "en": ("Part of the income depends on a KPI bonus (meeting the plan). How do you feel about that?",
               ["I like it: the better I work, the more I earn", "Acceptable, but a fixed salary matters too", "I want a fixed salary only"])},
    "pay_fix": {
        "uz": ("Kassirda oylik qat'iy belgilangan (bonus yo'q): o'qish davrida 2 500 000 so'm, o'qishni muvaffaqiyatli tugatgach yana 2 500 000 so'm qo'shiladi, jami 5 000 000 so'm. Sizga mos keladimi?",
               ["Ha, mos keladi", "Mos, lekin ko'proq bo'lishini xohlardim", "Yo'q, mos kelmaydi"]),
        "ru": ("У кассира оклад только фиксированный (без бонусов): во время обучения 2 500 000 сум, после успешного обучения добавляется ещё 2 500 000 сум, всего 5 000 000 сум. Вам это подходит?",
               ["Да, подходит", "Подходит, но хотелось бы больше", "Нет, не подходит"]),
        "en": ("A cashier's salary is fixed only (no bonuses): 2,500,000 UZS during training; after successful training another 2,500,000 UZS is added, 5,000,000 UZS in total. Does this suit you?",
               ["Yes, it suits me", "It suits me, but I would like more", "No, it does not suit me"])},
    "workload": {
        "uz": ("Ish hajmi katta: mijozlarga xizmat, tovarni joylashtirish, kassa, inventarizatsiya, tozalik. Shunday hajm sizga to'g'ri keladimi?",
               ["Ha, ko'p ishlashga tayyorman", "Tayyorman, lekin sharoit va yordam muhim", "Menga qiyin bo'ladi"]),
        "ru": ("Объём работы большой: обслуживание клиентов, выкладка товара, касса, инвентаризация, чистота. Подходит ли вам такой объём?",
               ["Да, готов(а) много работать", "Готов(а), но важны условия и помощь", "Мне будет тяжело"]),
        "en": ("The workload is large: serving customers, stocking goods, the cash desk, inventory, keeping things clean. Does this suit you?",
               ["Yes, I am ready to work a lot", "I am ready, but conditions and support matter", "It will be hard for me"])},
    "change": {
        "uz": ("Do'konda o'zgarishlar tez-tez bo'ladi: yangi aksiyalar, tovarlar, jarayonlar, smenalar. Siz bunga qanday qaraysiz?",
               ["Tez moslashaman, yangilikni yoqtiraman", "Moslashaman, lekin vaqt kerak", "O'zgarishlar menga yoqmaydi"]),
        "ru": ("В магазине часто бывают изменения: новые акции, товары, процессы, смены. Как вы к этому относитесь?",
               ["Быстро адаптируюсь, люблю новое", "Адаптируюсь, но нужно время", "Перемены мне не нравятся"]),
        "en": ("Changes happen often in the store: new promotions, products, processes, shifts. How do you feel about that?",
               ["I adapt quickly and like new things", "I adapt, but I need time", "I do not like changes"])},
    "exp": {
        "uz": ("Savdo yoki kassa sohasidagi tajribangiz?", ["Tajriba yo'q", "1 yilgacha", "1-3 yil", "3 yildan ortiq"]),
        "ru": ("Ваш опыт в торговле или на кассе?", ["Нет опыта", "До 1 года", "1-3 года", "Более 3 лет"]),
        "en": ("Your experience in retail or at a cash desk?", ["No experience", "Up to 1 year", "1-3 years", "More than 3 years"])},
    "tech_exp": {
        "uz": ("Maishiy texnika yoki elektronika do'konida ishlaganmisiz?", ["Ha", "Yo'q"]),
        "ru": ("Работали ли вы в магазине бытовой техники или электроники?", ["Да", "Нет"]),
        "en": ("Have you worked in a home appliance or electronics store?", ["Yes", "No"])},
    "jobs_year": {
        "uz": ("So'nggi 1 yilda nechta ish joyida ishlagansiz?", ["0-1", "2", "3 va undan ko'p"]),
        "ru": ("На скольких местах работы вы работали за последний год?", ["0-1", "2", "3 и более"]),
        "en": ("How many jobs have you had in the last year?", ["0-1", "2", "3 or more"])},
    "last_job": {
        "uz": ("So'nggi ish joyingiz haqida yozing: kompaniya, lavozim, qancha ishlagansiz, nima bilan shug'ullangansiz. Ishlamagan bo'lsangiz, «ishlamaganman» deb yozing.", None),
        "ru": ("Напишите о последнем месте работы: компания, должность, сколько проработали, чем занимались. Если не работали, напишите «не работал(а)».", None),
        "en": ("Tell us about your last job: company, position, how long you worked, what you did. If you have not worked, write “not worked”.", None)},
    "reason": {
        "uz": ("So'nggi ish joyidan ketishingizning (yoki ketmoqchi bo'lishingizning) asosiy sababi?",
               ["O'sish, boshqa ish formati", "Ko'chish, o'qish, oila", "Grafik mos kelmadi", "Kam to'lashdi, kechiktirishdi",
                "Rahbar yoki jamoa bilan nizo", "Jarimalar, bosim", "Qisqartirishdi, do'kon yopildi", "Bu birinchi ish joyim", "Boshqa"]),
        "ru": ("Главная причина ухода (или желания уйти) с последнего места работы?",
               ["Рост, другой формат работы", "Переезд, учёба, семья", "Не подошёл график", "Мало платили, задерживали",
                "Конфликт с руководителем или коллективом", "Штрафы, давление", "Сократили, магазин закрылся", "Это моё первое место работы", "Другое"]),
        "en": ("What was the main reason you left (or want to leave) your last job?",
               ["Growth, a different work format", "Relocation, studies, family", "The schedule did not suit me", "Low or delayed pay",
                "Conflict with a manager or the team", "Fines, pressure", "Laid off, the store closed", "This is my first job", "Other"])},
    "reason_text": {
        "uz": ("Bir-ikki gap bilan yozing: aynan nima bo'lgan va o'sha joyda nimani o'zgartirgan bo'lardingiz?", None),
        "ru": ("Напишите в одном-двух предложениях: что именно произошло и что бы вы изменили на том месте?", None),
        "en": ("In one or two sentences: what exactly happened, and what would you have changed there?", None)},
    "reference": {
        "uz": ("Sobiq rahbaringizga tavsiya uchun qo'ng'iroq qilsak bo'ladimi?", ["Ha, kontakt beraman", "Yo'q", "Tegishli emas, tajriba yo'q"]),
        "ru": ("Можно ли позвонить вашему бывшему руководителю за рекомендацией?", ["Да, дам контакт", "Нет", "Не применимо, опыта нет"]),
        "en": ("May we call your former manager for a reference?", ["Yes, I will give a contact", "No", "Not applicable, no experience"])},
    "other_jobs": {
        "uz": ("Hozir boshqa kompaniyalarga ham ish bo'yicha murojaat qilganmisiz?",
               ["Yo'q, faqat Texnomartga", "Ha, boshqa joylarga ham rezyume yuborganman",
                "Ha, boshqa kompaniyalarda suhbatlarga boryapman", "Boshqa kompaniyadan taklif (offer) olganman"]),
        "ru": ("Откликались ли вы сейчас на вакансии в других компаниях?",
               ["Нет, только в Texnomart", "Да, отправил(а) резюме и в другие компании",
                "Да, хожу на собеседования в другие компании", "Уже есть предложение (оффер) от другой компании"]),
        "en": ("Have you applied to other companies as well?",
               ["No, only to Texnomart", "Yes, I have sent my CV to other companies",
                "Yes, I am going to interviews at other companies", "I already have an offer from another company"])},
    "other_jobs_where": {
        "uz": ("Qaysi kompaniyalar va qaysi lavozimlar? Qaysi bosqichdasiz?", None),
        "ru": ("В какие компании и на какие должности? На каком вы этапе?", None),
        "en": ("Which companies and positions? What stage are you at?", None)},
    "calc_change": {
        "uz": ("1-masala. Xarid 3 740 000 so'm, mijoz 5 000 000 so'm berdi. Qaytim qancha (so'mda)?", None),
        "ru": ("Задача 1. Покупка на 3 740 000 сум, клиент дал 5 000 000 сум. Сколько сдачи (в сумах)?", None),
        "en": ("Task 1. A purchase costs 3,740,000 UZS and the customer paid 5,000,000 UZS. How much change (in UZS)?", None)},
    "calc_discount": {
        "uz": ("2-masala. Televizor 4 800 000 so'm turadi, chegirma 10%. Mijoz qancha to'laydi (so'mda)?", None),
        "ru": ("Задача 2. Телевизор стоит 4 800 000 сум, скидка 10%. Сколько заплатит клиент (в сумах)?", None),
        "en": ("Task 2. A TV costs 4,800,000 UZS with a 10% discount. How much will the customer pay (in UZS)?", None)},
    "calc_total": {
        "uz": ("3-masala. Mijoz 3 ta tovar oldi: 1 250 000, 899 000 va 349 000 so'm. Jami qancha to'laydi (so'mda)?", None),
        "ru": ("Задача 3. Клиент купил 3 товара: 1 250 000, 899 000 и 349 000 сум. Сколько всего он заплатит (в сумах)?", None),
        "en": ("Task 3. A customer bought 3 items: 1,250,000, 899,000 and 349,000 UZS. What is the total (in UZS)?", None)},
    "cash_shortage": {
        "uz": ("Smena oxirida kassada 200 000 so'm kam chiqdi. Qadamma-qadam nima qilasiz?", None),
        "ru": ("В конце смены в кассе не хватает 200 000 сум. Что вы будете делать, шаг за шагом?", None),
        "en": ("At the end of your shift the cash desk is 200,000 UZS short. What do you do, step by step?", None)},
    "needs": {
        "uz": ("Mijoz oilasi uchun muzlatgich tanlayapti. Eng to'g'ri modelni topish uchun unga qanday savollar berasiz? Kamida 3 ta savol yozing.", None),
        "ru": ("Клиент выбирает холодильник для семьи. Какие вопросы вы ему зададите, чтобы подобрать подходящую модель? Напишите не менее 3 вопросов.", None),
        "en": ("A customer is choosing a refrigerator for their family. What questions will you ask to find the right model? Write at least 3 questions.", None)},
    "objection": {
        "uz": ("Mijoz muzlatgich oldida: «Qimmat ekan, o'ylab ko'raman» dedi. Siz nima deb javob berasiz? Mijozga aytadigan gapingizni yozing.", None),
        "ru": ("Клиент у холодильника говорит: «Дорого, я подумаю». Что вы ответите? Напишите, что скажете клиенту.", None),
        "en": ("A customer at the refrigerator says: “It's expensive, I'll think about it.” What do you answer? Write what you would say.", None)},
    "conflict": {
        "uz": ("Mijoz sotib olgan texnikasi bilan qaytib keldi va norozi: «U nosoz, siz meni aldadingiz!» Qadamma-qadam nima qilasiz?", None),
        "ru": ("Клиент вернулся с купленной техникой и недоволен: «Она неисправна, вы меня обманули!» Что вы будете делать, шаг за шагом?", None),
        "en": ("A customer comes back with the appliance they bought and is upset: “It's faulty, you cheated me!” What do you do, step by step?", None)},
    "sjt_cash_honesty": {
        "uz": ("Vaziyat: smena oxirida kassada 150 000 so'm ortiqcha pul chiqdi. Nima qilasiz?",
               ["Jim turaman: ortiqcha pul zarar emas", "Rahbarga xabar beraman va cheklarni tekshirib sababini aniqlayman",
                "Ortiqchasini olib qo'yaman, keyin kam chiqsa to'ldirish uchun ishlataman", "Hamkasblarga aytaman, o'rtada bo'lib olamiz"]),
        "ru": ("Ситуация: в конце смены в кассе оказалось на 150 000 сум больше. Что вы сделаете?",
               ["Промолчу: лишние деньги не убыток", "Сообщу руководителю и проверю чеки, чтобы найти причину",
                "Оставлю излишек себе, чтобы потом покрыть возможную недостачу", "Скажу коллегам, поделим между собой"]),
        "en": ("Situation: at the end of your shift the cash desk has 150,000 UZS too much. What do you do?",
               ["Say nothing: extra money is not a loss", "Tell the manager and check the receipts to find the reason",
                "Keep the surplus to cover a possible shortage later", "Tell colleagues and split it among ourselves"])},
    "sjt_cash_queue": {
        "uz": ("Vaziyat: kassada navbat uzun, mijoz shoshib baqiryapti: «Tezroq bo'ling!» Nima qilasiz?",
               ["Men ham baqirib javob qaytaraman", "Xotirjam uzr so'rayman, ishni tezlashtiraman va kerak bo'lsa yordam chaqiraman",
                "Unga e'tibor bermayman", "Tezroq bo'lish uchun summalarni tekshirmay hisoblayman"]),
        "ru": ("Ситуация: на кассе длинная очередь, клиент торопится и кричит: «Быстрее!» Что вы сделаете?",
               ["Отвечу ему тем же тоном", "Спокойно извинюсь, ускорюсь и при необходимости позову на помощь",
                "Не буду обращать внимания", "Чтобы было быстрее, буду считать суммы не проверяя"]),
        "en": ("Situation: the queue at the cash desk is long and a customer in a hurry shouts: “Faster!” What do you do?",
               ["Shout back", "Calmly apologise, speed up and call for help if needed",
                "Ignore the customer", "To be faster, count amounts without double-checking"])},
    "sjt_customer": {
        "uz": ("Vaziyat: mijoz arzon telefon so'rayapti. Sizda bonusi yuqori bo'lgan qimmatroq model ham bor. Nima qilasiz?",
               ["Eng qimmat modelni tavsiya qilaman: bonusim ko'proq bo'ladi", "Mijoz byudjetiga mos modelni ko'rsataman va ustunliklarini tushuntiraman",
                "Ikkala variantni ko'rsataman, tanlovni mijozga qoldiraman", "Mijoz nima so'rasa, shuni beraman, ortiqcha gapirmayman"]),
        "ru": ("Ситуация: клиент просит недорогой телефон. У вас есть более дорогая модель с высоким бонусом. Что вы сделаете?",
               ["Порекомендую самую дорогую модель: мой бонус будет больше", "Покажу модель по бюджету клиента и объясню её преимущества",
                "Покажу оба варианта, выбор оставлю клиенту", "Дам то, что просит клиент, лишнего говорить не буду"]),
        "en": ("Situation: a customer asks for a cheap phone. You also have a pricier model with a higher bonus. What do you do?",
               ["Recommend the most expensive model: my bonus will be bigger", "Show a model within the customer's budget and explain its advantages",
                "Show both options and leave the choice to the customer", "Give what the customer asks for and say nothing extra"])},
    "sjt_team": {
        "uz": ("Vaziyat: kassada navbat uzayib ketdi, hamkasbingiz yolg'iz qoldi, sizda esa hozir mijoz yo'q. Nima qilasiz?",
               ["Mijozim yo'q, demak bu mening ishim emas", "Darhol yordamga boraman: kassaga o'taman yoki mijozlarni boshqa kassaga yo'naltiraman",
                "Faqat so'rashsa yordam beraman", "Rahbarga xabar beraman va o'z joyimda qolaman"]),
        "ru": ("Ситуация: на кассе выросла очередь, коллега остался один, а у вас сейчас нет клиентов. Что вы сделаете?",
               ["У меня нет клиентов, значит, это не моё дело", "Сразу пойду на помощь: встану на кассу или направлю клиентов на другую кассу",
                "Помогу, только если попросят", "Сообщу руководителю и останусь на своём месте"]),
        "en": ("Situation: the queue at the cash desk has grown, your colleague is alone, and you have no customers right now. What do you do?",
               ["I have no customers, so it is not my job", "Go and help right away: take a till or direct customers to another till",
                "Help only if asked", "Tell the manager and stay at my place"])},
    "sjt_learn": {
        "uz": ("Vaziyat: do'konga yangi model yoki yangi kassa dasturi keldi, siz uni bilmaysiz, mijoz esa kutyapti. Nima qilasiz?",
               ["Taxminan o'zim o'ylab javob beraman", "Ko'rsatma va ustozdan o'rganaman, smenadan oldin ko'rib chiqaman",
                "Hamkasbdan so'rayman, keyin o'zim ham o'qib chiqaman", "Mijozga «bilmayman» deb, boshqa xodimga yo'naltiraman"]),
        "ru": ("Ситуация: в магазин пришла новая модель или новая кассовая программа, вы её не знаете, а клиент ждёт. Что вы сделаете?",
               ["Отвечу приблизительно, как сам(а) думаю", "Изучу инструкцию и спрошу наставника, разберусь до смены",
                "Спрошу коллегу, потом изучу сам(а)", "Скажу клиенту «не знаю» и направлю к другому сотруднику"]),
        "en": ("Situation: a new model or a new till program has arrived, you do not know it, and a customer is waiting. What do you do?",
               ["Answer roughly, from my own guess", "Study the manual and ask the mentor, and learn it before my shift",
                "Ask a colleague, then study it myself", "Tell the customer “I don't know” and pass them to another employee"])},
    "sjt_stress": {
        "uz": ("Vaziyat: soat 19:00, do'konda mijozlar ko'p, kassa ishlamay qoldi, rahbar hozir yo'q. Nima qilasiz?",
               ["Hech narsa qilmayman, rahbar kelishini kutaman", "Mijozlarni ogohlantiraman, rahbar yoki texnik xodimni chaqiraman, mijozlarni boshqa kassaga yo'naltiraman",
                "Xotirjam turaman va mijozlardan biroz kutishni so'rayman", "Mijozlarga «kassa buzilgan, men aybdor emasman» deyman"]),
        "ru": ("Ситуация: 19:00, в магазине много клиентов, касса перестала работать, руководителя нет. Что вы сделаете?",
               ["Ничего не буду делать, подожду руководителя", "Предупрежу клиентов, вызову руководителя или техника, направлю клиентов на другую кассу",
                "Буду спокойно стоять и попрошу клиентов немного подождать", "Скажу клиентам: «касса сломана, я не виноват(а)»"]),
        "en": ("Situation: it is 19:00, the store is full of customers, the till has stopped working, and the manager is away. What do you do?",
               ["Do nothing and wait for the manager", "Warn customers, call the manager or a technician, direct customers to another till",
                "Stand calmly and ask customers to wait a little", "Tell customers “the till is broken, it's not my fault”"])},
    "late": {
        "uz": ("Smenaga kechikayotganingizni tushundingiz. Qanday harakat qilasiz?",
               ["Oldindan rahbarga xabar beraman va imkon qadar tez yetib boraman", "Qachon yetsam, o'shanda kelaman, hamkasblarga yozaman",
                "Joyida tushuntiraman", "Bu qo'rqinchli emas, do'konga zarar yo'q"]),
        "ru": ("Вы поняли, что опаздываете на смену. Как вы поступите?",
               ["Заранее предупрежу руководителя и приеду как можно быстрее", "Приеду, когда доберусь, напишу коллегам",
                "Объясню на месте", "Это не страшно, магазину вреда нет"]),
        "en": ("You realise you will be late for your shift. What do you do?",
               ["Warn my manager in advance and arrive as fast as I can", "Arrive whenever I get there and message colleagues",
                "Explain once I am there", "It is not a big deal, the store is not harmed"])},
    "motive": {
        "uz": ("Ishda siz uchun eng muhimi nima?",
               ["Daromad va bonus", "O'qish va karyera o'sishi", "Barqarorlik va rasmiy ish haqi", "Qulay grafik",
                "Hozircha boshqa ish qidiryapman, bu vaqtinchalik"]),
        "ru": ("Что для вас важнее всего в работе?",
               ["Доход и бонус", "Обучение и карьерный рост", "Стабильность и официальная зарплата", "Удобный график",
                "Пока ищу другую работу, это временно"]),
        "en": ("What matters most to you at work?",
               ["Income and bonus", "Training and career growth", "Stability and an official salary", "A convenient schedule",
                "I am looking for another job, this is temporary"])},
}

# Варианты текста для конкретной должности (1 = кассир). Порядок и число вариантов ответа те же.
Q_POS = {
    "health": {1: {
        "uz": ("Kassir ishi o'tirib ishlanadi: kun bo'yi kompyuter va kassa oldida, muddatli to'lovlarni rasmiylashtirish va to'lovlarni qabul qilish. Sog'lig'ingiz shunday tartibda ishlashga imkon beradimi?",
               ["Ha, cheklovlar yo'q", "Ba'zi cheklovlar bor", "Yo'q, bunday ish menga to'g'ri kelmaydi"]),
        "ru": ("Работа кассира сидячая: весь день за компьютером и кассой, оформление рассрочек и приём оплат. Позволяет ли вам здоровье работать в таком режиме?",
               ["Да, ограничений нет", "Есть некоторые ограничения", "Нет, такая работа мне не подходит"]),
        "en": ("A cashier's work is sedentary: the whole day at a computer and till, arranging installment plans and accepting payments. Does your health allow you to work this way?",
               ["Yes, no restrictions", "I have some restrictions", "No, this kind of work does not suit me"])}},
    "workload": {1: {
        "uz": ("Ish hajmi katta: muddatli to'lovlarni rasmiylashtirish, to'lovlarni qabul qilish, hujjatlar va kassa bilan ishlash, kun davomida ko'p mijoz. Shunday hajm sizga to'g'ri keladimi?",
               ["Ha, ko'p ishlashga tayyorman", "Tayyorman, lekin sharoit va yordam muhim", "Menga qiyin bo'ladi"]),
        "ru": ("Объём работы большой: оформление рассрочек, приём оплат, работа с документами и кассой, много клиентов в течение дня. Подходит ли вам такой объём?",
               ["Да, готов(а) много работать", "Готов(а), но важны условия и помощь", "Мне будет тяжело"]),
        "en": ("The workload is large: arranging installment plans, accepting payments, working with documents and the till, many customers during the day. Does this suit you?",
               ["Yes, I am ready to work a lot", "I am ready, but conditions and support matter", "It will be hard for me"])}},
}

UI = {
    "choose_lang": {l: "Tilni tanlang · Выберите язык · Choose language" for l in LANGS},
    "greeting": {
        "uz": "Assalomu alaykum! Bu %(company)s kompaniyasidagi vakansiyalar (sotuvchi-konsultant, kassir) uchun anketa.\n\nBiz taklif qilamiz:\n%(perks)s\n\nShartlar:\n- %(training)s\n- Grafik: %(schedule)s\n\nAnketa taxminan 15 daqiqa oladi. Iltimos, rost va o'z so'zlaringiz bilan javob bering. Chatda oldingi savolga qaytish uchun /orqaga ni yozing.\n\nAnketani boshlash tugmasini bosib, shaxsiy ma'lumotlaringiz, javoblaringiz va selfie suratingiz ishga qabul qilish maqsadida qayta ishlanishiga rozilik bildirasiz.",
        "ru": "Здравствуйте! Это анкета на вакансии компании %(company)s (продавец-консультант, кассир).\n\nМы предлагаем:\n%(perks)s\n\nУсловия:\n- %(training)s\n- График: %(schedule)s\n\nАнкета занимает около 15 минут. Пожалуйста, отвечайте честно и своими словами. В чате вернуться к предыдущему вопросу можно командой /orqaga.\n\nНажимая кнопку начала анкеты, вы соглашаетесь на обработку ваших персональных данных, ответов и селфи в целях трудоустройства.",
        "en": "Hello! This is the application form for vacancies at %(company)s (sales consultant, cashier).\n\nWe offer:\n%(perks)s\n\nTerms:\n- %(training)s\n- Schedule: %(schedule)s\n\nThe form takes about 15 minutes. Please answer honestly and in your own words. In chat, send /orqaga to go back to the previous question.\n\nBy pressing the start button you consent to the processing of your personal data, answers and selfie for hiring purposes."},
    "btn_web": {"uz": "📝 Anketani to'ldirish", "ru": "📝 Заполнить анкету", "en": "📝 Fill in the form"},
    "btn_chat": {"uz": "💬 Chatda to'ldirish", "ru": "💬 Заполнить в чате", "en": "💬 Fill in here in chat"},
    "thanks": {"uz": "Rahmat! Anketa yuborildi. Rekruter siz ko'rsatgan raqam orqali bog'lanadi.",
               "ru": "Спасибо! Анкета отправлена. Рекрутер свяжется с вами по указанному номеру.",
               "en": "Thank you! Your application has been sent. A recruiter will contact you at the number you provided."},
    "press_start": {"uz": "Anketani boshlash uchun /start ni bosing.", "ru": "Чтобы начать анкету, нажмите /start.", "en": "Press /start to begin."},
    "use_buttons": {"uz": "Iltimos, savol ostidagi tugma orqali variantni tanlang.", "ru": "Пожалуйста, выберите вариант кнопкой под вопросом.",
                    "en": "Please choose an option using the buttons below the question."},
    "need_number": {"uz": "Iltimos, raqam kiriting.", "ru": "Пожалуйста, введите число.", "en": "Please enter a number."},
    "bad_phone": {"uz": "Telefon raqam noto'g'ri. Masalan: +998 90 123 45 67", "ru": "Неверный номер телефона. Например: +998 90 123 45 67",
                  "en": "Invalid phone number. Example: +998 90 123 45 67"},
    "bad_age": {"uz": "Yoshni to'g'ri kiriting (16-70).", "ru": "Введите возраст правильно (16-70).", "en": "Enter a valid age (16-70)."},
    "no_back": {"uz": "Orqaga qaytib bo'lmaydi.", "ru": "Назад вернуться нельзя.", "en": "You cannot go back."},
    # --- Mini App
    "title": {"uz": "Ishga qabul anketasi", "ru": "Анкета кандидата", "en": "Job application"},
    "hero_title": {"uz": "Texnomart jamoasiga qo'shiling", "ru": "Присоединяйтесь к команде Texnomart", "en": "Join the Texnomart team"},
    "hero_sub": {"uz": "Vakansiyalar: sotuvchi-konsultant, kassir", "ru": "Вакансии: продавец-консультант, кассир",
                 "en": "Vacancies: sales consultant, cashier"},
    "st_year": {"uz": "yildan beri", "ru": "работаем с", "en": "since"},
    "st_store": {"uz": "do'kon", "ru": "магазинов", "en": "stores"},
    "st_staff": {"uz": "xodim", "ru": "сотрудников", "en": "employees"},
    "terms": {"uz": "Ish tartibi", "ru": "Условия работы", "en": "Job terms"},
    "perks": {"uz": "Biz taklif qilamiz", "ru": "Мы предлагаем", "en": "We offer"},
    "t_schedule": {"uz": "Grafik", "ru": "График", "en": "Schedule"},
    "t_income": {"uz": "Daromad", "ru": "Доход", "en": "Income"},
    "t_noexp": {"uz": "Tajriba shart emas, ustoz bilan o'rgatamiz", "ru": "Опыт не обязателен, обучаем с наставником",
                "en": "No experience required, we train you with a mentor"},
    "hint_time": {"uz": "Anketa taxminan 15 daqiqa oladi. Rost va o'z so'zlaringiz bilan javob bering.",
                  "ru": "Анкета занимает около 15 минут. Отвечайте честно и своими словами.",
                  "en": "The form takes about 15 minutes. Answer honestly and in your own words."},
    "consent": {"uz": "Shaxsiy ma'lumotlarim, javoblarim va selfie suratim ishga qabul qilish maqsadida qayta ishlanishiga roziman.",
                "ru": "Я согласен(на) на обработку моих персональных данных, ответов и селфи в целях трудоустройства.",
                "en": "I consent to the processing of my personal data, answers and selfie for hiring purposes."},
    "consent_err": {"uz": "Davom etish uchun rozilik belgisini qo'ying.", "ru": "Чтобы продолжить, отметьте согласие.",
                    "en": "Please tick the consent box to continue."},
    "start": {"uz": "Boshlash", "ru": "Начать", "en": "Start"},
    "resume": {"uz": "Davom ettirish (saqlangan javoblar)", "ru": "Продолжить (сохранённые ответы)", "en": "Continue (saved answers)"},
    "warn_tg": {"uz": "Anketani Telegram ichida, bot tugmasi orqali oching. Aks holda yuborib bo'lmaydi.",
                "ru": "Откройте анкету внутри Telegram, кнопкой бота. Иначе отправить её не получится.",
                "en": "Open this form inside Telegram using the bot's button. Otherwise it cannot be sent."},
    "warn_api": {"uz": "Server manzili sozlanmagan.", "ru": "Адрес сервера не настроен.", "en": "Server address is not configured."},
    "next": {"uz": "Davom etish", "ru": "Далее", "en": "Next"},
    "back": {"uz": "Orqaga", "ru": "Назад", "en": "Back"},
    "submit": {"uz": "Yuborish", "ru": "Отправить", "en": "Submit"},
    "sending": {"uz": "Yuborilmoqda...", "ru": "Отправляем...", "en": "Sending..."},
    "step": {"uz": "Savol {n} / {t}", "ru": "Вопрос {n} из {t}", "en": "Question {n} of {t}"},
    "choose_opt": {"uz": "Variantni tanlang.", "ru": "Выберите вариант.", "en": "Please choose an option."},
    "write_answer": {"uz": "Javob yozing.", "ru": "Напишите ответ.", "en": "Please write an answer."},
    "hint_long": {"uz": "O'z so'zlaringiz bilan batafsil yozing.", "ru": "Напишите подробно, своими словами.", "en": "Write in detail, in your own words."},
    "fio_err": {"uz": "Ism-familiyani to'liq yozing.", "ru": "Напишите имя и фамилию полностью.", "en": "Please write your full name."},
    "photo_block": {"uz": "Surat", "ru": "Фото", "en": "Photo"},
    "photo_title": {"uz": "Selfie yuboring", "ru": "Сделайте селфи", "en": "Take a selfie"},
    "photo_hint": {"uz": "Yuzingiz aniq ko'rinsin. Surat faqat rekruterga yuboriladi.",
                   "ru": "Лицо должно быть хорошо видно. Фото получит только рекрутер.",
                   "en": "Your face should be clearly visible. Only the recruiter will receive the photo."},
    "take_photo": {"uz": "📸 Suratga olish", "ru": "📸 Сделать снимок", "en": "📸 Take photo"},
    "retake": {"uz": "Qayta olish", "ru": "Переснять", "en": "Retake"},
    "use_phone_cam": {"uz": "Kamera bilan suratga olish", "ru": "Снять на камеру телефона", "en": "Use the phone camera"},
    "cam_denied": {"uz": "Kameraga ruxsat berilmadi yoki kamera yo'q. Telefon kamerasi orqali oling.",
                   "ru": "Нет доступа к камере или камеры нет. Снимите через камеру телефона.",
                   "en": "Camera access was denied or there is no camera. Use the phone camera instead."},
    "cam_unsupported": {"uz": "Brauzer kamerani qo'llamaydi.", "ru": "Браузер не поддерживает камеру.", "en": "This browser does not support the camera."},
    "cam_notready": {"uz": "Kamera hali tayyor emas.", "ru": "Камера ещё не готова.", "en": "The camera is not ready yet."},
    "photo_need": {"uz": "Iltimos, selfie oling.", "ru": "Пожалуйста, сделайте селфи.", "en": "Please take a selfie."},
    "img_err": {"uz": "Rasmni o'qib bo'lmadi, qayta urinib ko'ring.", "ru": "Не удалось прочитать фото, попробуйте ещё раз.",
                "en": "Could not read the image, please try again."},
    "slot_block": {"uz": "Oxirgi qadam", "ru": "Последний шаг", "en": "Last step"},
    "slot_title": {"uz": "Suhbat uchun qaysi vaqt qulay?", "ru": "Какое время удобно для собеседования?", "en": "What time suits you for an interview?"},
    "slot_need": {"uz": "Qulay vaqtni tanlang.", "ru": "Выберите удобное время.", "en": "Please choose a time."},
    "done_title": {"uz": "Rahmat!", "ru": "Спасибо!", "en": "Thank you!"},
    "done_text": {"uz": "Anketangiz yuborildi. Rekruter siz ko'rsatgan raqam orqali bog'lanadi.",
                  "ru": "Анкета отправлена. Рекрутер свяжется с вами по указанному номеру.",
                  "en": "Your application has been sent. A recruiter will contact you at the number you provided."},
    "close": {"uz": "Yopish", "ru": "Закрыть", "en": "Close"},
    "err_telegram": {"uz": "Anketani Telegram ichida, bot tugmasi orqali oching.", "ru": "Откройте анкету внутри Telegram, кнопкой бота.",
                     "en": "Open this form inside Telegram using the bot's button."},
    "err_rate": {"uz": "Juda tez. Bir necha soniyadan keyin qayta urinib ko'ring.", "ru": "Слишком быстро. Повторите через несколько секунд.",
                 "en": "Too fast. Please try again in a few seconds."},
    "err_data": {"uz": "Ma'lumotlarda xatolik. Barcha savollarga javob berilganini tekshiring.",
                 "ru": "Ошибка в данных. Проверьте, что вы ответили на все вопросы.",
                 "en": "There is a problem with the data. Check that all questions are answered."},
    "err_photo": {"uz": "Selfie noto'g'ri. Qayta oling.", "ru": "Проблема с селфи. Сделайте снимок заново.", "en": "There is a problem with the selfie. Please retake it."},
    "err_server": {"uz": "Serverda xatolik. Birozdan keyin qayta urinib ko'ring.", "ru": "Ошибка на сервере. Повторите чуть позже.",
                   "en": "Server error. Please try again a bit later."},
    "err_big": {"uz": "Surat juda katta. Qayta oling.", "ru": "Фото слишком большое. Сделайте снимок заново.", "en": "The photo is too large. Please retake it."},
    "err_network": {"uz": "Internet aloqasi yo'q yoki server javob bermadi. Javoblaringiz saqlangan, qayta urinib ko'ring.",
                    "ru": "Нет интернета или сервер не ответил. Ответы сохранены, попробуйте ещё раз.",
                    "en": "No internet or the server did not respond. Your answers are saved, please try again."},
    "err_generic": {"uz": "Yuborib bo'lmadi. Qayta urinib ko'ring.", "ru": "Не удалось отправить. Попробуйте ещё раз.", "en": "Could not send. Please try again."},
}


def lang_ok(lang):
    return lang if lang in LANGS else "uz"


def ui(key, lang):
    return UI[key][lang_ok(lang)]


def _q(key, lang, pos=0):
    return Q_POS.get(key, {}).get(pos, Q[key])[lang_ok(lang)]


def q_text(key, lang, pos=0):
    return _q(key, lang, pos)[0]


def q_options(key, lang, pos=0):
    return _q(key, lang, pos)[1]


def block(bid, lang):
    return BLOCKS[bid][lang_ok(lang)]


def greeting(lang, company):
    lang = lang_ok(lang)
    return UI["greeting"][lang] % {"company": company, "training": JOB_TR["training"][lang],
                                   "schedule": JOB_TR["schedule"][lang], "perks": "\n".join("- " + p for p in JOB_TR["perks"][lang])}
