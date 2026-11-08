"""Telegram-bot: Mini App'dan kelgan anketa ma'lumotlarini PDF qilib yuborish."""
import asyncio
import json
import logging
import os
import re
import base64
from io import BytesIO

from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import store

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("texnomart-bot")

TOKEN = os.environ.get("BOT_TOKEN", "8698734594:AAHk0G1aQo_2MAFFiPAFJNShjGvSMoKBTG0")
RECRUITERS = {int(x) for x in re.split(r"[\s,;]+", os.environ.get("RECRUITER_IDS", "546403983")) if x.strip().isdigit()}

MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://uzkhan9669-ai.github.io/texnomart/")

def generate_pdf_report(data: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#1c1c1e'),
        spaceAfter=15
    )

    story.append(Paragraph("Texnomart — Анкета кандидата", title_style))
    story.append(Spacer(1, 10))

    photo_b64 = data.get("photo")
    if photo_b64 and "," in photo_b64:
        try:
            img_data = base64.b64decode(photo_b64.split(",")[1])
            img_io = BytesIO(img_data)
            img = RLImage(img_io, width=100, height=100)
            story.append(img)
            story.append(Spacer(1, 10))
        except Exception as e:
            log.error(f"Ошибка добавления фото в PDF: {e}")

    answers = data.get("answers", data)
    table_data = [
        ["Поле", "Ответ кандидата"],
        ["Ф.I.Sh / Имя", data.get("fio") or data.get("name") or "—"],
        ["Возраст", data.get("age") or "—"],
        ["Семейное положение", data.get("marital_status") or "—"],
        ["Телефон", data.get("phone") or "—"],
        ["Район / Город", data.get("city") or "—"],
    ]

    for k, v in answers.items():
        if k not in ["fio", "name", "age", "marital_status", "phone", "district", "city", "photo"] and not k.endswith("_i"):
            table_data.append([str(k), str(v)])

    t = Table(table_data, colWidths=[150, 360])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#ffc800')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.HexColor('#1c1c1e')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e2e8')),
    ]))
    
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer

async def handle_http_post(request):
    try:
        try:
            data = await request.json()
        except Exception:
            post_data = await request.post()
            raw_json = post_data.get("data", "{}")
            data = json.loads(raw_json)
        
        pdf_file = generate_pdf_report(data)
        fio = data.get("fio") or data.get("name") or "Nomzod"
        pdf_file.name = f"Anketa_{fio.replace(' ', '_')}.pdf"

        for rid in RECRUITERS:
            try:
                await tg_app.bot.send_document(
                    chat_id=rid,
                    document=pdf_file,
                    caption=f"📄 <b>Yangi anketa (PDF)</b>\n\n👤 F.I.Sh: <b>{fio}</b>\n📞 Tel: <b>{data.get('phone', '—')}</b>",
                    parse_mode="HTML"
                )
                pdf_file.seek(0)
            except Exception as e:
                log.error(f"Telegram orqali PDF yuborishda xatolik ({rid}): {e}")

        return web.json_response({"status": "ok"})
    except Exception as e:
        log.error(f"HTTP Webhook error: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 ANKETA", web_app=dict(url=MINI_APP_URL))
    ]])
    await update.effective_message.reply_text("Assalomu alaykum! Quyidagi tugmani bosib anketani to'ldiring:", reply_markup=markup)

tg_app = None

async def start_web_server():
    web_app = web.Application()
    web_app.router.add_post('/', handle_http_post)
    web_app.router.add_post('/webhook', handle_http_post)
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    log.info(f"HTTP Server runs on port {port}")

def main():
    global tg_app
    store.init()
    tg_app = Application.builder().token(TOKEN).build()
    
    tg_app.add_handler(CommandHandler("start", start))
    
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    
    log.info("Bot started...")
    tg_app.run_polling()

if __name__ == "__main__":
    main()
