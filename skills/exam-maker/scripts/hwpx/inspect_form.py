# -*- coding: utf-8 -*-
"""학교 시험지 양식(hwpx)을 살펴보고 form_map.json 초안을 쓴다.

    python inspect_form.py <양식.hwpx | 풀어 둔 폴더> [--out form_map.json] [--all]

출력
  1) 쪽 설정(용지·여백·단 수·단 폭)과 머리(표지 표·결재란·안내 상자·꼬리말) 글
  2) 문단 모양(paraPr)·글자 모양(charPr)·테두리(borderFill) 목록
     「번호 · 글꼴 · 크기 · 줄 간격 · 내어쓰기 + 그 모양을 쓰는 실제 문장 앞 20자」
  3) 어느 번호를 문항 번호/본문/〈보기〉/선지/표/상자에 쓸지 추측한 form_map.json 초안
     → Claude(또는 사람)가 목록을 보고 틀린 번호를 고친 뒤 build_exam.py --map 으로 넘긴다.

양식마다 번호가 다르므로 번호를 코드에 박지 않고 이 map 으로 주고받는다.
양식 안의 예시 문항(「1. 다음 중 …」)이 어디서 시작하는지(body_start)도 여기서 정한다.
그 앞(머리)은 그대로 두고, 그 뒤는 build_exam.py 가 지우고 새 문항으로 채운다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwpx_common import (Header, Package, own_text, page_geometry, plain_text, setup_console,  # noqa: E402
                         top_paragraphs)

SUBJECTS = ["통합과학", "과학탐구실험", "생명과학", "생명과학Ⅰ", "생명과학Ⅱ", "물리학", "물리학Ⅰ", "물리학Ⅱ", "화학", "화학Ⅰ", "화학Ⅱ",
            "지구과학", "지구과학Ⅰ", "지구과학Ⅱ", "과학", "국어", "수학", "영어", "사회", "통합사회", "역사", "한국사", "도덕",
            "기술·가정", "기술가정", "정보", "음악", "미술", "체육", "한문", "일본어", "중국어"]
SUBJ = "|".join(sorted(map(re.escape, SUBJECTS), key=len, reverse=True))

# 머리 글자 바꾸기 기본 규칙(앞에서부터 차례로, 머리 글 조각마다 적용). {…}는 exam.json meta 값.
DEFAULT_REPLACE = [
    {"pattern": r"[○\d]\s*학기\s*(?:중간|기말|○○)\s*고사", "to": "{semester}학기 {exam}", "설명": "2학기 기말고사"},
    {"pattern": r"○○\s*고사|(?:중간|기말)\s*고사", "to": "{exam}", "설명": "기말고사"},
    {"pattern": r"[가-힣○]{1,12}?(?:초등|중|고등|여자중|여자고등)?학교", "to": "{school}", "설명": "학교 이름"},
    {"pattern": r"\(\s*[○\d]\s*\)\s*학년", "to": "( {grade} )학년", "설명": "( 2 )학년"},
    {"pattern": r"(?<![\d○])[○\d]\s*학년(?!도)", "to": "{grade}학년", "설명": "2학년"},
    {"pattern": r"\d{4}\s*학년도", "to": "{year}학년도", "설명": "2026학년도"},
    {"pattern": r"\(\s*(?:%s|○○)\s*\)\s*과" % SUBJ, "to": "(  {subject}  )과", "설명": "(  과학  )과"},
    {"pattern": r"^\s*(?:%s)\s*$" % SUBJ, "to": "{subject}", "설명": "과목 칸(글 조각 전체가 과목 이름일 때만)"},
    {"pattern": r"○○", "to": "{subject}", "설명": "남은 ○○ 자리 = 과목"},
]

BOGI_TITLE = re.compile(r"^\s*[<〈＜《]\s*보\s*기\s*[>〉＞》]\s*$")
CHOICE = re.compile(r"^\s*[①②③④⑤]")
QNUM = re.compile(r"^\s*(\d{1,2})\s*[.．)]\s*\S")
POINTS = re.compile(r"[(\[]\s*\d+(?:\.\d+)?\s*점\s*[)\]]")


# --------------------------------------------------------------------
def _spans(sec: str, open_tag: str, close_tag: str):
    out, stack = [], []
    for m in re.finditer(re.escape(open_tag) + r"\b|" + re.escape(close_tag), sec):
        if m.group(0) == close_tag:
            if stack:
                out.append((stack.pop(), m.end()))
        else:
            stack.append(m.start())
    return out


def walk(sec: str):
    """모든 문단(표 안 포함) → [{start, end, pp, style, text, top, table, runs}]"""
    tables = []
    for a, b in _spans(sec, "<hp:tbl", "</hp:tbl>"):
        head = re.match(r"<hp:tbl [^>]*>", sec[a:b]).group(0)
        tables.append({"start": a, "end": b, "rows": int(re.search(r'rowCnt="(\d+)"', head).group(1)),
                       "cols": int(re.search(r'colCnt="(\d+)"', head).group(1)), "text": plain_text(sec[a:b])})
    tops = top_paragraphs(sec)
    top_at = {a: k for k, (a, _) in enumerate(tops)}
    paras = []
    for a, b in _spans(sec, "<hp:p", "</hp:p>"):
        x = sec[a:b]
        if not x.startswith("<hp:p "):
            continue
        hd = re.match(r"<hp:p [^>]*>", x).group(0)
        inner = [t for t in tables if t["start"] < a < t["end"]]
        tb = min(inner, key=lambda t: t["end"] - t["start"]) if inner else None
        body = re.sub(r"<hp:(tbl|footer|header)\b.*?</hp:\1>", "", x, flags=re.S)
        runs = [(int(c), plain_text(r)) for c, r in re.findall(r'<hp:run charPrIDRef="(\d+)">(.*?)</hp:run>', body, re.S)]
        in_footer = any(f[0] < a < f[1] for f in _spans(sec, "<hp:footer", "</hp:footer>") + _spans(sec, "<hp:header", "</hp:header>"))
        paras.append({"start": a, "end": b, "pp": int(re.search(r'paraPrIDRef="(\d+)"', hd).group(1)),
                      "style": int(re.search(r'styleIDRef="(\d+)"', hd).group(1)), "text": own_text(x).strip(),
                      "top": top_at.get(a), "table": tb, "runs": runs, "footer": in_footer})
    paras.sort(key=lambda p: p["start"])
    return paras, tables, tops


def find_body_start(sec: str, hdr: Header, paras, tops):
    """예시 문항이 시작하는 최상위 문단 번호"""
    for p in paras:
        if p["top"] is None or p["footer"]:
            continue
        info = hdr.parapr_info(p["pp"])
        t = p["text"]
        if info["heading"] == "NUMBER" and t:
            return p["top"]
        if t and (QNUM.match(t) or POINTS.search(t)) and not t.startswith("["):
            return p["top"]
    return len(tops)


def first_text_run(p):
    for c, t in p["runs"]:
        if t.strip():
            return c
    return p["runs"][0][0] if p["runs"] else None


def guess_map(pkg: Package) -> tuple[dict, dict]:
    """(form_map 초안, 살펴본 자료)"""
    secname = pkg.section_names()[0]
    sec = pkg.text(secname)
    hdr = Header(pkg.text("Contents/header.xml"))
    paras, tables, tops = walk(sec)
    bs = find_body_start(sec, hdr, paras, tops)
    body_pos = tops[bs][0] if bs < len(tops) else len(sec)
    body = [p for p in paras if p["start"] >= body_pos]
    roles, notes = {}, {}

    def role(name, p, cp=None, why=""):
        roles[name] = {"paraPr": p["pp"], "charPr": cp if cp is not None else first_text_run(p), "style": p["style"]}
        notes[name] = "%s ← 「%s」" % (why, p["text"][:20])

    # 문항(번호 문단)
    qp = next((p for p in body if p["top"] == bs), None)
    if qp:
        # 번호를 글자로 적은 양식이면 첫 조각(「1.」)이 번호 모양, 가장 긴 글 조각이 발문 모양
        runs = [(c, t) for c, t in qp["runs"] if t.strip()]
        num_cp = None
        if runs and re.fullmatch(r"\s*\d{1,2}\s*[.．)]?\s*", runs[0][1]):
            num_cp = runs[0][0]
            runs = runs[1:] or runs
        body_cp = max(runs, key=lambda r: len(r[1]))[0] if runs else None
        role("question", qp, cp=body_cp, why="예시 문항 첫 문단")
        info = hdr.parapr_info(qp["pp"])
        ncp = hdr.numbering_charpr(info["numbering"]) if info["heading"] == "NUMBER" else num_cp
        roles["question"]["number_charPr"] = ncp
    # 선지
    cp_ = next((p for p in body if p["top"] is not None and CHOICE.match(p["text"])), None) or \
        next((p for p in body if CHOICE.match(p["text"])), None)
    if cp_:
        role("choice", cp_, why="① 로 시작하는 문단")
    # 〈보기〉
    bogi_label = None
    for p in body:
        if p["table"] is not None and BOGI_TITLE.match(p["text"]):
            role("bogi_title", p, why="〈보기〉 머리 글")
            bogi_label = p["text"].strip()
            items = [q for q in body if q["table"] is p["table"] and re.match(r"^\s*[ㄱ-ㅎ]\s*[.．]", q["text"])]
            if not items:  # 〈보기〉 글이 머리 칸과 다른(안쪽) 표에 있을 때
                items = [q for q in body if q["table"] and p["table"]["start"] <= q["start"] <= p["table"]["end"]
                         and re.match(r"^\s*[ㄱ-ㅎ]\s*[.．]", q["text"])]
            if items:
                role("bogi_item", items[0], why="〈보기〉 ㄱ. 문단")
            break
    bogi_tables = {id(p["table"]) for p in body if p["table"] is not None and "보" in p["table"]["text"] and "기" in p["table"]["text"]
                   and re.search(r"[<〈＜]\s*보\s*기\s*[>〉＞]", p["table"]["text"])}
    # 상자·표: 가장 많이 쓴 (문단, 글자) 모양
    box_c, tab_c = {}, {}
    for p in body:
        tb = p["table"]
        if tb is None or id(tb) in bogi_tables or not p["text"] or CHOICE.match(p["text"]):
            continue
        key = (p["pp"], first_text_run(p), p["style"])
        if tb["rows"] * tb["cols"] == 1:
            box_c.setdefault(key, []).append(p)
        elif tb["rows"] >= 2 and tb["cols"] >= 2:
            tab_c.setdefault(key, []).append(p)
    for name, cnt, why in (("box_text", box_c, "1칸 상자 안 문단(가장 많이 쓴 모양)"), ("table_text", tab_c, "자료 표 칸 문단(가장 많이 쓴 모양)")):
        if cnt:
            key = max(cnt, key=lambda k: len(cnt[k]))
            role(name, cnt[key][0], cp=key[1], why=why + " %d곳" % len(cnt[key]))
    # 본문(번호 없는 문단): 「이에 대한 … 고른 것은?」 같은 묻는 문장을 먼저 찾는다
    cands = []
    for p in body:
        if p["top"] is None or p is qp or len(p["text"]) < 8 or CHOICE.match(p["text"]) or QNUM.match(p["text"]):
            continue
        info = hdr.parapr_info(p["pp"])
        c = first_text_run(p)
        if info["heading"] != "NONE" or info["align"] not in ("JUSTIFY", "LEFT", "DISTRIBUTE") or p["text"][0] in "☞◇[※<〈":
            continue
        if c is None or hdr.charpr_info(c)["bold"]:
            continue
        cands.append((0 if "?" in p["text"] else 1, p["start"], p, c))
    if cands:
        _, _, p, c = min(cands, key=lambda x: (x[0], x[1]))
        role("text", p, cp=c, why="번호 없는 본문 문단")
    # 모자라면 다른 역할에서 빌린다
    fallback = {"question": None, "text": "question", "choice": "text", "box_text": "text", "table_text": "box_text",
                "bogi_item": "box_text", "bogi_title": "bogi_item"}
    if "question" not in roles:  # 예시 문항이 전혀 없는 양식: 머리 다음 바탕글
        base = next((p for p in paras if p["top"] is not None and not p["footer"]), paras[0])
        role("question", base, why="예시 문항이 없어 바탕 문단")
        roles["question"]["number_charPr"] = None
    for k, src in fallback.items():
        if k not in roles and src:
            roles[k] = dict(roles[src])
            roles[k].pop("number_charPr", None)
            notes[k] = "(양식에 없어 %s 모양을 빌림)" % src
    fmap = {
        "_설명": "inspect_form.py 가 추측한 초안. 번호가 틀렸으면 아래 목록을 보고 고친다. "
                "roles 의 paraPr/charPr/style 은 양식 header.xml 번호다. 줄 간격·내어쓰기·정렬은 build_exam.py 가 이 모양을 복제해 새로 맞춘다.",
        "form": pkg.path.name,
        "section": secname,
        "body_start": {"index": bs, "text": (tops and bs < len(tops) and own_text(sec[tops[bs][0]:tops[bs][1]]).strip()[:30]) or ""},
        "roles": roles,
        "role_notes": notes,
        "bogi_label": bogi_label or "〈보기〉",
        "line_width": hdr.common_line_width(),
        "points_format": "[{pts}점]",
        "ask_indent": 1.0,
        "essay_title": "서술형",
        "number_format": "{no}.",
        "update_summary": True,
        "replace": [{k: v for k, v in r.items()} for r in DEFAULT_REPLACE],
    }
    return fmap, {"sec": sec, "hdr": hdr, "paras": paras, "tables": tables, "tops": tops, "body_start": bs}


# --------------------------------------------------------------------
def preview_replace(head_xml: str, rules, meta=None):
    meta = meta or {"school": "{school}", "grade": "{grade}", "subject": "{subject}", "exam": "{exam}",
                    "semester": "{semester}", "year": "{year}"}
    out = []
    for t in re.findall(r"<hp:t>([^<]+)</hp:t>", head_xml):
        new = apply_rules(t, rules, meta)
        if new != t:
            out.append((t.strip(), new.strip()))
    return out


def apply_rules(t: str, rules, meta) -> str:
    import html as _h
    s = _h.unescape(t)
    orig = s
    for r in rules:
        try:
            to = r["to"].format_map(_Safe(meta))
            s = re.sub(r["pattern"], lambda m: to, s)
        except re.error as e:
            print("[경고] replace 규칙 정규식 오류 %r: %s" % (r.get("pattern"), e))
    return t if s == orig else _h.escape(s, quote=False)


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def report(pkg: Package, fmap: dict, info: dict, show_all=False):
    sec, hdr, paras, tops, bs = info["sec"], info["hdr"], info["paras"], info["tops"], info["body_start"]
    g = page_geometry(sec)
    print("=" * 70)
    print("양식: %s  (본문 파일 %s)" % (pkg.path, fmap["section"]))
    print("용지 %s  %.0f×%.0fmm  여백 좌%.0f 우%.0f 위%.0f 아래%.0f mm  단 %d개(간격 %.1fmm)  단 폭 %d (%.1fmm)" % (
        g["paper"], g["width"] / 283.465, g["height"] / 283.465, g["left"] / 283.465, g["right"] / 283.465,
        g["top"] / 283.465, g["bottom"] / 283.465, g["cols"], g["gap"] / 283.465, g["col_w"], g["col_w"] / 283.465))
    if len(pkg.section_names()) > 1:
        print("[알림] 구역 파일이 %d개입니다. 첫 구역(%s)만 채우고 나머지는 그대로 둡니다." % (len(pkg.section_names()), fmap["section"]))
    print("\n[머리] 최상위 문단 0~%d (그대로 둠)" % (bs - 1))
    head_end = tops[bs][0] if bs < len(tops) else len(sec)
    head = sec[:head_end]
    for k in range(min(bs, len(tops))):
        a, b = tops[k]
        t = plain_text(sec[a:b]).strip()
        kinds = sorted(set(re.findall(r"<hp:(tbl|pic|footer|header|colPr|rect|equation)\b", sec[a:b])))
        print("  %2d  %-28s %s" % (k, ",".join(kinds), t[:60]))
    print("\n[예시 문항 시작] 최상위 문단 %d: 「%s」 → 여기부터 끝까지 지우고 새 문항으로 채움" % (bs, fmap["body_start"]["text"]))
    rest = len(tops) - bs
    print("  (지울 최상위 문단 %d개)" % rest)

    rep = preview_replace(head, fmap["replace"])
    print("\n[머리 글자 바꾸기 미리보기] (form_map 의 replace 규칙)")
    for a, b in rep:
        print("  %s  →  %s" % (a[:40], b[:40]))
    if not rep:
        print("  (바꿀 글 없음)")

    # 쓰임 표본
    pp_use, cp_use = {}, {}
    for p in paras:
        if p["text"]:
            pp_use.setdefault(p["pp"], []).append(p)
        for c, t in p["runs"]:
            if t.strip():
                cp_use.setdefault(c, []).append(t.strip())
    used_roles = {}
    for r, v in fmap["roles"].items():
        used_roles.setdefault(("pp", v.get("paraPr")), []).append(r)
        used_roles.setdefault(("cp", v.get("charPr")), []).append(r)

    print("\n[문단 모양 paraPr] 번호 · 정렬 · 줄간격 · 왼쪽 · 들여(+)/내어(−) · 문단 번호 · 쓰는 문장")
    for i in sorted(hdr.items("paraPr")):
        if not show_all and i not in pp_use and ("pp", i) not in used_roles:
            continue
        x = hdr.parapr_info(i)
        smp = pp_use.get(i, [])
        print("  %3d  %-7s %3d%%  왼%5d  %+6d  %-6s  %-22s %s" % (
            i, x["align"], x["line"], x["left"], x["intent"], x["heading"] if x["heading"] != "NONE" else "",
            ("「%s」" % smp[0]["text"][:20]) if smp else "", "← " + ",".join(used_roles.get(("pp", i), [])) if ("pp", i) in used_roles else ""))
    print("\n[글자 모양 charPr] 번호 · 글꼴 · 크기 · 장평/자간 · 굵게 · 쓰는 문장")
    for i in sorted(hdr.items("charPr")):
        if not show_all and i not in cp_use and ("cp", i) not in used_roles:
            continue
        x = hdr.charpr_info(i)
        smp = cp_use.get(i, [])
        print("  %3d  %-10s %5.1fpt  %3d%%/%+d%%  %-4s  %-22s %s" % (
            i, x["font"], x["height"] / 100, x["ratio"], x["spacing"], ("굵게" if x["bold"] else "") + ("기울" if x["italic"] else ""),
            ("「%s」" % smp[0][:20]) if smp else "", "← " + ",".join(used_roles.get(("cp", i), [])) if ("cp", i) in used_roles else ""))
    print("\n[테두리 borderFill] 번호 · 왼/오/위/아래 선")
    bf_use = {}
    for m in re.finditer(r'<hp:tc [^>]*borderFillIDRef="(\d+)"', sec):
        bf_use[int(m.group(1))] = bf_use.get(int(m.group(1)), 0) + 1
    for i in sorted(hdr.items("borderFill")):
        if not show_all and i not in bf_use:
            continue
        x = hdr.borderfill_info(i)
        side = " ".join("%s:%s" % (s[0].upper(), ("─" + x[s][1]) if x[s][0] != "NONE" else "없음") for s in ("left", "right", "top", "bottom"))
        print("  %3d  %s%s  (칸 %d곳)" % (i, side, "  색 채움" if x["fill"] else "", bf_use.get(i, 0)))

    print("\n[역할 추측]")
    for r, v in fmap["roles"].items():
        print("  %-11s paraPr %-4s charPr %-4s style %-3s %s" % (r, v.get("paraPr"), v.get("charPr"), v.get("style"), fmap["role_notes"].get(r, "")))
    print("  〈보기〉 머리 글: %s   선 굵기: %s" % (fmap["bogi_label"], fmap["line_width"]))


def main(argv=None):
    setup_console()
    ap = argparse.ArgumentParser(description="학교 양식 hwpx 살펴보기 → form_map.json 초안")
    ap.add_argument("form", help="양식 .hwpx 또는 풀어 둔 폴더")
    ap.add_argument("--out", help="form_map.json 쓸 곳(기본: 양식과 같은 폴더의 form_map.json)")
    ap.add_argument("--all", action="store_true", help="쓰이지 않는 모양 번호까지 모두 보이기")
    a = ap.parse_args(argv)
    pkg = Package(a.form)
    fmap, info = guess_map(pkg)
    report(pkg, fmap, info, a.all)
    out = Path(a.out) if a.out else (Path(a.form).parent if Path(a.form).is_file() else Path(a.form).parent) / "form_map.json"
    out.write_text(json.dumps(fmap, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nform_map 초안: %s" % out.resolve())
    print("→ 위 목록과 비교해 틀린 번호를 고친 뒤:  python build_exam.py exam.json 양식.hwpx 시험지.hwpx --map %s" % out.name)


if __name__ == "__main__":
    main()
