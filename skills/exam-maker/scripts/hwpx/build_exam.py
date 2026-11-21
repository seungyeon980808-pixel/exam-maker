# -*- coding: utf-8 -*-
"""exam.json → 학교 양식 모양을 빌린 시험지 hwpx

    python build_exam.py <exam.json> <양식.hwpx> <out.hwpx> [--map form_map.json] [--only 1,3] [--pages 4]

- 양식의 머리(표지 표·결재란·안내 상자·꼬리말)는 그대로 둔다. 학교·학년·과목 글자는 form_map 의 replace 규칙으로
  meta 값으로 바꾸고, 못 찾으면 그대로 둔다. [배점 현황] 같은 「총 N문항」「N문항×P점 … = T점」 글도 다시 센다.
- 양식의 예시 문항(body_start 부터 끝까지)은 지우고 exam.json 문항으로 채운다.
- 글자·문단·테두리 모양은 form_map 의 양식 번호를 복제해 쓴다(줄 간격 = meta.line_spacing, 내어쓰기는 새로 잰다).
- --map 이 없으면 inspect_form.py 의 추측을 그대로 쓴다.

표·상자 높이는 글 폭을 어림해 적는다. 한글은 열 때 스스로 다시 맞추지만, 미리보기 엔진은 적힌 높이를 쓴다.
"""
from __future__ import annotations

import argparse
import html
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwpx_common import (UNKNOWN_TEX, Header, Ids, Metric, Package, cell_xml, check_xml, eq_size, equation_xml,  # noqa: E402
                         esc, fmt_pts, image_size, load_json, obj_run, page_geometry, para_xml, parse_inline,
                         picture_xml, run_xml, setup_console, strip_inline, table_xml, tall_extra, text_width,
                         top_paragraphs)
import inspect_form  # noqa: E402

MARK = "①②③④⑤⑥⑦⑧⑨⑩"
COMBO = re.compile(r"^\s*[ㄱ-ㅎ](?:\s*,\s*[ㄱ-ㅎ])*\s*$")
WARN: list[str] = []


def warn(msg):
    WARN.append(msg)


class Para(str):
    """문단 XML + 어림 높이(HWPUNIT)"""

    def __new__(cls, x, h):
        o = str.__new__(cls, x)
        o.h = h
        return o


class Builder:
    def __init__(self, pkg: Package, fmap: dict, meta: dict, base_dir: Path):
        self.pkg, self.fmap, self.meta, self.base = pkg, fmap, meta, base_dir
        self.secname = fmap.get("section") or pkg.section_names()[0]
        self.sec = pkg.text(self.secname)
        self.hdr = Header(pkg.text("Contents/header.xml"))
        self.geo = page_geometry(self.sec)
        self.W = self.geo["col_w"]
        self.ids = Ids(para=max([int(x) for x in re.findall(r'<hp:p id="(\d+)"', self.sec)] + [0]) + 1000)
        self.roles = self._resolve_roles(fmap.get("roles", {}))
        q = self.roles["question"]
        self.line = int(meta.get("line_spacing") or self.hdr.parapr_info(q["paraPr"])["line"])
        lw = fmap.get("line_width") or self.hdr.common_line_width()
        h = self.hdr
        self.bf_all = h.add_borderfill(True, True, True, True, lw)
        self.bf_none = h.add_borderfill(False, False, False, False, lw)
        self.bf_b = h.add_borderfill(bottom=True, width=lw)              # 〈보기〉 머리 줄 왼·오 윗칸(아래 선 = 가는 머리 선)
        self.bf_lt = h.add_borderfill(left=True, top=True, width=lw)
        self.bf_rt = h.add_borderfill(right=True, top=True, width=lw)
        self.bf_lrb = h.add_borderfill(left=True, right=True, bottom=True, width=lw)
        self.box_w = int(self.W - max(600, self.W * 0.032))             # 상자·〈보기〉 폭
        self.metrics = {}

    # ---------------- 역할 ----------------
    def _resolve_roles(self, roles):
        h = self.hdr
        out = {}
        order = ["question", "text", "choice", "box_text", "table_text", "bogi_item", "bogi_title"]
        fb = {"text": "question", "choice": "text", "box_text": "text", "table_text": "box_text",
              "bogi_item": "box_text", "bogi_title": "bogi_item"}
        for r in order:
            v = dict(roles.get(r) or {})
            ok = h.has("paraPr", v.get("paraPr")) and h.has("charPr", v.get("charPr"))
            if not ok:
                if r == "question":
                    raise SystemExit("[오류] form_map 의 question 역할 번호(paraPr/charPr)가 양식에 없습니다. inspect_form.py 로 다시 만드세요.")
                if roles.get(r):
                    warn("form_map 역할 %s 의 번호가 양식에 없어 %s 모양을 빌림" % (r, fb[r]))
                v = dict(out[fb[r]])
            v.setdefault("style", 0)
            if not h.has("style", v["style"]):
                v["style"] = 0
            out[r] = v
        ncp = out["question"].get("number_charPr")
        if not h.has("charPr", ncp):
            ncp = h.add_charpr(out["question"]["charPr"], bold=True)
        out["question"]["number_charPr"] = int(ncp)
        return out

    def cp(self, role, flags=()):
        base = self.roles[role]["charPr"] if isinstance(role, str) else role
        f = set(flags)
        return self.hdr.add_charpr(base, bold=True if "b" in f else None, italic=True if "i" in f else None,
                                   underline=True if "u" in f else None, sup="sup" in f, sub="sub" in f)

    def metric(self, role) -> Metric:
        c = self.roles[role]["charPr"] if isinstance(role, str) else role
        if c not in self.metrics:
            self.metrics[c] = Metric(self.hdr, c)
        return self.metrics[c]

    def pp(self, role, *, align=None, intent=0, left=0, line=None, tab=None, prev=None, next=None, keep_next=None):
        # 문단 위·아래 간격은 양식 값을 쓰지 않고 0(문항 문단만 양식의 아래 간격)으로 맞춘다: 들쭉날쭉한 예시 문항 간격이 섞이지 않게
        return self.hdr.add_parapr(self.roles[role]["paraPr"], align=align, intent=int(intent), left=int(left), right=0,
                                   prev=prev or 0, next=next or 0, line=line or self.line, tab=tab, keep_next=keep_next)

    def style(self, role):
        # 양식 스타일(「문제」 등)에는 문단 번호가 묶여 있는 일이 많아 기본은 바탕글(0)로 둔다
        return self.roles[role]["style"] if self.fmap.get("use_styles") else 0

    def lh(self, role, line=None):
        return self.metric(role).size * (line or self.line) / 100

    # ---------------- 글 ----------------
    def runs(self, text, role, extra=()):
        out = []
        size = self.metric(role).size
        for kind, s, flags in parse_inline(text):
            c = self.cp(role, set(flags) | set(extra))
            if kind == "eq":
                out.append(obj_run(equation_xml(self.ids, s, size), c))
            elif s:
                out.append(run_xml(s, c))
        return "".join(out) or run_xml("", self.cp(role, extra))

    def tpara(self, text, role, width, *, intent=0, left=0, align=None, prefix="", prefix_w=0, next=None, extra=(),
              line=None, tab=None, keep_next=None):
        """글 문단. 높이 = 어림 줄 수 × 줄 높이"""
        w = text_width(text, self.metric(role)) * 1.03 + prefix_w
        first = width - left - max(intent, 0)
        rest = width - left - max(-intent, 0)
        n = 1 if w <= first else 1 + math.ceil((w - first) / max(rest, 3000))
        lh = self.lh(role, line)
        h = n * lh + tall_extra(text, self.metric(role).size)
        pp = self.pp(role, align=align, intent=intent, left=left, next=next, line=line, tab=tab, keep_next=keep_next)
        x = para_xml(self.ids, prefix + self.runs(text, role, extra), pp, self.style(role))
        return Para(x, h + (next or 0))

    def opara(self, obj, obj_h, role="text", align="CENTER", next=None):
        """그림·표·수식 하나만 든 문단"""
        pp = self.pp(role, align=align, next=next)
        x = para_xml(self.ids, obj_run(obj, self.cp(role)), pp, self.style(role))
        return Para(x, obj_h + (self.line - 100) / 100 * self.metric(role).size + 60)

    def blank(self, role="text"):
        return Para(para_xml(self.ids, run_xml("", self.cp(role)), self.pp(role), self.style(role)), self.lh(role))

    # ---------------- 블록 ----------------
    def blocks(self, blocks, width, inbox=False):
        out = []
        for b in blocks or []:
            out += self.block(b, width, inbox)
        return out

    def block(self, b, width, inbox):
        t = b.get("type")
        role = "box_text" if inbox else "text"
        if t == "text":
            return [self.tpara(line, role, width) for line in str(b.get("text", "")).split("\n") if line.strip()]
        if t == "fig":
            return self.figure(b, width)
        if t == "table":
            x, _, H = self.data_table(b, width - 200)
            out = [self.opara(x, H, role)]
            if b.get("caption"):
                out.append(self.tpara(b["caption"], role, width, align="CENTER"))
            return out
        if t == "eq":
            tex = b.get("tex", "")
            return [self.opara(equation_xml(self.ids, tex, self.metric(role).size), eq_size(tex, self.metric(role).size)[1], role)]
        if t == "box":
            return [self.box(self.blocks(b.get("blocks"), self.box_w - 566 * 2 - 300, True))]
        if t == "talk":
            return [self.box(self.talk(b.get("lines") or [], self.box_w - 566 * 2 - 300))]
        if t == "pair":
            return self.pair(b, width, inbox)
        warn("모르는 블록 종류 %r → 건너뜀" % t)
        return []

    def talk(self, lines, width):
        role = "box_text"
        m = self.metric(role)
        labels = ["%s : " % (lab or "") for lab, _ in lines] or [""]
        hang = max(m.plain(strip_inline(l)) for l in labels) + 100
        out = []
        for lab, txt in lines:
            pre = self.runs("%s : " % lab, role, ("b",))
            out.append(self.tpara(txt, role, width, intent=-hang, prefix=pre, prefix_w=hang))
        return out

    def box(self, inner, width=None):
        W = width or self.box_w
        h = sum(p.h for p in inner) + 400 + 400 + 200
        trs = [[cell_xml(0, 0, W, h, inner, self.bf_all, margin=(566, 566, 400, 400))]]
        t = table_xml(self.ids, 1, 1, W, h, trs, self.bf_all, inmargin=(566, 566, 0, 0), outmargin=(0, 0, 141, 283))
        return self.opara(t, h + 424, "text")

    def figure(self, b, width):
        src = b.get("src") or ""
        path = (self.base / src) if src else None
        frac = float(b.get("width") or 0.6)
        W = int(min(width, self.W - 300) * max(0.05, min(frac, 1.0)))
        role = "text"
        if not path or not path.is_file():
            warn("그림 파일을 찾지 못함: %s → 자리 상자로 넣음" % src)
            inner = [self.tpara("[그림 자리: %s]" % src, "box_text", W - 1400, align="CENTER")]
            out = [self.box(inner, W)]
        else:
            raw = path.read_bytes()
            ext = path.suffix.lower().lstrip(".")
            if ext not in ("png", "jpg", "jpeg"):
                try:
                    import io
                    from PIL import Image
                    buf = io.BytesIO()
                    Image.open(io.BytesIO(raw)).save(buf, "PNG")
                    raw, ext = buf.getvalue(), "png"
                except Exception:
                    warn("그림 %s 은(는) PNG·JPG 가 아니고 Pillow 도 없어 건너뜀" % src)
                    return []
            pw, ph = image_size(raw)
            bid = self.pkg.add_bindata(raw, "jpg" if ext == "jpeg" else ext)
            x, H = picture_xml(self.ids, bid, pw, ph, W)
            out = [self.opara(x, H, role)]
        if b.get("caption"):
            out.append(self.tpara(b["caption"], role, width, align="CENTER"))
        return out

    def table_nat(self, b):
        m = self.metric("table_text")
        head = b.get("head") or []
        rows = ([head] if head else []) + (b.get("rows") or [])
        C = max((len(r) for r in rows), default=0)
        return [max(max((text_width(str(x), m) for x in str(r[c] if c < len(r) else "").split("\n")), default=0) for r in rows) * 1.05 + 900
                for c in range(C)]

    def data_table(self, b, avail):
        role = "table_text"
        head = b.get("head") or []
        rows = ([head] if head else []) + (b.get("rows") or [])
        if not rows:
            return "", 0, 0
        C = max(len(r) for r in rows)
        nat = [max(n, 2300) for n in self.table_nat(b)]
        total = sum(nat)
        if total > avail:
            long_cols = [c for c in range(C) if nat[c] > 6000]
            over = total - avail
            if long_cols:
                share = sum(nat[c] for c in long_cols)
                for c in long_cols:
                    nat[c] = max(2300, nat[c] - over * nat[c] / share)
            if sum(nat) > avail:
                nat = [n * avail / sum(nat) for n in nat]
        Wc = [int(n) for n in nat]
        CM = (200, 200, 100, 100)
        trs, H = [], 0
        for r, row in enumerate(rows):
            cols = []
            for c in range(C):
                v = str(row[c]) if c < len(row) else ""
                inner = Wc[c] - CM[0] - CM[1] - 150
                ps = [self.tpara(l, role, inner, align="CENTER") for l in (v.split("\n") or [""])]
                cols.append(ps)
            rh = max(sum(p.h for p in ps) for ps in cols) + CM[2] + CM[3] + 100
            trs.append([cell_xml(c, r, Wc[c], rh, cols[c], self.bf_all, margin=CM) for c in range(C)])
            H += rh
        x = table_xml(self.ids, len(rows), C, sum(Wc), H, trs, self.bf_all, outmargin=(0, 0, 0, 141),
                      repeat=1 if head else 0)
        return x, sum(Wc), H

    def pair(self, b, width, inbox):
        ch = (b.get("blocks") or [])[:2]
        if len(ch) < 2:
            return self.blocks(ch, width, inbox)
        widths = [sum(self.table_nat(x)) + 700 if x.get("type") == "table" else None for x in ch]
        fixed = sum(w for w in widths if w)
        free = max(width - fixed, width * 0.3)
        nf = widths.count(None)
        widths = [w if w else free / nf for w in widths] if nf else widths
        if sum(widths) > width:
            widths = [w * width / sum(widths) for w in widths]
        cols = []
        for c, x in enumerate(ch):
            x = dict(x)
            if x.get("type") == "fig":
                x["width"] = 1.0 if not x.get("width") else min(1.0, float(x["width"]) * width / widths[c])
            cols.append(self.block(x, widths[c] - 200, inbox))
        rh = max(sum(p.h for p in col) for col in cols) + 100
        cells = [cell_xml(c, 0, widths[c], rh, cols[c], self.bf_none, valign="BOTTOM", margin=(100, 100, 0, 0)) for c in range(2)]
        gt = table_xml(self.ids, 1, 2, sum(widths), rh, [cells], self.bf_none, inmargin=(0, 0, 0, 0),
                       outmargin=(0, 0, 0, 141), split="NONE")
        return [self.opara(gt, rh + 141, "text")]

    # ---------------- 〈보기〉 ----------------
    def bogi(self, lines):
        """머리 줄(가는 선 + 〈보기〉)은 얇게, 안쪽 좌우·아래 여백 1.5mm"""
        label = self.fmap.get("bogi_label") or "〈보기〉"
        T = self.box_w
        PAD = 425
        tm = self.metric("bogi_title")
        title_w = int(tm.plain(label) + 1400)
        side = (T - title_w) // 2
        BW = [side, T - 2 * side, side]
        title_line = 130
        HR = int(math.ceil(tm.size * title_line / 100 / 2))
        tiny_cp = self.hdr.add_charpr(self.roles["bogi_title"]["charPr"], height=500)
        tiny_pp = self.pp("bogi_title", line=100)

        def tiny():
            return para_xml(self.ids, run_xml("", tiny_cp), tiny_pp, 0)

        inner = T - PAD * 2
        im = self.metric("bogi_item")
        items = []
        for k, l in enumerate(lines):
            lab = "ㄱㄴㄷㄹㅁㅂㅅㅇ"[k] if k < 8 else str(k + 1)
            head = "%s. " % lab
            hang = im.plain(head)
            items.append(self.tpara(head + l, "bogi_item", inner, intent=-hang))
        ih = sum(p.h for p in items) + 100 + PAD
        z = (0, 0, 0, 0)
        title_p = para_xml(self.ids, run_xml(label, self.cp("bogi_title")), self.pp("bogi_title", align="CENTER", line=title_line), 0)
        trs = [
            [cell_xml(0, 0, BW[0], HR, [tiny()], self.bf_b, margin=z),
             cell_xml(1, 0, BW[1], HR * 2, [title_p], self.bf_none, rowspan=2, margin=z),
             cell_xml(2, 0, BW[2], HR, [tiny()], self.bf_b, margin=z)],
            [cell_xml(0, 1, BW[0], HR, [tiny()], self.bf_lt, margin=z),
             cell_xml(2, 1, BW[2], HR, [tiny()], self.bf_rt, margin=z)],
            [cell_xml(0, 2, T, ih, items, self.bf_lrb, colspan=3, margin=(PAD, PAD, 100, PAD))],
        ]
        H = HR * 2 + ih
        gap = int(self.fmap.get("bogi_gap", 110))
        t = table_xml(self.ids, 3, 3, T, H, trs, self.bf_none, inmargin=(283, 283, 0, 0), outmargin=(0, 0, 0, gap), split="NONE")
        return self.opara(t, H + gap, "text")

    # ---------------- 선지 ----------------
    def choice_w(self, s):
        return text_width(s, self.metric("choice"))

    def combo_stops(self, items):
        """시험지 전체 ㄱ·ㄴ·ㄷ 조합 선지: 자리마다 가장 넓은 폭 + 같은 사이 간격 → 1×5 칸 폭"""
        ws = [0] * 5
        for q in items:
            cs = q.get("choices") or []
            if len(cs) == 5 and all(COMBO.match(strip_inline(c)) for c in cs):
                for i, c in enumerate(cs):
                    ws[i] = max(ws[i], self.choice_w("%s %s" % (MARK[i], c)))
        if not any(ws):
            return None
        avail = self.W - 300
        gap = (avail - sum(ws)) / 5          # 남는 폭을 다섯 칸에 고르게(마지막 칸도 여유를 둔다)
        if gap < 300:
            return None
        return [int(ws[i] + gap) for i in range(5)]

    def choices(self, q, combo):
        cs = q.get("choices") or []
        if not cs:
            return []
        labeled = ["%s %s" % (MARK[i] if i < len(MARK) else "(%d)" % (i + 1), c) for i, c in enumerate(cs)]
        role = "choice"
        lh = self.lh(role)
        if combo and len(cs) == 5 and all(COMBO.match(strip_inline(c)) for c in cs):
            return [self.choice_row(labeled, combo)]
        ws = [self.choice_w(c) for c in labeled]
        avail = self.W - 300
        widest = max(ws)
        n = len(labeled)
        for per in (5, 3):   # 짧으면 한 줄 5개, 중간이면 3+2 (테두리 없는 칸으로 자리를 고정)
            slot = avail / per
            if widest + 700 <= slot and n > 1:
                return [self.choice_row(labeled[i:i + per], [int(slot)] * per) for i in range(0, n, per)]
        # 길면 한 줄에 하나, 넘치면 번호 뒤에 맞춰 내어쓰기
        base_left = max(0, self.hdr.parapr_info(self.roles[role]["paraPr"])["left"])
        out = []
        for i, c in enumerate(labeled):
            hang = self.choice_w(c[:2])
            out.append(self.tpara(c, role, self.W, intent=-hang, left=base_left))
        return out

    def choice_row(self, parts, widths):
        """선지 한 줄 = 테두리 없는 1×N 칸(한글·미리보기 엔진 모두 자리가 똑같다)"""
        role = "choice"
        RH = int(self.lh(role)) + 60
        pp = self.pp(role, align="LEFT")
        tds = []
        for i, w in enumerate(widths):
            txt = parts[i] if i < len(parts) else ""
            tds.append(cell_xml(i, 0, w, RH, [para_xml(self.ids, self.runs(txt, role), pp, self.style(role))],
                                self.bf_none, margin=(0, 0, 0, 0)))
        t = table_xml(self.ids, 1, len(widths), sum(widths), RH, [tds], self.bf_none, inmargin=(0, 0, 0, 0), split="NONE")
        return self.opara(t, RH, role, align="LEFT")

    # ---------------- 문항 ----------------
    def question(self, q, combo):
        fm = self.fmap
        pts = (fm.get("points_format") or "[{pts}점]").format(pts=fmt_pts(q.get("pts", "")))
        stem = (q.get("stem") or "").strip()
        ask = (q.get("ask") or "").strip()
        blocks = q.get("blocks") or []
        out = []
        num = (fm.get("number_format") or "{no}.").format(no=q.get("no", ""))
        ncp = self.roles["question"]["number_charPr"]
        nm = Metric(self.hdr, ncp)
        num_w = nm.plain(num + " ")
        prefix = run_xml(num + " ", ncp)
        if not blocks and ask:
            stem, ask = ("%s %s" % (stem, ask)).strip(), ""
        main = stem if ask else ("%s %s" % (stem, pts)).strip()
        qpp_next = self.hdr.parapr_info(self.roles["question"]["paraPr"])["next"]
        out.append(self.tpara(main, "question", self.W, intent=-num_w, prefix=prefix, prefix_w=num_w,
                              next=qpp_next, keep_next=True))
        out += self.blocks(blocks, self.W - 300)
        if ask:
            indent = int(float(fm.get("ask_indent", 1.0)) * self.metric("text").em)
            out.append(self.tpara("%s %s" % (ask, pts), "text", self.W, intent=indent, keep_next=bool(q.get("bogi") or q.get("choices"))))
        if q.get("bogi"):
            out.append(self.bogi(q["bogi"]))
        out += self.choices(q, combo)
        out.append(self.blank())
        return out

    def essay_title(self):
        t = self.fmap.get("essay_title") or "서술형"
        role = "text"
        T = self.box_w
        p = para_xml(self.ids, self.runs(t, role, ("b",)), self.pp(role, align="CENTER"), self.style(role))
        h = self.lh(role) + 300
        trs = [[cell_xml(0, 0, T, h, [p], self.hdr.add_borderfill(top=True, bottom=True, width="0.4 mm"), margin=(141, 141, 150, 150))]]
        x = table_xml(self.ids, 1, 1, T, h, trs, self.bf_none, outmargin=(0, 0, 0, 283), split="NONE")
        return self.opara(x, h + 283, role)

    # ---------------- 머리 글자 바꾸기 ----------------
    def _replace_head(self, head, rules, meta, changed):
        """가장 안쪽 문단마다 규칙을 적용하고, 글이 길어져 칸(또는 꼬리말) 폭을 넘으면 그 문단 글자 크기를 줄인다"""
        out, last = [], 0
        for m in re.finditer(r"<hp:p [^>]*>(?:(?!<hp:p ).)*?</hp:p>", head, re.S):
            px = m.group(0)
            olds = re.findall(r"<hp:t>([^<]+)</hp:t>", px)
            news = [inspect_form.apply_rules(t, rules, meta) for t in olds]
            if news == olds:
                continue
            for a, b in zip(olds, news):
                if a != b:
                    changed.append((a.strip(), b.strip()))
            it = iter(news)
            npx = re.sub(r"<hp:t>([^<]+)</hp:t>", lambda mm: "<hp:t>%s</hp:t>" % next(it), px)
            avail = self._avail_width(head, m.start(), m.end())
            ow, nw = self._para_w(px), self._para_w(npx)
            if avail and nw > ow:
                # 글꼴 폭은 어림이라 칸 폭의 92%까지만 쓴다. 원래 글이 이미 그보다 넓었으면(그래도 맞았으면) 원래 폭까지
                target = max(ow, avail * 0.92)
                if nw > target * 1.01:
                    f = target / nw
                    def shrink(mm):
                        cid = int(mm.group(1))
                        if not self.hdr.has("charPr", cid):
                            return mm.group(0)
                        h0 = self.hdr.charpr_info(cid)["height"]
                        return '<hp:run charPrIDRef="%d"' % self.hdr.add_charpr(cid, height=max(int(h0 * 0.6), int(h0 * f)))
                    npx = re.sub(r'<hp:run charPrIDRef="(\d+)"', shrink, npx)
                    changed.append(("  └ 칸 폭을 넘어 글자 크기를 %d%%로 줄임" % max(60, int(100 * f)), ""))
            out.append(head[last:m.start()] + npx)
            last = m.end()
        return "".join(out) + head[last:]

    def _para_w(self, px):
        w = 0.0
        for cid, body in re.findall(r'<hp:run charPrIDRef="(\d+)">(.*?)</hp:run>', px, re.S):
            t = html.unescape("".join(re.findall(r"<hp:t>([^<]*)</hp:t>", body)))
            if t and self.hdr.has("charPr", int(cid)):
                w += Metric(self.hdr, int(cid)).plain(t)
        return w

    def _avail_width(self, head, a, b):
        """문단이 든 칸의 안쪽 폭, 꼬리말·머리말이면 그 폭. 모르면 None"""
        tc = head.rfind("<hp:tc ", 0, a)
        if tc >= 0 and head.rfind("</hp:tc>", 0, a) < tc:
            m = re.compile(r'<hp:cellSz width="(\d+)"[^>]*/><hp:cellMargin left="(\d+)" right="(\d+)"').search(head, b)
            if m:
                return int(m.group(1)) - int(m.group(2)) - int(m.group(3))
        sl = head.rfind("<hp:subList ", 0, a)
        if sl >= 0 and head.rfind("</hp:subList>", 0, a) < sl:
            m = re.match(r'<hp:subList [^>]*textWidth="(\d+)"', head[sl:])
            if m and int(m.group(1)) > 0:
                return int(m.group(1))
        return None

    # ---------------- 머리 ----------------
    def head(self, items, pages=None):
        changed = []
        tops = top_paragraphs(self.sec)
        bs = int((self.fmap.get("body_start") or {}).get("index", len(tops)))
        bs = max(1, min(bs, len(tops)))
        cut = tops[bs][0] if bs < len(tops) else tops[-1][1]
        head = self.sec[:cut]
        # 양식의 줄 배치 기록(linesegarray)은 예시 문항 기준이라 버린다(한글이 열 때 다시 계산)
        head = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", head, flags=re.S)
        # 첫 문단에 떠 있는 머리 표(글자처럼 취급 아님, 문단·단 기준)는 쪽 기준으로 바꾼다.
        # 첫 문단은 쪽 맨 위라 한글에서 자리는 같고, 두 단 모두 이 표를 피해 흐른다(미리보기 엔진도 같게 그림).
        if tops:
            a, b = tops[0]
            p0 = head[a:b]
            p0n = re.sub(r'(<hp:pos treatAsChar="0"[^>]*?)vertRelTo="PARA" horzRelTo="(?:COLUMN|PARA)"',
                         r'\1vertRelTo="PAGE" horzRelTo="PAGE"', p0)
            if p0n != p0:
                head = head[:a] + p0n + head[b:]
                changed.append(("머리 표 위치 기준", "쪽(PAGE) 기준"))
        # 학교·학년·과목 글자
        meta = {k: ("" if v is None else str(v)) for k, v in self.meta.items()}
        meta.setdefault("semester", "")
        rules = self.fmap.get("replace") or []
        if self.fmap.get("update_summary", True):
            mc = [q for q in items if q.get("kind") != "서술형"]
            ps = [float(q.get("pts") or 0) for q in mc]
            cnt = {}
            for p in ps:
                cnt[p] = cnt.get(p, 0) + 1
            formula = " + ".join("%d문항×%s점" % (n, fmt_pts(p)) for p, n in sorted(cnt.items())) + " = %s점" % fmt_pts(sum(ps))
            rules = list(rules) + [
                {"pattern": r"총\s*\d+\s*문항", "to": "총 %d문항" % len(mc)},
                {"pattern": r"\d+\s*문항\s*×\s*[\d.]+\s*점(?:\s*\+\s*\d+\s*문항\s*×\s*[\d.]+\s*점)*\s*=\s*[\d.]+\s*점",
                 "to": formula.replace("{", "{{").replace("}", "}}")},
            ]
        if pages:
            rules = list(rules) + [{"pattern": r"총\s*\(\s*\d*\s*\)\s*쪽", "to": "총( %s )쪽" % pages}]
        if rules:
            head = self._replace_head(head, rules, meta, changed)
        return head, changed


def main(argv=None):
    setup_console()
    ap = argparse.ArgumentParser(description="exam.json → 학교 양식 hwpx 시험지")
    ap.add_argument("exam")
    ap.add_argument("form", help="양식 .hwpx(또는 풀어 둔 폴더). 없으면 templates/기본양식.hwpx")
    ap.add_argument("out")
    ap.add_argument("--map", help="form_map.json (없으면 inspect_form.py 추측을 그대로 씀)")
    ap.add_argument("--only", help="이 번호 문항만(예: 1,3)")
    ap.add_argument("--pages", help="꼬리말 「총( N )쪽」 의 N")
    a = ap.parse_args(argv)

    exam_path = Path(a.exam).resolve()
    exam = load_json(exam_path)
    meta = exam.get("meta") or {}
    items = exam.get("items") or []
    if a.only:
        want = {int(x) for x in a.only.split(",") if x.strip()}
        items = [q for q in items if int(q.get("no", 0)) in want]
    if not items:
        raise SystemExit("[오류] 만들 문항이 없습니다.")
    pkg = Package(a.form)
    if a.map:
        fmap = load_json(a.map)
    else:
        fmap, _ = inspect_form.guess_map(pkg)
        print("(form_map 없이 추측으로 만듭니다. 모양이 이상하면 inspect_form.py 로 map 을 만들어 고친 뒤 --map 으로 주세요)")
    B = Builder(pkg, fmap, meta, exam_path.parent)

    mc = [q for q in items if q.get("kind") != "서술형"]
    essay = [q for q in items if q.get("kind") == "서술형"]
    combo = B.combo_stops(mc)
    body = []
    for q in mc:
        body += B.question(q, combo)
    if essay:
        body.append(B.essay_title())
        for q in essay:
            body += B.question(q, combo)
    head, changed = B.head(items, a.pages)
    section = head + "".join(body) + "</hs:sec>"
    check_xml(section, "본문")
    hdr_xml = B.hdr.finalize()
    check_xml(hdr_xml, "header")
    pkg.set_text(B.secname, section)
    pkg.set_text("Contents/header.xml", hdr_xml)
    # 옛 미리보기(양식의 예시 문항 모습)는 버리고 글 미리보기만 새로
    hpf = pkg.text("Contents/content.hpf")
    if "Preview/PrvImage.png" in pkg.files and "PrvImage" not in hpf:
        del pkg.files["Preview/PrvImage.png"]
    if "Preview/PrvText.txt" in pkg.files:
        pkg.files["Preview/PrvText.txt"] = (meta.get("title") or "시험지").encode("utf-8")
    pkg.save(a.out)

    nfig = sum(1 for n in pkg.files if n.startswith("BinData/"))
    print("만듦: %s" % Path(a.out).resolve())
    print("  문항 %d (선택형 %d, 서술형 %d) · 줄 간격 %d%% · 단 폭 %d · 그림 %d · 조합 선지 칸 %s" % (
        len(items), len(mc), len(essay), B.line, B.W, nfig, combo))
    for o, n in changed:
        print("  머리 글 바꿈: %s → %s" % (o[:40], n[:40]))
    if UNKNOWN_TEX:
        warn("한글 수식으로 못 바꾼 LaTeX 명령: %s (한글에서 확인)" % ", ".join(sorted(UNKNOWN_TEX)))
    for w in WARN:
        print("[경고] " + w)


if __name__ == "__main__":
    main()
