"""Nomzodlar bazasi (SQLite, standart kutubxona). Fayl: candidates.db (DB_PATH o'zgaruvchisi bilan o'zgartiriladi)."""
import csv
import datetime
import io
import json
import os
import sqlite3
from contextlib import closing

STATUSES = ("yangi", "chaqirildi", "zaxira", "rad", "qabul")


def data_dir():
    """Папка для данных. Если подключён постоянный диск (Railway Volume в /data), данные хранятся на нём."""
    d = os.environ.get("DATA_DIR", "/data")
    return d if os.path.isdir(d) and os.access(d, os.W_OK) else "."


def _db_path():
    return os.environ.get("DB_PATH") or os.path.join(data_dir(), "candidates.db")


def storage_info():
    """Где лежит база и переживёт ли она перезапуск (лежит ли на отдельно подключённом диске)."""
    path = os.path.abspath(_db_path())
    d, persistent = os.path.dirname(path), False
    while d and d != "/":
        if os.path.ismount(d):
            persistent = True
            break
        d = os.path.dirname(d)
    return {"path": path, "persistent": persistent}


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
        status TEXT DEFAULT 'yangi', answers TEXT, photo_file_id TEXT)""")
    # eski bazalar uchun: selfie ustuni qo'shiladi
    cols = {r["name"] for r in _run("PRAGMA table_info(candidates)", (), "all")}
    if "photo_file_id" not in cols:
        _run("ALTER TABLE candidates ADD COLUMN photo_file_id TEXT")
    if "branch" not in cols:   # veb-panel: filial
        _run("ALTER TABLE candidates ADD COLUMN branch TEXT DEFAULT ''")
    _run("""CREATE TABLE IF NOT EXISTS status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER, old_status TEXT, new_status TEXT,
        changed_by TEXT, ts TEXT)""")


def save(tg_id, username, answers_json, fio, phone, pct, verdict, red, yellow, flags, photo_file_id=None):
    """Nomzodni saqlaydi. Qayta to'ldirsa, eski yozuv yangilanadi va holat 'yangi' ga qaytadi.
    Yangi selfie berilmasa, eski selfie saqlanib qoladi."""
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    _run("""INSERT INTO candidates (tg_id, username, ts, fio, phone, pct, verdict, red, yellow, flags, status, answers, photo_file_id)
            VALUES (?,?,?,?,?,?,?,?,?,?, 'yangi', ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET username=excluded.username, ts=excluded.ts, fio=excluded.fio,
              phone=excluded.phone, pct=excluded.pct, verdict=excluded.verdict, red=excluded.red,
              yellow=excluded.yellow, flags=excluded.flags, status='yangi', answers=excluded.answers,
              photo_file_id=COALESCE(excluded.photo_file_id, candidates.photo_file_id)""",
         (tg_id, username, ts, fio, phone, pct, verdict, red, yellow, flags, answers_json, photo_file_id))
    return _run("SELECT id FROM candidates WHERE tg_id=?", (tg_id,), "one")["id"]


def set_photo(cid, file_id):
    _run("UPDATE candidates SET photo_file_id=? WHERE id=?", (file_id, cid))


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


def set_status(cid, status, by="telegram"):
    """Holatni o'zgartiradi va tarixga yozadi (kim, qachon)."""
    row = get(cid)
    if status not in STATUSES or not row:
        return False
    _run("UPDATE candidates SET status=? WHERE id=?", (status, cid))
    if row["status"] != status:
        _run("INSERT INTO status_history (candidate_id, old_status, new_status, changed_by, ts) VALUES (?,?,?,?,?)",
             (cid, row["status"], status, by, datetime.datetime.now().isoformat(timespec="seconds")))
    return True


def set_branch(cid, branch):
    _run("UPDATE candidates SET branch=? WHERE id=?", (branch, cid))


def history(cid):
    return _run("SELECT old_status, new_status, changed_by, ts FROM status_history WHERE candidate_id=? ORDER BY id DESC LIMIT 20",
                (cid,), "all")


def all_rows():
    return _run("SELECT * FROM candidates ORDER BY pct DESC, id ASC", (), "all")


def stats():
    by_v = {r["verdict"]: r["n"] for r in _run("SELECT verdict, COUNT(*) n FROM candidates GROUP BY verdict", (), "all")}
    by_s = {r["status"]: r["n"] for r in _run("SELECT status, COUNT(*) n FROM candidates GROUP BY status", (), "all")}
    return by_v, by_s


def export_csv():
    """Excel uchun UTF-8 (BOM bilan) CSV, baytlar ko'rinishida."""
    rows = _run("SELECT * FROM candidates ORDER BY pct DESC, id ASC", (), "all")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Дата", "Ф.И.О.", "Должность", "Телефон", "Telegram", "Соответствие %", "Рекомендация", "Красные", "Жёлтые", "Статус", "Флаги"])
    for r in rows:
        try:
            pos = ["Консультант", "Кассир"][json.loads(r["answers"] or "{}").get("position_i", 0)]
        except (ValueError, IndexError, TypeError):
            pos = ""
        w.writerow([r["id"], r["ts"], r["fio"], pos, r["phone"], ("@" + r["username"]) if r["username"] else "",
                    r["pct"], r["verdict"], r["red"], r["yellow"], r["status"], r["flags"]])
    return ("﻿" + buf.getvalue()).encode("utf-8")
