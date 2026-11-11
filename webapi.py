"""HTTP-interfeys Mini App uchun (faqat standart kutubxona).

Mini App anketani (javoblar + selfie) shu yerga POST qiladi: POST /api/submit.
(tg.sendData() 4096 baytdan oshmaydi, shuning uchun selfie va uzun javoblar u orqali o'tmaydi.)

Tekshiruvlar: Telegram WebApp imzosi (initData), anketa tuzilishi, selfie (JPEG), hajm, tezlik chegarasi,
takroriy yuborishdan himoya (sid). Muhit o'zgaruvchilari: PORT, WEBAPP_ORIGIN (ruxsat etilgan manzillar, vergul bilan).
"""
import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import i18n
from scoring import QUESTIONS, applies

log = logging.getLogger("texnomart-bot.web")

MAX_BODY = 2_000_000       # so'rov hajmi (bayt)
MAX_PHOTO = 1_000_000      # selfie hajmi (bayt)
RATE_SECONDS = 5           # bir foydalanuvchidan ketma-ket yuborish oralig'i
KEEP_SECONDS = 3600        # takroriy sid larni eslab qolish muddati
SLOT_RE = re.compile(r"^\d{2}:\d{2} - \d{2}:\d{2}$")
SID_RE = re.compile(r"^[A-Za-z0-9]{6,40}$")


def verify_init_data(init_data, token, max_age=86400, now=None):
    """Telegram WebApp initData imzosini tekshiradi. To'g'ri bo'lsa foydalanuvchi lug'atini qaytaradi, aks holda None."""
    if not init_data or not token:
        return None
    try:
        data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        got = data.pop("hash", "")
        if not got:
            return None
        check = "\n".join("%s=%s" % (k, data[k]) for k in sorted(data))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, got):
            return None
        auth = int(data.get("auth_date", "0"))
        if (now if now is not None else time.time()) - auth > max_age:
            return None
        user = json.loads(data.get("user", ""))
        if not isinstance(user, dict) or not isinstance(user.get("id"), int):
            return None
        return user
    except (ValueError, TypeError):
        return None


def sanitize(a):
    """Mijozdan kelgan javoblarni tekshiradi va tozalaydi. Hamma savolga javob bo'lishi shart.
    Tanlov savollarida matn variant raqamidan qayta tiklanadi (mijozga ishonilmaydi). Noto'g'ri bo'lsa None."""
    if not isinstance(a, dict):
        return None
    out = {}
    for q in QUESTIONS:
        if not applies(q, out):   # boshqa lavozim yoki shartli savol: kutilmaydi va saqlanmaydi
            continue
        k = q["key"]
        if q["type"] == "choice":
            i = a.get(k + "_i")
            if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(q["options"]):
                return None
            out[k] = q["options"][i]
            out[k + "_i"] = i
        else:
            t = a.get(k)
            if not isinstance(t, str):
                return None
            t = t.strip()[:1500]
            if not t:
                return None
            out[k] = t
    if not 9 <= len(re.sub(r"\D", "", out["phone"])) <= 12:
        return None
    age = re.sub(r"\D", "", out["age"])[:3]
    if not age or not 14 <= int(age) <= 80:
        return None
    return out


def decode_photo(s):
    """data:image/jpeg;base64,... yoki sof base64 qatorni JPEG baytlariga aylantiradi. Noto'g'ri bo'lsa None."""
    if not isinstance(s, str):
        return None
    if s.startswith("data:"):
        s = s.split(",", 1)[-1]
    if len(s) > MAX_PHOTO * 4 // 3 + 16:
        return None
    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not 1000 <= len(raw) <= MAX_PHOTO or raw[:3] != b"\xff\xd8\xff":
        return None
    return raw


class Gate:
    """Anketa qabul qilish mantig'i (HTTP dan alohida, sinash oson)."""

    def __init__(self, loop, process, token, origins=""):
        self.loop, self.process, self.token = loop, process, token
        self.origins = [o.strip().rstrip("/") for o in (origins or "").split(",") if o.strip()]
        self.lock = threading.Lock()
        self.last = {}   # foydalanuvchi -> oxirgi yuborish vaqti
        self.sids = {}   # sid -> vaqt

    def allow_origin(self, origin):
        if not self.origins:
            return "*"
        return origin if origin and origin.rstrip("/") in self.origins else None

    def _gc(self, now):
        self.sids = {k: v for k, v in self.sids.items() if now - v < KEEP_SECONDS}
        self.last = {k: v for k, v in self.last.items() if now - v < KEEP_SECONDS}

    def handle(self, raw, now=None):
        """raw: so'rov tanasi (bayt). Qaytaradi: (HTTP kod, javob lug'ati)."""
        now = time.time() if now is None else now
        try:
            p = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return 400, {"ok": False, "error": "data"}
        if not isinstance(p, dict):
            return 400, {"ok": False, "error": "data"}
        user = verify_init_data(p.get("initData"), self.token, now=now)
        if not user:
            return 403, {"ok": False, "error": "telegram"}
        sid = p.get("sid")
        if not isinstance(sid, str) or not SID_RE.match(sid):
            return 400, {"ok": False, "error": "data"}
        uid = user["id"]
        with self.lock:
            self._gc(now)
            if sid in self.sids:
                return 200, {"ok": True, "dup": True}
            if now - self.last.get(uid, 0) < RATE_SECONDS:
                return 429, {"ok": False, "error": "rate"}
        answers = sanitize(p.get("answers"))
        if answers is None:
            return 400, {"ok": False, "error": "data"}
        photo = decode_photo(p.get("photo"))
        if photo is None:
            return 400, {"ok": False, "error": "photo"}
        answers["ui_lang"] = i18n.lang_ok(p.get("lang"))
        slot = p.get("slot")
        if isinstance(slot, str) and SLOT_RE.match(slot):
            answers["slot"] = slot
        with self.lock:  # ikki parallel so'rov bir xil sid bilan o'tib ketmasin
            if sid in self.sids:
                return 200, {"ok": True, "dup": True}
            self.sids[sid] = now
            self.last[uid] = now
        try:
            asyncio.run_coroutine_threadsafe(self.process(user, answers, photo), self.loop).result(timeout=90)
        except Exception:
            log.exception("Anketani qayta ishlashda xatolik")
            with self.lock:
                self.sids.pop(sid, None)
                self.last.pop(uid, None)
            return 500, {"ok": False, "error": "server"}
        return 200, {"ok": True}


def make_handler(gate, dash=None):
    class Handler(BaseHTTPRequestHandler):
        timeout = 30

        def log_message(self, fmt, *args):
            log.debug(fmt, *args)

        def _cors(self):
            origin = gate.allow_origin(self.headers.get("Origin"))
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _json(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _dash(self, method, body=b""):
            ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
            code, headers, out = dash.handle(method, self.path, self.headers, body, ip)
            self.send_response(code)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def do_GET(self):
            if dash and dash.match(self.path):
                self._dash("GET")
            elif self.path.split("?")[0] in ("/", "/health"):
                self._json(200, {"ok": True})
            else:
                self._json(404, {"ok": False})

        def do_POST(self):
            if dash and dash.match(self.path):
                try:
                    n = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    n = 0
                if not 0 <= n <= 10_000:
                    self._json(413, {"ok": False, "error": "big"})
                    return
                self._dash("POST", self.rfile.read(n) if n else b"")
                return
            if self.path.split("?")[0] != "/api/submit":
                self._json(404, {"ok": False})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0:
                self._json(400, {"ok": False, "error": "data"})
                return
            if length > MAX_BODY:
                self._json(413, {"ok": False, "error": "big"})
                return
            code, obj = gate.handle(self.rfile.read(length))
            self._json(code, obj)

    return Handler


def start_server(loop, process, token, port, origins="", dash=None):
    """HTTP serverni alohida oqimda ishga tushiradi. process(user, answers, photo_bytes) - asinxron funksiya."""
    gate = Gate(loop, process, token, origins)
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(gate, dash))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True, name="webapi").start()
    log.info("Mini App uchun HTTP server: port %d", port)
    return srv
