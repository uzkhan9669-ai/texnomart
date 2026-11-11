"""Собирает miniapp/index.html: вопросы берутся из scoring.py и i18n.py (три языка).
Ключи оценки ("scores") в файл для кандидата НЕ попадают.
Запуск:  python miniapp/build_miniapp.py https://ВАШ-ДОМЕН.up.railway.app/api/submit"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import i18n  # noqa: E402
from scoring import QUESTIONS  # noqa: E402

CLIENT_UI = [k for k in i18n.UI if k not in ("greeting", "btn_web", "btn_chat", "thanks", "press_start", "use_buttons", "need_number", "no_back")]


def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    api = sys.argv[1] if len(sys.argv) > 1 else "PASTE_API_URL_HERE"
    qs = []
    for q in QUESTIONS:
        item = {k: q[k] for k in ("key", "type", "block", "pos", "when") if k in q}
        item["t"] = {l: list(i18n.Q[q["key"]][l]) for l in i18n.LANGS}
        if q["key"] in i18n.Q_POS:   # текст зависит от должности
            item["tp"] = {str(p): {l: list(v[l]) for l in i18n.LANGS} for p, v in i18n.Q_POS[q["key"]].items()}
        qs.append(item)
    t = open(os.path.join(HERE, "miniapp_template.html"), encoding="utf-8").read()
    for mark, val in (("/*@@JOB@@*/{}", i18n.JOB_TR), ("/*@@QUESTIONS@@*/[]", qs), ("/*@@BLOCKS@@*/{}", i18n.BLOCKS),
                      ("/*@@UI@@*/{}", {k: i18n.UI[k] for k in CLIENT_UI}), ("/*@@LANGS@@*/{}", i18n.LANG_NAMES)):
        assert t.count(mark) == 1, mark
        t = t.replace(mark, js(val))
    t = t.replace('"PASTE_API_URL_HERE"', js(api))
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(t)
    print("index.html готов: вопросов %d, языков %d, API: %s" % (len(qs), len(i18n.LANGS), api))


main()
