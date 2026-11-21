# -*- coding: utf-8 -*-
"""exam.json → 정답표 hwpx (A4 세로 한 단)

    python build_answers.py <exam.json> <out.hwpx> [--form 양식.hwpx] [--map form_map.json]

- 위: 번호·유형·정답·배점·단원·성취기준·난이도 표 + 배점 합계
- 아래: 서술형마다 모범 답안과 채점 기준(점수·기준) 표
- 글꼴·테두리 굵기는 --form 양식(없으면 templates/기본양식.hwpx)의 본문 모양을 빌린다. 쪽 설정은 늘 A4 세로·한 단.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwpx_common import (Header, Ids, Metric, Package, cell_xml, check_xml, fmt_pts, load_json, obj_run,  # noqa: E402
                         para_xml, run_xml, setup_console, strip_inline, table_xml)
import inspect_form  # noqa: E402

HERE = Path(__file__).resolve().parent
A4W, A4H = 59528, 84188
ML = MR = 5669   # 20mm
MT, MB = 4252, 4252
TW = A4W - ML - MR


def secpr_xml() -> str:
    return ('<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
            'outlineShapeIDRef="0" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0"><hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
            '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
            '<hp:pagePr landscape="WIDELY" width="%d" height="%d" gutterType="LEFT_ONLY"><hp:margin header="0" footer="1417" gutter="0" left="%d" right="%d" top="%d" bottom="%d"/></hp:pagePr>'
            '<hp:footNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/><hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hp:noteSpacing betweenNotes="284" belowLine="568" aboveLine="852"/><hp:numbering type="CONTINUOUS" newNum="1"/><hp:placement place="EACH_COLUMN" beneathText="0"/></hp:footNotePr>'
            '<hp:endNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/><hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hp:noteSpacing betweenNotes="0" belowLine="568" aboveLine="852"/><hp:numbering type="CONTINUOUS" newNum="1"/><hp:placement place="END_OF_DOCUMENT" beneathText="0"/></hp:endNotePr>'
            '</hp:secPr>') % (A4W, A4H, ML, MR, MT, MB)


class Sheet:
    def __init__(self, pkg: Package, fmap: dict, line: int):
        self.pkg = pkg
        self.hdr = Header(pkg.text("Contents/header.xml"))
        roles = fmap.get("roles", {})
        h = self.hdr

        def pick(*names):
            for n in names:
                r = roles.get(n) or {}
                if h.has("charPr", r.get("charPr")) and h.has("paraPr", r.get("paraPr")):
                    return r
            raise SystemExit("[오류] 양식에서 본문 글자 모양을 찾지 못했습니다. --map 을 확인하세요.")
        base = pick("text", "question")
        tbase = pick("table_text", "box_text", "text", "question")
        self.cp = base["charPr"]
        self.tcp = tbase["charPr"]
        self.pp_base = base["paraPr"]
        self.line = line
        self.bold = h.add_charpr(self.cp, bold=True)
        self.tbold = h.add_charpr(self.tcp, bold=True)
        size = h.charpr_info(self.cp)["height"]
        self.title_cp = h.add_charpr(self.cp, bold=True, height=int(size * 1.5))
        lw = fmap.get("line_width") or h.common_line_width()
        self.bf = h.add_borderfill(True, True, True, True, lw)
        self.bf_none = h.add_borderfill(False, False, False, False, lw)
        self.ids = Ids()
        self.m = Metric(h, self.tcp)

    def pp(self, align="JUSTIFY", intent=0):
        return self.hdr.add_parapr(self.pp_base, align=align, intent=intent, left=0, right=0, prev=0, next=0, line=self.line)

    def para(self, text, cp=None, align="JUSTIFY"):
        return para_xml(self.ids, run_xml(text, cp or self.cp), self.pp(align))

    def lines(self, text, width):
        w = self.m.plain(strip_inline(text)) * 1.05
        return max(1, math.ceil(w / max(width, 2000)))

    def table(self, rows, widths, head_rows=1, aligns=None):
        """rows: [[글, …]] → 표 문단"""
        lh = self.hdr.charpr_info(self.tcp)["height"] * self.line / 100
        trs, H = [], 0
        for r, row in enumerate(rows):
            n = max(self.lines(str(v), widths[c] - 400) for c, v in enumerate(row))
            rh = int(n * lh + 300)
            cells = []
            for c, v in enumerate(row):
                al = (aligns[c] if aligns else "CENTER") if r >= head_rows else "CENTER"
                cp = self.tbold if r < head_rows else self.tcp
                ps = [para_xml(self.ids, run_xml(strip_inline(x), cp), self.pp(al)) for x in (str(v).split("\n") or [""])]
                cells.append(cell_xml(c, r, widths[c], rh, ps, self.bf, margin=(200, 200, 141, 141)))
            trs.append(cells)
            H += rh
        t = table_xml(self.ids, len(rows), len(widths), sum(widths), H, trs, self.bf, outmargin=(0, 0, 0, 0), repeat=1 if head_rows else 0)
        return para_xml(self.ids, obj_run(t, self.cp), self.pp("CENTER"))


def main(argv=None):
    setup_console()
    ap = argparse.ArgumentParser(description="exam.json → 정답표 hwpx")
    ap.add_argument("exam")
    ap.add_argument("out")
    ap.add_argument("--form", help="글꼴을 빌릴 양식 hwpx (없으면 templates/기본양식.hwpx)")
    ap.add_argument("--map", help="form_map.json")
    a = ap.parse_args(argv)

    exam = load_json(a.exam)
    meta = exam.get("meta") or {}
    items = exam.get("items") or []
    form = Path(a.form) if a.form else HERE / "templates" / "기본양식.hwpx"
    pkg = Package(form)
    fmap = load_json(a.map) if a.map else inspect_form.guess_map(pkg)[0]
    secname = pkg.section_names()[0]
    S = Sheet(pkg, fmap, int(meta.get("line_spacing") or 160))

    mc = [q for q in items if q.get("kind") != "서술형"]
    es = [q for q in items if q.get("kind") == "서술형"]
    pmc = sum(float(q.get("pts") or 0) for q in mc)
    pes = sum(float(q.get("pts") or 0) for q in es)
    body = []
    title = (meta.get("title") or "시험") + " 정답표"
    body.append(S.para(title, S.title_cp, "CENTER"))
    sub = "판 %s · %s" % (meta.get("version", ""), meta.get("date", ""))
    body.append(S.para(sub.strip(" ·"), S.cp, "CENTER"))
    body.append(S.para("", S.cp))

    # 정답·배점 표
    widths_rel = [6, 8, 9, 7, 20, 18, 7]
    widths = [int(TW * w / sum(widths_rel)) for w in widths_rel]
    rows = [["번호", "유형", "정답", "배점", "단원", "성취기준", "난이도"]]
    for q in items:
        ans = q.get("ans", "") if q.get("kind") != "서술형" else "아래 참고"
        rows.append([str(q.get("no", "")), q.get("kind", "선택형"), ans, fmt_pts(q.get("pts", "")),
                     q.get("unit", ""), q.get("standard", ""), q.get("level", "")])
    rows.append(["합계", "", "", fmt_pts(pmc + pes), "", "", ""])
    body.append(S.table(rows, widths, aligns=["CENTER", "CENTER", "CENTER", "CENTER", "LEFT", "CENTER", "CENTER"]))
    body.append(S.para("", S.cp))
    summary = "선택형 %d문항 %s점" % (len(mc), fmt_pts(pmc))
    if es:
        summary += " · 서술형 %d문항 %s점" % (len(es), fmt_pts(pes))
    summary += " · 합계 %s점" % fmt_pts(pmc + pes)
    body.append(S.para(summary, S.bold, "CENTER"))
    # 정답 분포(선택형)
    dist = {}
    for q in mc:
        dist[q.get("ans", "?")] = dist.get(q.get("ans", "?"), 0) + 1
    if dist:
        body.append(S.para("정답 분포: " + "  ".join("%s %d개" % (k, dist[k]) for k in sorted(dist)), S.cp, "CENTER"))

    # 서술형
    for q in es:
        body.append(S.para("", S.cp))
        body.append(S.para("서술형 %s번 (%s점)" % (q.get("no", ""), fmt_pts(q.get("pts", ""))), S.bold))
        body.append(S.table([["모범 답안"], [strip_inline(str(q.get("ans", "")))]], [TW], aligns=["LEFT"]))
        rub = q.get("rubric") or []
        if rub:
            body.append(S.para("", S.cp))
            rrows = [["점수", "채점 기준"]] + [[fmt_pts(r.get("점수", r.get("score", ""))), r.get("기준", r.get("criteria", ""))] for r in rub]
            body.append(S.table(rrows, [int(TW * 0.14), TW - int(TW * 0.14)], aligns=["CENTER", "LEFT"]))

    sec = pkg.text(secname)
    root = sec[:sec.find("<hp:p ")]
    first = ('<hp:p id="1" paraPrIDRef="%d" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="%d">%s'
             '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl><hp:t/></hp:run></hp:p>') % (
        S.pp(), S.cp, secpr_xml())
    section = root + first + "".join(body) + "</hs:sec>"
    check_xml(section, "정답표 본문")
    hx = re.sub(r'secCnt="\d+"', 'secCnt="1"', S.hdr.finalize(), count=1)
    check_xml(hx, "header")
    pkg.set_text(secname, section)
    pkg.set_text("Contents/header.xml", hx)
    for n in list(pkg.files):   # 양식의 그림·다른 구역은 정답표에 필요 없다
        if n.startswith("BinData/") or (re.match(r"Contents/section[1-9]\d*\.xml$", n)):
            del pkg.files[n]
    hpf = pkg.text("Contents/content.hpf")
    hpf = re.sub(r'<opf:item id="[^"]*" href="BinData/[^"]*"[^>]*/>', "", hpf)
    hpf = re.sub(r'<opf:item id="section[1-9]\d*"[^>]*/>|<opf:itemref idref="section[1-9]\d*"[^>]*/>', "", hpf)
    pkg.set_text("Contents/content.hpf", hpf)
    if "Preview/PrvImage.png" in pkg.files and "PrvImage" not in hpf:
        del pkg.files["Preview/PrvImage.png"]
    if "Preview/PrvText.txt" in pkg.files:
        pkg.files["Preview/PrvText.txt"] = title.encode("utf-8")
    pkg.save(a.out)
    print("만듦: %s" % Path(a.out).resolve())
    print("  " + summary)


if __name__ == "__main__":
    main()
