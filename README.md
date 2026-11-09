# Texnomart: nomzodlarni baholash boti + Mini App

Oqim: /start -> Mini App tugmasi -> anketa + selfie -> bot baholaydi -> rekruterga karta (selfie, ball, flaglar, tugmalar) -> Google Tablitsa.

## 1. Railway (bot)
1. Repozitoriyni Railway'ga ulang (fayllar: bot.py, webapi.py, scoring.py, store.py, sheets.py).
2. Variables: BOT_TOKEN, RECRUITER_IDS, WEBAPP_URL, WEBAPP_ORIGIN, SHEETS_URL, SHEETS_SECRET.
3. Settings -> Networking -> **Generate Domain** (bot HTTP serverni PORT da ochadi; Procfile: `web: python bot.py`).
4. Disk vaqtinchalik: candidates.db qayta ishga tushganda o'chishi mumkin. Doimiy nusxa - Google Tablitsa (yoki Railway Volume + DB_PATH=/data/candidates.db).
5. Bitta token = bitta ishlayotgan nusxa.

## 2. Mini App (GitHub Pages)
1. `python miniapp/build_miniapp.py https://<railway-domen>/api/submit` -> miniapp/index.html tayyor.
2. index.html ni **alohida (ochiq) repozitoriyga** yuklang va Settings -> Pages ni yoqing. Botning kodini ochiq repoga qo'ymang.
3. Pages manzilini WEBAPP_URL ga yozing; @BotFather da botning domenini sozlash shart emas (tugma orqali ochiladi).
4. scoring.py o'zgarsa, build_miniapp.py ni qayta ishga tushiring. Baholash kalitlari index.html ga tushmaydi.

## 3. Google Tablitsa
apps_script.gs ni jadvalga joylang, Web app sifatida e'lon qiling, URL -> SHEETS_URL, SECRET -> SHEETS_SECRET.

## 4. Maxfiylik
Selfie va oilaviy ahvol - shaxsiy ma'lumot. Rozilik anketada olinadi. Oilaviy ahvol baholashga ta'sir qilmaydi va jadvalga yuborilmaydi; selfie faqat Telegram file_id sifatida saqlanadi. Qonun bo'yicha maslahatlashing.

## Rekruter buyruqlari
/reyting, /songgi, /stat, /csv, /nomzod ID (/n_ID), /holat ID status
