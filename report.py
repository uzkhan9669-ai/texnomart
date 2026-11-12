"""Отчёт для руководства в Excel: дашборд с показателями и диаграммами, воронка, динамика, кандидаты, отказы, филиалы.

В отчёт не попадают телефоны, семейное положение, дети, сведения о здоровье и селфи.
Диаграммы настоящие (их можно менять в Excel) и строятся по данным с соседних листов.
"""
import datetime
import io
import json

import xlsxwriter

import store
from scoring import VERDICT_RU, position_name

INK, YELLOW, BLUE, ORANGE, MUTED, LINE, SOFT = "#1C1C1E", "#FFC800", "#2A78D6", "#EB6834", "#6B6B74", "#E4E5EA", "#F4F5F7"
STAGE_RU = store.STAGE_RU
POSITIONS = ("Консультант", "Кассир")


def _date(ts):
    try:
        return datetime.date.fromisoformat((ts or "")[:10])
    except ValueError:
        return None


def default_period(today=None):
    """Текущий месяц с первого числа по сегодня."""
    today = today or datetime.date.today()
    return today.replace(day=1), today


def collect(d_from, d_to, pos=None):
    """Собирает данные за период [d_from, d_to] по дате анкеты. pos: 'Консультант', 'Кассир' или None."""
    reached = store.reached()
    offer_ts = {}
    for h in store.history_all():
        if h["new_status"] == "offer":
            offer_ts.setdefault(h["candidate_id"], h["ts"])
    span = (d_to - d_from).days + 1
    p_from, p_to = d_from - datetime.timedelta(days=span), d_from - datetime.timedelta(days=1)
    items, prev_total = [], 0
    for r in store.all_rows():
        try:
            a = json.loads(r["answers"] or "{}")
        except ValueError:
            a = {}
        p = position_name(a, short=True)
        d = _date(r["ts"])
        if not d or (pos and p != pos):
            continue
        if p_from <= d <= p_to:
            prev_total += 1
        if not d_from <= d <= d_to:
            continue
        od = _date(offer_ts.get(r["id"]))
        sd = _date(r["stage_ts"] or r["ts"])
        items.append({
            "id": r["id"], "date": d, "fio": r["fio"] or "", "pos": p, "pct": r["pct"] or 0,
            "verdict": VERDICT_RU.get(r["verdict"], r["verdict"] or ""), "red": r["red"] or 0, "yellow": r["yellow"] or 0,
            "status": r["status"], "reach": reached.get(r["id"], 0), "branch": (r["branch"] or "").strip(),
            "stage_days": (datetime.date.today() - sd).days if sd else 0, "reason": r["reject_reason"] or "",
            "to_offer": (od - d).days if od and od >= d else None, "flags": [f for f in (r["flags"] or "").split(" | ") if f]})
    return {"items": items, "prev_total": prev_total, "from": d_from, "to": d_to, "pos": pos, "prev": (p_from, p_to)}


def _count(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return sorted(out.items(), key=lambda kv: (-kv[1], kv[0]))


def make_xlsx(d_from=None, d_to=None, pos=None):
    if not d_from or not d_to:
        d_from, d_to = default_period()
    if d_to < d_from:
        d_from, d_to = d_to, d_from
    data = collect(d_from, d_to, pos if pos in POSITIONS else None)
    items = data["items"]
    total = len(items)
    reach = [sum(1 for i in items if i["reach"] >= n) for n in range(len(store.STAGES))]
    now_on = {s: sum(1 for i in items if i["status"] == s) for s in store.STATUSES}
    rejected, reserve = now_on["rad"], now_on["zaxira"]
    to_offer = [i["to_offer"] for i in items if i["to_offer"] is not None]
    reasons = _count(i["reason"] or "Причина не указана" for i in items if i["status"] == "rad")
    risks = _count(f for i in items for f in i["flags"])
    pct = lambda a, b: (a / b) if b else 0

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    wb.set_properties({"title": "Texnomart: отчёт по подбору персонала", "author": "Texnomart HR"})
    base = {"font_name": "Arial", "font_size": 10, "font_color": INK, "valign": "vcenter"}
    F = lambda **kw: wb.add_format(dict(base, **kw))
    head = F(bold=True, font_color="#FFFFFF", bg_color=INK, border=1, border_color=INK, text_wrap=True)
    cell, num = F(border=1, border_color=LINE), F(border=1, border_color=LINE, num_format="0")
    prc = F(border=1, border_color=LINE, num_format="0%")
    dat = F(border=1, border_color=LINE, num_format="dd.mm.yyyy", align="left")
    wrap = F(border=1, border_color=LINE, text_wrap=True)
    title = F(bold=True, font_size=14)
    note = F(font_color=MUTED, font_size=9, text_wrap=True, valign="top")

    # листы создаются сразу в том порядке, в котором их увидит читатель
    ws, ws_f, ws_d, ws_c, ws_r, ws_b = [wb.add_worksheet(n) for n in ("Дашборд", "Воронка", "Динамика", "Кандидаты", "Отказы и риски", "Филиалы")]

    # ---------------------------------------------------------------- Воронка (данные для диаграмм)
    ws_f.hide_gridlines(2)
    ws_f.set_column("A:A", 24)
    ws_f.set_column("B:E", 19)
    ws_f.write("A1", "Воронка найма", title)
    ws_f.write_row("A3", ["Этап", "Дошло до этапа", "От предыдущего этапа", "От всех анкет", "Сейчас на этапе"], head)
    for n, s in enumerate(store.STAGES):
        r = 3 + n   # строка (с нуля)
        ws_f.write(r, 0, STAGE_RU[s], cell)
        ws_f.write_number(r, 1, reach[n], num)
        if n == 0:
            ws_f.write(r, 2, "—", cell)
        else:
            ws_f.write_formula(r, 2, "=IF(B%d=0,0,B%d/B%d)" % (r, r + 1, r), prc, pct(reach[n], reach[n - 1]))
        ws_f.write_formula(r, 3, "=IF($B$4=0,0,B%d/$B$4)" % (r + 1), prc, pct(reach[n], total))
        ws_f.write_number(r, 4, now_on[s], num)
    ns = len(store.STAGES)
    off0 = 5 + ns   # строка (с нуля) заголовка блока «Вне воронки»
    ws_f.write(off0, 0, "Вне воронки", F(bold=True))
    ws_f.write_row(off0 + 1, 0, ["Статус", "Кандидатов", "Доля от анкет"], head)
    for n, s in enumerate(("zaxira", "rad")):
        ws_f.write(off0 + 2 + n, 0, STAGE_RU[s], cell)
        ws_f.write_number(off0 + 2 + n, 1, now_on[s], num)
        ws_f.write_formula(off0 + 2 + n, 2, "=IF($B$4=0,0,B%d/$B$4)" % (off0 + 3 + n), prc, pct(now_on[s], total))
    pos0 = off0 + 5   # строка (с нуля) заголовка блока по должностям
    ws_f.write(pos0, 0, "По должностям: сколько дошло до этапа", F(bold=True))
    ws_f.write_row(pos0 + 1, 0, ["Этап"] + list(POSITIONS), head)
    for n, s in enumerate(store.STAGES):
        ws_f.write(pos0 + 2 + n, 0, STAGE_RU[s], cell)
        for k, p in enumerate(POSITIONS):
            ws_f.write_number(pos0 + 2 + n, 1 + k, sum(1 for i in items if i["pos"] == p and i["reach"] >= n), num)
    ws_f.write(pos0 + 3 + ns, 0, "«Дошло до этапа» считает кандидата на всех этапах, которые он прошёл, даже если потом он получил отказ или ушёл в резерв.", note)

    # ---------------------------------------------------------------- Динамика
    ws_d.hide_gridlines(2)
    ws_d.set_column("A:A", 20)
    ws_d.set_column("B:B", 14)
    weekly = (d_to - d_from).days > 45
    ws_d.write("A1", "Анкеты по неделям" if weekly else "Анкеты по дням", title)
    ws_d.write_row("A3", ["Неделя с" if weekly else "День", "Анкет"], head)
    buckets = {}
    d = d_from
    while d <= d_to:
        key = d - datetime.timedelta(days=d.weekday()) if weekly else d
        buckets.setdefault(max(key, d_from) if weekly else key, 0)
        d += datetime.timedelta(days=1)
    for i in items:
        key = i["date"] - datetime.timedelta(days=i["date"].weekday()) if weekly else i["date"]
        key = max(key, d_from) if weekly else key
        buckets[key] = buckets.get(key, 0) + 1
    days = sorted(buckets)
    for n, k in enumerate(days):
        ws_d.write(3 + n, 0, k.strftime("%d.%m"), cell)
        ws_d.write_number(3 + n, 1, buckets[k], num)

    # ---------------------------------------------------------------- Отказы и риски
    ws_r.hide_gridlines(2)
    ws_r.set_column("A:A", 70)
    ws_r.set_column("B:C", 14)
    ws_r.write("A1", "Причины отказов", title)
    ws_r.write_row("A3", ["Причина", "Кандидатов", "Доля"], head)
    rr = reasons or [("Отказов за период нет", 0)]
    for n, (k, v) in enumerate(rr):
        ws_r.write(3 + n, 0, k, wrap)
        ws_r.write_number(3 + n, 1, v, num)
        ws_r.write_number(3 + n, 2, pct(v, rejected), prc)
    r0 = 3 + len(rr) + 2
    ws_r.write(r0, 0, "Частые риски по анкетам", title)
    ws_r.write_row(r0 + 2, 0, ["Риск (флаг системы)", "Анкет", "Доля анкет"], head)
    for n, (k, v) in enumerate(risks[:15] or [("Флагов за период нет", 0)]):
        ws_r.write(r0 + 3 + n, 0, k, wrap)
        ws_r.write_number(r0 + 3 + n, 1, v, num)
        ws_r.write_number(r0 + 3 + n, 2, pct(v, total), prc)

    # ---------------------------------------------------------------- Филиалы
    ws_b.hide_gridlines(2)
    ws_b.set_column("A:A", 30)
    ws_b.set_column("B:G", 17)
    ws_b.write("A1", "По филиалам", title)
    ws_b.write_row("A3", ["Филиал", "Кандидатов", "До собеседования", "До стажировки", "Офферов", "Принято", "Средний балл"], head)
    branches = {}
    for i in items:
        branches.setdefault(i["branch"] or "Не назначен", []).append(i)
    for n, (b, lst) in enumerate(sorted(branches.items(), key=lambda kv: (-len(kv[1]), kv[0])) or [("Данных нет", [])]):
        ws_b.write(3 + n, 0, b, cell)
        ws_b.write_row(3 + n, 1, [len(lst), sum(1 for i in lst if i["reach"] >= 2), sum(1 for i in lst if i["reach"] >= 3),
                                  sum(1 for i in lst if i["reach"] >= 4), sum(1 for i in lst if i["reach"] >= 5)], num)
        ws_b.write_number(3 + n, 6, round(sum(i["pct"] for i in lst) / len(lst)) if lst else 0, num)
    ws_b.autofilter(2, 0, 2 + max(1, len(branches)), 6)

    # ---------------------------------------------------------------- Кандидаты
    cols = [("№", 6), ("Дата анкеты", 13), ("Ф.И.О.", 30), ("Должность", 14), ("Балл, %", 9), ("Рекомендация", 15), ("Красных флагов", 10),
            ("Жёлтых флагов", 10), ("Текущий этап", 17), ("Дошёл до этапа", 17), ("Филиал", 20), ("Дней на этапе", 10), ("Причина отказа", 26)]
    for n, (name, w) in enumerate(cols):
        ws_c.set_column(n, n, w)
        ws_c.write(0, n, name, head)
    ws_c.set_row(0, 30)
    for n, i in enumerate(sorted(items, key=lambda x: (-x["pct"], x["id"]))):
        r = n + 1
        ws_c.write_number(r, 0, i["id"], num)
        ws_c.write_datetime(r, 1, datetime.datetime.combine(i["date"], datetime.time()), dat)
        ws_c.write_string(r, 2, i["fio"], cell)   # write_string: текст кандидата не превращается в формулу
        ws_c.write_string(r, 3, i["pos"], cell)
        ws_c.write_number(r, 4, i["pct"], num)
        ws_c.write_string(r, 5, i["verdict"], cell)
        ws_c.write_number(r, 6, i["red"], num)
        ws_c.write_number(r, 7, i["yellow"], num)
        ws_c.write_string(r, 8, STAGE_RU.get(i["status"], i["status"]), cell)
        ws_c.write_string(r, 9, STAGE_RU[store.STAGES[i["reach"]]], cell)
        ws_c.write_string(r, 10, i["branch"], cell)
        ws_c.write_number(r, 11, i["stage_days"], num)
        ws_c.write_string(r, 12, i["reason"], cell)
    ws_c.freeze_panes(1, 3)
    ws_c.autofilter(0, 0, max(1, total), len(cols) - 1)
    if total:
        ws_c.conditional_format(1, 4, total, 4, {"type": "data_bar", "bar_color": BLUE, "bar_solid": True, "min_type": "num", "min_value": 0,
                                                 "max_type": "num", "max_value": 100})

    # ---------------------------------------------------------------- Дашборд (первый лист)
    ws.hide_gridlines(2)
    ws.set_column("A:A", 2)
    ws.set_column("B:M", 12.5)
    ws.set_column("N:N", 2)
    band = F(bg_color=INK)
    for r in range(0, 4):
        ws.set_row(r, 20, band)
    ws.merge_range("B2:G3", "", band)
    ws.write_rich_string("B2", F(bold=True, font_size=24, font_color="#FFFFFF", bg_color=INK), "texnomart",
                         F(bold=True, font_size=24, font_color=YELLOW, bg_color=INK), "*", band)
    ws.merge_range("H2:M2", "Отчёт по подбору персонала", F(bold=True, font_size=14, font_color="#FFFFFF", bg_color=INK, align="right"))
    period = "%s – %s" % (d_from.strftime("%d.%m.%Y"), d_to.strftime("%d.%m.%Y"))
    ws.merge_range("H3:M3", "Период: %s · Должность: %s" % (period, data["pos"] or "все"),
                   F(font_color="#D0D0D6", bg_color=INK, align="right"))
    ws.set_row(4, 8)

    k_label = F(font_color=MUTED, font_size=9, bold=True, bg_color=SOFT, top=2, top_color=YELLOW, indent=1)
    k_value = F(font_size=22, bold=True, bg_color=SOFT, indent=1)
    k_pct = F(font_size=22, bold=True, bg_color=SOFT, indent=1, num_format="0%")
    k_days = F(font_size=22, bold=True, bg_color=SOFT, indent=1, num_format='0.0" дн."')
    k_note = F(font_color=MUTED, font_size=9, bg_color=SOFT, indent=1, text_wrap=True, valign="top")
    delta = total - data["prev_total"]
    tiles = [
        ("АНКЕТ ПОЛУЧЕНО", total, k_value, "к прошлому периоду: %s%d (было %d)" % ("+" if delta >= 0 else "−", abs(delta), data["prev_total"])),
        ("ДОШЛИ ДО СОБЕСЕДОВАНИЯ", reach[2], k_value, "%d%% от анкет" % round(pct(reach[2], total) * 100)),
        ("ДОШЛИ ДО СТАЖИРОВКИ", reach[3], k_value, "%d%% от анкет" % round(pct(reach[3], total) * 100)),
        ("ОФФЕРОВ", reach[4], k_value, "конверсия анкета → оффер: %d%%" % round(pct(reach[4], total) * 100)),
        ("СРЕДНИЙ БАЛЛ КАНДИДАТОВ", pct(sum(i["pct"] for i in items), total * 100), k_pct, "оценка анкеты системой, из 100%"),
        ("ОТ АНКЕТЫ ДО ОФФЕРА", (sum(to_offer) / len(to_offer)) if to_offer else None, k_days,
         "в среднем, по %d офферам" % len(to_offer) if to_offer else "офферов за период ещё нет"),
        ("ДОЛЯ ОТКАЗОВ", pct(rejected, total), k_pct, ("главная причина: %s" % reasons[0][0].lower()) if reasons else "отказов за период нет"),
        ("ПРИНЯТО НА РАБОТУ", reach[5], k_value, "%d%% от анкет · в резерве: %d" % (round(pct(reach[5], total) * 100), reserve)),
    ]
    for n, (label, value, fmt, sub) in enumerate(tiles):
        r, c = 5 + (n // 4) * 5, 1 + (n % 4) * 3
        ws.merge_range(r, c, r, c + 2, label, k_label)
        if value is None:
            ws.merge_range(r + 1, c, r + 2, c + 2, "—", k_value)
        else:
            ws.merge_range(r + 1, c, r + 2, c + 2, value, fmt)
        ws.merge_range(r + 3, c, r + 3, c + 2, sub, k_note)
        ws.set_row(r, 18)
        ws.set_row(r + 1, 17)
        ws.set_row(r + 2, 17)
        ws.set_row(r + 3, 26)
        ws.set_row(r + 4, 8)

    def chart(kind, name, cats, vals, color=BLUE, labels=True, reverse=False, title_text=""):
        ch = wb.add_chart({"type": kind})
        s = {"name": name, "categories": cats, "values": vals, "fill": {"color": color}, "border": {"none": True}, "gap": 60}
        if labels:
            s["data_labels"] = {"value": True, "font": {"name": "Arial", "size": 9, "color": INK}}
        ch.add_series(s)
        ch.set_title({"name": title_text, "name_font": {"name": "Arial", "size": 11, "bold": True, "color": INK}, "overlay": False})
        ch.set_legend({"none": True})
        axis_font = {"name": "Arial", "size": 9, "color": MUTED}
        grid = {"visible": True, "line": {"color": LINE, "width": 0.75}}
        cat_axis = {"num_font": axis_font, "line": {"color": "#B9BBC4"}, "major_gridlines": {"visible": False}, "reverse": reverse}
        val_axis = {"num_font": axis_font, "line": {"none": True}, "major_gridlines": grid, "min": 0, "num_format": "0"}
        if kind == "bar":   # у горизонтальных столбцов значения подписаны на самих столбцах, ось не нужна
            ch.set_y_axis(cat_axis)
            ch.set_x_axis(dict(val_axis, visible=False, major_gridlines={"visible": False}))
        else:
            ch.set_x_axis(cat_axis)
            ch.set_y_axis(val_axis)
        ch.set_chartarea({"border": {"color": LINE}, "fill": {"color": "#FFFFFF"}})
        ch.set_plotarea({"fill": {"color": "#FFFFFF"}})
        return ch

    c1 = chart("bar", "Дошло до этапа", "=Воронка!$A$4:$A$%d" % (3 + ns), "=Воронка!$B$4:$B$%d" % (3 + ns), reverse=True, title_text="Воронка: сколько кандидатов дошло до этапа")
    c2 = chart("column", "Анкет", ["Динамика", 3, 0, 2 + len(days), 0], ["Динамика", 3, 1, 2 + len(days), 1], labels=len(days) <= 16,
               title_text="Анкеты по неделям" if weekly else "Анкеты по дням")
    p1, p2 = pos0 + 3, pos0 + 2 + ns   # строки Excel блока по должностям
    c3 = chart("column", POSITIONS[0], "=Воронка!$A$%d:$A$%d" % (p1, p2), "=Воронка!$B$%d:$B$%d" % (p1, p2), title_text="Консультанты и кассиры по этапам")
    c3.add_series({"name": POSITIONS[1], "categories": "=Воронка!$A$%d:$A$%d" % (p1, p2), "values": "=Воронка!$C$%d:$C$%d" % (p1, p2), "fill": {"color": ORANGE},
                   "border": {"none": True}, "data_labels": {"value": True, "font": {"name": "Arial", "size": 9, "color": INK}}})
    c3.set_legend({"position": "bottom", "font": {"name": "Arial", "size": 9, "color": INK}})
    c4 = chart("bar", "Отказов", ["Отказы и риски", 3, 0, 2 + len(rr), 0], ["Отказы и риски", 3, 1, 2 + len(rr), 1], reverse=True,
               title_text="Причины отказов")
    size = {"x_scale": 1.155, "y_scale": 1.12}
    ws.insert_chart("B16", c1, dict(size, x_offset=0))
    ws.insert_chart("H16", c2, size)
    ws.insert_chart("B33", c3, size)
    ws.insert_chart("H33", c4, size)
    ws.merge_range("B50:M52", "Сформировано %s из базы анкет бота. Данные для диаграмм и расчёты лежат на листах «Воронка», «Динамика», «Отказы и риски», "
                   "«Филиалы», «Кандидаты». Телефоны и личные сведения кандидатов в отчёт не включаются."
                   % datetime.datetime.now().strftime("%d.%m.%Y %H:%M"), note)
    ws.set_row(49, 15)
    ws.set_row(50, 15)
    ws.set_row(51, 15)
    ws.print_area("A1:N53")
    ws.set_landscape()
    ws.set_paper(9)
    ws.fit_to_pages(1, 1)
    ws.set_margins(0.3, 0.3, 0.3, 0.3)
    ws.activate()
    wb.close()
    return buf.getvalue()


def filename(d_from, d_to):
    return "texnomart_hr_otchet_%s_%s.xlsx" % (d_from.isoformat(), d_to.isoformat())
