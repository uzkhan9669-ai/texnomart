"""PDF-анкета кандидата для рекрутера (reportlab + шрифт DejaVu с кириллицей, лежит в папке fonts/)."""
import datetime
import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from scoring import JOB, VERDICT_RU, build_profile, evaluate, position_name, verdict_code

HERE = os.path.dirname(os.path.abspath(__file__))
YELLOW, INK, MUTED, LINE = colors.HexColor("#ffc800"), colors.HexColor("#1c1c1e"), colors.HexColor("#6b6b74"), colors.HexColor("#e4e5ea")
VERDICT_COLOR = {"QABUL": colors.HexColor("#1b8a4b"), "ZAXIRA": colors.HexColor("#b77900"), "RAD": colors.HexColor("#c93030")}
FLAG_COLOR = {"🔴": colors.HexColor("#c93030"), "🟡": colors.HexColor("#e0a100")}
_ready = False


def _fonts():
    global _ready
    if not _ready:
        pdfmetrics.registerFont(TTFont("DV", os.path.join(HERE, "fonts", "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DV-B", os.path.join(HERE, "fonts", "DejaVuSans-Bold.ttf")))
        _ready = True


def _p(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _split(line):
    """Делит строку профиля на «подпись» и «значение» по первому «: » вне скобок."""
    depth = 0
    for n, ch in enumerate(line):
        depth += (ch == "(") - (ch == ")")
        if ch == ":" and depth == 0 and line[n + 1:n + 2] == " " and n <= 90:
            return line[:n], line[n + 2:]
    return None


def _bar(value, width=34 * mm, height=3.2 * mm):
    """Полоса оценки 1-5."""
    t = Table([[""] * 5], colWidths=[width / 5] * 5, rowHeights=[height])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (max(0, value - 1), 0), INK), ("BACKGROUND", (value, 0), (4, 0), LINE),
                           ("GRID", (0, 0), (-1, -1), 1.2, colors.white)] if value < 5 else
                          [("BACKGROUND", (0, 0), (4, 0), INK), ("GRID", (0, 0), (-1, -1), 1.2, colors.white)]))
    return t


def make_pdf(a, ts=None, cid=None, status="", username="", branch="", photo=None):
    """a: ответы кандидата. Возвращает PDF (bytes)."""
    _fonts()
    ev = evaluate(a)
    code = verdict_code(ev["verdict"])
    base = ParagraphStyle("b", fontName="DV", fontSize=9, leading=12.5, textColor=INK)
    small = ParagraphStyle("s", parent=base, fontSize=8, leading=11, textColor=MUTED)
    h1 = ParagraphStyle("h1", parent=base, fontName="DV-B", fontSize=17, leading=21)
    h2 = ParagraphStyle("h2", parent=base, fontName="DV-B", fontSize=10, leading=13, spaceBefore=9, spaceAfter=4, keepWithNext=True)
    bold = ParagraphStyle("bd", parent=base, fontName="DV-B")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=20 * mm, bottomMargin=16 * mm,
                            title="Анкета кандидата: %s" % a.get("fio", ""), author=JOB["company"])
    W = A4[0] - 32 * mm

    def page(canvas, d):
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0, A4[1] - 13 * mm, A4[0], 13 * mm, stroke=0, fill=1)
        canvas.setFont("DV-B", 12)
        canvas.setFillColor(colors.white)
        canvas.drawString(16 * mm, A4[1] - 8.6 * mm, "texnomart")
        canvas.setFillColor(YELLOW)
        canvas.drawString(16 * mm + canvas.stringWidth("texnomart", "DV-B", 12), A4[1] - 8.6 * mm, "*")
        canvas.setFillColor(colors.white)
        canvas.setFont("DV", 8)
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 8.4 * mm, "Анкета кандидата" + (" #%s" % cid if cid else ""))
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 8 * mm, "Сформировано %s. Персональные данные: не передавать третьим лицам." % datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))
        canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, "стр. %d" % d.page)
        canvas.restoreState()

    # --- шапка: имя, должность, балл; справа селфи
    head = [_p(a.get("fio", "-"), h1),
            _p(" · ".join(x for x in [position_name(a), ("%s лет" % a["age"]) if a.get("age") else "", a.get("phone", ""),
                                      ("@" + username) if username else ""] if x), base),
            Spacer(1, 5)]
    vt = Table([[_p("%d%%" % ev["pct"], ParagraphStyle("pc", parent=h1, fontSize=20, leading=24)),
                 _p(VERDICT_RU[code], ParagraphStyle("vd", parent=bold, textColor=colors.white, fontSize=10, alignment=1)),
                 _p("Красных флагов: %d, жёлтых: %d" % (sum(f[0] == "🔴" for f in ev["flags"]), sum(f[0] == "🟡" for f in ev["flags"])), base)]],
               colWidths=[24 * mm, 30 * mm, None])
    vt.setStyle(TableStyle([("BACKGROUND", (1, 0), (1, 0), VERDICT_COLOR[code]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (0, 0), 0), ("LEFTPADDING", (2, 0), (2, 0), 10),
                            ("TOPPADDING", (1, 0), (1, 0), 5), ("BOTTOMPADDING", (1, 0), (1, 0), 5)]))
    head.append(vt)
    extra = [x for x in [("Статус: %s" % status) if status else "", ("Филиал: %s" % branch) if branch else "",
                         ("Удобное время для собеседования: %s" % a["slot"]) if a.get("slot") else ""] if x]
    if extra:
        head += [Spacer(1, 4), _p(" · ".join(extra), small)]
    img = ""
    if photo and photo[:3] == b"\xff\xd8\xff":
        try:
            img = Image(io.BytesIO(photo), width=30 * mm, height=38 * mm, kind="proportional")
        except Exception:
            img = ""
    top = Table([[head, img]], colWidths=[W - 34 * mm, 34 * mm])
    top.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story = [top]
    pre = [x for x in build_profile(a, ts).split("\n")[1:4] if x.startswith(("Дата анкеты", "Язык анкеты"))]
    if pre:
        story += [Spacer(1, 3), _p(" · ".join(pre), small)]

    # --- оценки
    story.append(_p("ОЦЕНКА КОМПЕТЕНЦИЙ (1–5)", h2))
    rows = []
    for title, part in (("Hard skills", ev["scores"]["hard"]), ("Soft skills", ev["scores"]["soft"])):
        for n, (k, v) in enumerate(part.items()):
            rows.append([_p(title if n == 0 else "", small), _p(k, base), _bar(v), _p(str(v), bold)])
    st = Table(rows, colWidths=[20 * mm, W - 20 * mm - 38 * mm - 10 * mm, 38 * mm, 10 * mm])
    st.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                            ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (0, -1), 0)]))
    story.append(st)

    # --- риски
    story.append(_p("РИСКИ И ФЛАГИ", h2))
    if ev["flags"]:
        fr = [["", _p(("Серьёзный риск. " if lvl == "🔴" else "") + text, base)] for lvl, text, _c in ev["flags"]]
        ft = Table(fr, colWidths=[4 * mm, W - 4 * mm])
        ft.setStyle(TableStyle([("BACKGROUND", (0, n), (0, n), FLAG_COLOR.get(f[0], MUTED)) for n, f in enumerate(ev["flags"])] +
                               [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 3, colors.white),
                                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(ft)
    else:
        story.append(_p("По анкете серьёзных рисков не выявлено.", base))

    # --- остальной профиль: разделы из текстового профиля, кроме уже показанных таблицами
    skip = {"ОЦЕНКА HARD SKILLS (1-5)", "ОЦЕНКА SOFT SKILLS (1-5)", "РИСКИ И ФЛАГИ"}
    section, lines = None, []

    def flush():
        if section and section not in skip and lines:
            story.append(_p(section, h2))
            data = []
            for ln in lines:
                if ln.startswith("- "):
                    data.append([_p("•", base), _p(ln[2:], base)])
                elif _split(ln):
                    k, v = _split(ln)
                    data.append([_p(k, small), _p(v, base)])
                else:
                    data.append([_p(ln, base), ""])
            bullets = all(r[0].text == "•" for r in data)
            t = Table(data, colWidths=[5 * mm, W - 5 * mm] if bullets else [58 * mm, W - 58 * mm])
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, -1), 0),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)] +
                                  [("SPAN", (0, n), (1, n)) for n, r in enumerate(data) if r[1] == ""]))
            story.append(t)

    for ln in build_profile(a, ts).split("\n")[1:]:
        s = ln.strip()
        if not s:
            continue
        head_line = s.split(" (")[0]
        if head_line.isupper() and len(head_line) > 3 and ":" not in head_line:
            flush()
            section, lines = s, []
        elif section is None:
            continue
        elif not s.startswith(("ИТОГ:", "РЕКОМЕНДАЦИЯ:")):
            lines.append(s)
    flush()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buf.getvalue()


def filename(a, cid):
    safe = "".join(ch if ch.isalnum() else "_" for ch in (a.get("fio") or "kandidat"))[:40].strip("_") or "kandidat"
    return "anketa_%s_%s.pdf" % (cid, safe)
