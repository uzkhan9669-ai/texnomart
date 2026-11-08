"""Google Tablitsa bilan sinxronlash (Google Apps Script veb-ilova orqali, qo'shimcha kutubxona kerak emas).

Muhit o'zgaruvchilari:
    SHEETS_URL     Apps Script veb-ilovasining manzili (https://script.google.com/macros/s/.../exec)
    SHEETS_SECRET  maxfiy so'z (apps_script.gs dagi SECRET bilan bir xil bo'lishi kerak)
Agar SHEETS_URL bo'sh bo'lsa, sinxronlash o'chiq turadi va bot odatdagidek ishlaydi.
Jadvaldagi kalit: Telegram ID. Nomzod qayta to'ldirsa yoki holati o'zgarsa, qator yangilanadi.
"""
import json
import logging
import os
import urllib.request

log = logging.getLogger("texnomart-bot.sheets")


def enabled():
    return bool(os.environ.get("SHEETS_URL"))


def build_payload(row):
    """row: store dan olingan nomzod yozuvi (lug'at)."""
    answers = json.loads(row["answers"] or "{}")
    return {
        "secret": os.environ.get("SHEETS_SECRET", ""),
        "tg_id": row["tg_id"],
        "ts": row["ts"],
        "fio": row["fio"],
        "age": answers.get("age", ""),
        "phone": row["phone"],
        "username": row["username"] or "",
        "district": answers.get("district", ""),
        "pct": row["pct"],
        "verdict": row["verdict"],
        "red": row["red"],
        "yellow": row["yellow"],
        "status": row["status"],
        "flags": row["flags"] or "",
        "answers": row["answers"],
    }


def push_row(row, timeout=20):
    """Qatorni jadvalga yuboradi. Muvaffaqiyatli bo'lsa True. Xatolik botni to'xtatmaydi."""
    url = os.environ.get("SHEETS_URL")
    if not url:
        return False
    try:
        data = json.dumps(build_payload(row), ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "text/plain;charset=utf-8"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        ok = bool(json.loads(body).get("ok"))
        if not ok:
            log.error("Google Tablitsa rad etdi: %s", body[:200])
        return ok
    except Exception:
        log.exception("Google Tablitsaga yuborib bo'lmadi")
        return False
