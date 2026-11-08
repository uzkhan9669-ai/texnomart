"""Nomzodlar bazasi (SQLite, standart kutubxona). Fayl: candidates.db (DB_PATH o'zgaruvchisi bilan o'zgartiriladi)."""
import csv
import datetime
import io
import os
import sqlite3
from contextlib import closing

STATUSES = ("yangi", "chaqirildi", "zaxira", "rad", "qabul")


def _db_path():
    return os.environ.get("DB_PATH", "candidates.db")


def _run(sql, args=(), fetch=None):
    with closing(sqlite3.connect(_db_path())) as c:
        c.row_factory = sqlite3.Row
        cur = c.execute(sql, args)
        rows = cur.fetchall() if fetch == "all" else (cur.fetchone() if fetch == "one" else None)
        c.commit()
        return rows


def init():
    _run("""CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE, username TEXT, ts TEXT,
        fio TEXT, phone TEXT, pct INTEGER, verdict TEXT,
        red INTEGER, yellow INTEGER, flags TEXT,
        status TEXT DEFAULT 'yangi', answers TEXT)""")


def save(tg_id, username, answers_json, fio, phone, pct, verdict, red, yellow, flags):
    """Nomzodni saqlaydi. Qayta to'ldirsa, eski yozuv yangilanadi va holat 'yangi' ga qaytadi."""
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    _run("""INSERT INTO candidates (tg_id, username, ts, fio, phone, pct, verdict, red, yellow, flags, status, answers)
            VALUES (?,?,?,?,?,?,?,?,?,?, 'yangi', ?)
            ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, ts=excluded.ts, fio=excluded.fio,
              phone=excluded.phone, pct=excluded.pct, verdict=excluded.verdict, red=excluded.red,
              yellow=excluded.yellow, flags=excluded.flags, status='yangi', answers=excluded.answers""",
         (tg_id, username, ts, fio, phone, pct, verdict, red, yellow, flags, answers_json))
    return _run("SELECT id FROM candidates WHERE tg_id=?", (tg_id,), "one")["id"]


def get(cid):
    return _run("SELECT * FROM candidates WHERE id=?", (cid,), "one")


def listing(verdict=None, newest=False, limit=20):
    where, args = "", []
    if verdict:
        where = "WHERE verdict=?"
        args.append(verdict)
    order = "id DESC" if newest else "pct DESC, id ASC"
    args.append(limit)
    return _run("SELECT * FROM candidates %s ORDER BY %s LIMIT ?" % (where, order), tuple(args), "all")


def set_status(cid, status):
    if status not in STATUSES or not get(cid):
        return False
    _run("UPDATE candidates SET status=? WHERE id=?", (status, cid))
    return True


def stats():
    by_v = {r["verdict"]: r["n"] for r in _run("SELECT verdict, COUNT(*) n FROM candidates GROUP BY verdict", (), "all")}
    by_s = {r["status"]: r["n"] for r in _run("SELECT status, COUNT(*) n FROM candidates GROUP BY status", (), "all")}
    return by_v, by_s


def export_csv():
    """Excel uchun UTF-8 (BOM bilan) CSV, baytlar ko'rinishida."""
    rows = _run("SELECT * FROM candidates ORDER BY pct DESC, id ASC", (), "all")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Sana", "F.I.Sh.", "Telefon", "Telegram", "Moslik %", "Tavsiya", "Qizil", "Sariq", "Holat", "Flaglar"])
    for r in rows:
        w.writerow([r["id"], r["ts"], r["fio"], r["phone"], ("@" + r["username"]) if r["username"] else "",
                    r["pct"], r["verdict"], r["red"], r["yellow"], r["status"], r["flags"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")
