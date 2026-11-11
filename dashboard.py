"""Веб-панель рекрутера (только стандартная библиотека). Открывается по адресу https://ДОМЕН/dashboard

Переменные окружения:
    DASHBOARD_PASSWORD   пароль для входа (не короче 8 символов). Если не задан, панель выключена.
    DASHBOARD_USERNAME   логин (по умолчанию hr)
    DASHBOARD_SECRET     секрет для подписи сессии (необязательно: по умолчанию выводится из BOT_TOKEN)
Вход: подписанная cookie (HttpOnly, Secure, SameSite=Strict) на 8 часов. После 5 неверных попыток вход
с этого адреса блокируется на 15 минут. Ответы с данными кандидатов не кэшируются.
"""
import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request

import store
from scoring import VERDICT_RU, build_profile, evaluate, position_name

log = logging.getLogger("texnomart-bot.dashboard")
SESSION_SECONDS = 8 * 3600
MAX_FAILS, FAIL_WINDOW = 5, 15 * 60
STATUS_RU = {"yangi": "Новая", "chaqirildi": "Приглашён", "zaxira": "Резерв", "rad": "Отказ", "qabul": "Принят"}
HERE = os.path.dirname(os.path.abspath(__file__))
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: blob:; frame-ancestors 'none'; base-uri 'none'")


def telegram_photo(token, file_id, timeout=15):
    """Скачивает фото по file_id через Telegram Bot API. Возвращает байты или None."""
    try:
        url = "https://api.telegram.org/bot%s/getFile?file_id=%s" % (token, urllib.parse.quote(file_id))
        with urllib.request.urlopen(url, timeout=timeout) as r:
            path = json.loads(r.read())["result"]["file_path"]
        with urllib.request.urlopen("https://api.telegram.org/file/bot%s/%s" % (token, urllib.parse.quote(path)), timeout=timeout) as r:
            return r.read(3_000_000)
    except Exception:
        log.exception("Не удалось получить фото из Telegram")
        return None


class Dashboard:
    def __init__(self, token, username=None, password=None, secret=None, on_change=None, fetch_photo=telegram_photo):
        self.token = token
        self.username = (username if username is not None else os.environ.get("DASHBOARD_USERNAME", "hr")).strip() or "hr"
        self.password = (password if password is not None else os.environ.get("DASHBOARD_PASSWORD", "")).strip()
        secret = secret if secret is not None else os.environ.get("DASHBOARD_SECRET", "")
        self.secret = (secret or hmac.new(token.encode(), b"dashboard-session", hashlib.sha256).hexdigest()).encode()
        self.on_change, self.fetch_photo = on_change, fetch_photo
        self.fails, self.lock = {}, threading.Lock()
        try:
            self.page = open(os.path.join(HERE, "dashboard.html"), "rb").read()
        except OSError:
            self.page = None

    @property
    def enabled(self):
        return len(self.password) >= 8 and self.page is not None

    @staticmethod
    def match(path):
        p = path.split("?")[0]
        return p.rstrip("/") == "/dashboard" or (p.startswith("/api/") and p != "/api/submit")

    # ---------- сессия
    def _sign(self, payload):
        return hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()

    def make_session(self, now=None):
        data = json.dumps({"sub": self.username, "exp": int(now or time.time()) + SESSION_SECONDS}, separators=(",", ":"))
        payload = base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")
        return payload + "." + self._sign(payload)

    def read_session(self, cookie_header, now=None):
        m = re.search(r"(?:^|;\s*)hr_session=([A-Za-z0-9_\-]+\.[0-9a-f]{64})", cookie_header or "")
        if not m:
            return None
        payload, sig = m.group(1).split(".", 1)
        if not hmac.compare_digest(sig, self._sign(payload)):
            return None
        try:
            data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if int(data["exp"]) < (now or time.time()) or data.get("sub") != self.username:
                return None
            return data["sub"]
        except (ValueError, KeyError, TypeError):
            return None

    # ---------- ответы
    @staticmethod
    def _json(code, obj, extra=None):
        h = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        h.update(extra or {})
        return code, h, json.dumps(obj, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def _answers(row):
        try:
            a = json.loads(row["answers"] or "{}")
            return a if isinstance(a, dict) else {}
        except ValueError:
            return {}

    def _item(self, row):
        a = self._answers(row)
        return {"id": row["id"], "fio": row["fio"] or "", "phone": row["phone"] or "", "username": row["username"] or "",
                "age": a.get("age", ""), "district": a.get("district", ""), "pos": position_name(a, short=True),
                "pct": row["pct"], "verdict": row["verdict"], "verdict_ru": VERDICT_RU.get(row["verdict"], row["verdict"]),
                "red": row["red"], "yellow": row["yellow"], "status": row["status"],
                "status_ru": STATUS_RU.get(row["status"], row["status"]), "branch": row["branch"] or "",
                "ts": row["ts"], "photo": bool(row["photo_file_id"]), "slot": a.get("slot", "")}

    # ---------- маршруты
    def handle(self, method, path, headers, body=b"", ip="", now=None):
        """Возвращает (код, заголовки, тело). headers: объект с .get()."""
        url = urllib.parse.urlsplit(path)
        p, query = url.path.rstrip("/") or "/", dict(urllib.parse.parse_qsl(url.query))
        if p == "/dashboard":
            if method != "GET":
                return self._json(405, {"error": "method"})
            if self.page is None:
                return self._json(404, {"error": "Файл dashboard.html не найден"})
            return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "Content-Security-Policy": CSP,
                         "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}, self.page
        if not self.enabled:
            return self._json(503, {"error": "Панель не настроена: задайте переменную DASHBOARD_PASSWORD (не короче 8 символов)."})
        if method == "POST" and "json" not in (headers.get("Content-Type") or ""):
            return self._json(415, {"error": "content-type"})   # защита от отправки формой с чужого сайта
        if p == "/api/login" and method == "POST":
            return self._login(body, ip, now or time.time())
        if p == "/api/logout" and method == "POST":
            return self._json(200, {"ok": True}, {"Set-Cookie": "hr_session=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict"})
        user = self.read_session(headers.get("Cookie"), now)
        if not user:
            return self._json(401, {"error": "Требуется вход"})
        if p == "/api/me" and method == "GET":
            return self._json(200, {"ok": True, "user": user, "statuses": STATUS_RU, "verdicts": VERDICT_RU})
        if p == "/api/summary" and method == "GET":
            return self._summary()
        if p == "/api/candidates" and method == "GET":
            return self._list(query)
        if p == "/api/export.csv" and method == "GET":
            return 200, {"Content-Type": "text/csv; charset=utf-8", "Cache-Control": "no-store",
                         "Content-Disposition": 'attachment; filename="kandidaty.csv"'}, store.export_csv()
        m = re.fullmatch(r"/api/candidates/(\d{1,9})(/photo|/pdf)?", p)
        if m:
            row = store.get(int(m.group(1)))
            if not row:
                return self._json(404, {"error": "Кандидат не найден"})
            if m.group(2) == "/pdf":
                return self._pdf(row) if method == "GET" else self._json(405, {"error": "method"})
            if m.group(2):
                return self._photo(row) if method == "GET" else self._json(405, {"error": "method"})
            if method == "GET":
                a = self._answers(row)
                item = self._item(row)
                item["profile"] = build_profile(a, row["ts"])
                item["flags"] = [[f[0], f[1]] for f in evaluate(a)["flags"]]
                item["history"] = [dict(h) for h in store.history(row["id"])]
                return self._json(200, item)
            if method == "POST":
                return self._update(row, body, user)
        return self._json(404, {"error": "not found"})

    def _login(self, body, ip, now):
        with self.lock:
            self.fails = {k: [t for t in v if now - t < FAIL_WINDOW] for k, v in self.fails.items()}
            self.fails = {k: v for k, v in self.fails.items() if v}
            if len(self.fails.get(ip, [])) >= MAX_FAILS or sum(len(v) for v in self.fails.values()) >= MAX_FAILS * 10:
                return self._json(429, {"error": "Слишком много попыток. Повторите через 15 минут."})
        try:
            d = json.loads(body.decode("utf-8"))
            u, pw = str(d.get("username", "")), str(d.get("password", ""))
        except (ValueError, AttributeError, UnicodeDecodeError):
            u = pw = ""
        ok = hmac.compare_digest(u.encode(), self.username.encode()) & hmac.compare_digest(pw.encode(), self.password.encode())
        if not ok:
            with self.lock:
                self.fails.setdefault(ip, []).append(now)
            time.sleep(0.3)
            return self._json(401, {"error": "Неверный логин или пароль"})
        cookie = "hr_session=%s; Path=/; Max-Age=%d; HttpOnly; Secure; SameSite=Strict" % (self.make_session(now), SESSION_SECONDS)
        return self._json(200, {"ok": True, "user": self.username}, {"Set-Cookie": cookie})

    def _summary(self):
        rows = store.all_rows()
        items = [self._item(r) for r in rows]
        count = lambda key: {k: sum(1 for i in items if i[key] == k) for k in sorted({i[key] for i in items})}
        buckets = {"85-100": 0, "70-84": 0, "45-69": 0, "0-44": 0}
        for i in items:
            buckets["85-100" if i["pct"] >= 85 else "70-84" if i["pct"] >= 70 else "45-69" if i["pct"] >= 45 else "0-44"] += 1
        risks = {}
        for r in rows:
            for f in (r["flags"] or "").split(" | "):
                if f:
                    risks[f] = risks.get(f, 0) + 1
        today = datetime.date.today()
        days = [(today - datetime.timedelta(days=n)).isoformat() for n in range(13, -1, -1)]
        per_day = {d: 0 for d in days}
        week = prev_week = 0
        for i in items:
            d = (i["ts"] or "")[:10]
            if d in per_day:
                per_day[d] += 1
            try:
                age_days = (today - datetime.date.fromisoformat(d)).days
            except ValueError:
                continue
            week += 0 <= age_days < 7
            prev_week += 7 <= age_days < 14
        comp, by_pos = {}, {}
        for r, i in zip(rows, items):
            sc = evaluate(self._answers(r))["scores"]
            for k, v in list(sc["hard"].items()) + list(sc["soft"].items()):
                comp.setdefault(k, []).append(v)
            by_pos.setdefault(i["pos"], []).append(i["pct"])
        share = lambda n: round(n * 100 / len(items)) if items else 0
        return self._json(200, {
            "daily": [[d, per_day[d]] for d in days], "week": week, "prev_week": prev_week,
            "invited_pct": share(sum(1 for i in items if i["status"] in ("chaqirildi", "qabul"))),
            "hired": sum(1 for i in items if i["status"] == "qabul"),
            "red_pct": share(sum(1 for i in items if i["red"])),
            "competencies": sorted(([k, round(sum(v) / len(v), 1), len(v)] for k, v in comp.items()), key=lambda x: x[1]),
            "pos_avg": {k: round(sum(v) / len(v)) for k, v in by_pos.items()},
            "storage": store.storage_info(),
            "total": len(items), "avg": round(sum(i["pct"] for i in items) / len(items)) if items else 0,
            "verdicts": {k: sum(1 for i in items if i["verdict"] == k) for k in ("QABUL", "ZAXIRA", "RAD")},
            "statuses": {k: sum(1 for i in items if i["status"] == k) for k in store.STATUSES},
            "positions": count("pos"), "buckets": buckets,
            "top_risks": sorted(risks.items(), key=lambda kv: -kv[1])[:6],
            "recent": sorted(items, key=lambda i: i["ts"] or "", reverse=True)[:6]})

    def _list(self, q):
        text = (q.get("q") or "").strip().lower()[:80]
        digits = re.sub(r"\D", "", text)
        out = []
        for r in store.all_rows():
            i = self._item(r)
            if q.get("verdict") and i["verdict"] != q["verdict"]:
                continue
            if q.get("status") and i["status"] != q["status"]:
                continue
            if q.get("pos") and i["pos"] != q["pos"]:
                continue
            if text and not (text in i["fio"].lower() or text in i["branch"].lower() or text in i["district"].lower()
                             or (digits and digits in re.sub(r"\D", "", i["phone"]))):
                continue
            out.append(i)
        out.sort(key=(lambda i: i["ts"] or "") if q.get("sort") == "new" else (lambda i: i["pct"]), reverse=True)
        return self._json(200, {"items": out[:500], "count": len(out)})

    def _update(self, row, body, user):
        try:
            d = json.loads(body.decode("utf-8"))
            if not isinstance(d, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "data"})
        if "status" in d:
            if d["status"] not in store.STATUSES:
                return self._json(400, {"error": "Недопустимый статус"})
            store.set_status(row["id"], d["status"], by=user)
        if "branch" in d:
            store.set_branch(row["id"], str(d["branch"]).strip()[:80])
        if self.on_change:
            try:
                self.on_change(row["id"])
            except Exception:
                log.exception("Синхронизация после изменения не удалась")
        return self._json(200, {"ok": True, "item": self._item(store.get(row["id"]))})

    def _pdf(self, row):
        try:
            import pdfgen
        except ImportError:
            return self._json(501, {"error": "PDF недоступен: не установлена библиотека reportlab"})
        a = self._answers(row)
        photo = self.fetch_photo(self.token, row["photo_file_id"]) if row["photo_file_id"] else None
        try:
            raw = pdfgen.make_pdf(a, row["ts"], row["id"], STATUS_RU.get(row["status"], row["status"]), row["username"] or "",
                                  row["branch"] or "", photo)
        except Exception:
            log.exception("Не удалось собрать PDF")
            return self._json(500, {"error": "Не удалось собрать PDF"})
        name = pdfgen.filename(a, row["id"])
        disp = "attachment; filename=\"anketa_%d.pdf\"; filename*=UTF-8''%s" % (row["id"], urllib.parse.quote(name))
        return 200, {"Content-Type": "application/pdf", "Cache-Control": "no-store", "Content-Disposition": disp,
                     "X-Content-Type-Options": "nosniff"}, raw

    def _photo(self, row):
        if not row["photo_file_id"]:
            return self._json(404, {"error": "Фото нет"})
        raw = self.fetch_photo(self.token, row["photo_file_id"])
        if not raw or raw[:3] != b"\xff\xd8\xff":
            return self._json(502, {"error": "Не удалось получить фото"})
        return 200, {"Content-Type": "image/jpeg", "Cache-Control": "private, max-age=600", "X-Content-Type-Options": "nosniff"}, raw
