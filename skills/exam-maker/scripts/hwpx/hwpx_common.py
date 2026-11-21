# -*- coding: utf-8 -*-
"""hwpx 공용 도구 (inspect_form.py · build_exam.py · build_answers.py가 같이 쓴다)

- Package : hwpx(zip) 또는 풀어 둔 폴더를 읽고 다시 묶는다.
- Header  : header.xml 의 글자 모양(charPr)·문단 모양(paraPr)·테두리(borderFill)·탭(tabPr) 목록을 읽고,
            양식의 모양을 복제해 새 번호로 덧붙인다(양식에 있던 번호는 건드리지 않는다).
- 글 폭 어림, LaTeX 꼴 → 한글 수식 변환, 문단·표·그림·수식 XML 조각.

표준 라이브러리만 쓴다(그림 크기는 Pillow가 있으면 쓰고, 없으면 PNG·JPEG 머리에서 직접 읽는다).
한글 단위(HWPUNIT): 1pt = 100, 1mm ≈ 283.46.
"""
from __future__ import annotations

import html
import math
import re
import struct
import sys
import zipfile
from pathlib import Path

MM = 283.465  # 1mm 의 HWPUNIT
NS_UNIT = "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar"


def setup_console():
    """윈도우 콘솔(cp949)에서도 한글·기호 출력이 깨져 멈추지 않게 한다."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# ====================================================================
# 패키지
# ====================================================================
class Package:
    """hwpx 묶음. files: {이름: bytes} (읽은 순서 유지)"""

    def __init__(self, path):
        p = Path(path)
        self.path = p
        self.files: dict[str, bytes] = {}
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(p).as_posix()
                if any(part.startswith(".") or part == "__MACOSX" for part in rel.split("/")):
                    continue
                self.files[rel] = f.read_bytes()
        elif p.is_file():
            try:
                with zipfile.ZipFile(p) as z:
                    for info in z.infolist():
                        if not info.is_dir():
                            self.files[info.filename] = z.read(info)
            except zipfile.BadZipFile:
                raise SystemExit(
                    "[오류] %s 는 hwpx(zip) 파일이 아닙니다. 옛 .hwp 파일이면 윈도우에서 먼저\n"
                    "       python hangul_win.py to-hwpx 양식.hwp 양식.hwpx 로 바꾸세요." % p.name)
        else:
            raise SystemExit("[오류] 파일을 찾을 수 없습니다: %s" % p)
        if "Contents/header.xml" not in self.files:
            raise SystemExit("[오류] %s 안에 Contents/header.xml 이 없습니다(hwpx 양식이 아닌 듯합니다)." % p)

    def text(self, name: str) -> str:
        return self.files[name].decode("utf-8")

    def set_text(self, name: str, s: str):
        self.files[name] = s.encode("utf-8")

    def section_names(self):
        return sorted((n for n in self.files if re.match(r"Contents/section\d+\.xml$", n)),
                      key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)))

    def add_bindata(self, raw: bytes, ext: str) -> str:
        """BinData/에 그림을 넣고 content.hpf 목록에 올린다. 돌려주는 값 = binaryItemIDRef"""
        hpf = self.text("Contents/content.hpf")
        used = set(re.findall(r'<opf:item id="([^"]+)"', hpf))
        k = 1
        while "image%d" % k in used or ("BinData/image%d.%s" % (k, ext)) in self.files:
            k += 1
        iid = "image%d" % k
        name = "BinData/%s.%s" % (iid, ext)
        self.files[name] = raw
        mt = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp"}.get(ext, "image/png")
        item = '<opf:item id="%s" href="%s" media-type="%s" isEmbeded="1"/>' % (iid, name, mt)
        hpf = hpf.replace("</opf:manifest>", item + "</opf:manifest>", 1)
        self.set_text("Contents/content.hpf", hpf)
        return iid

    # 다른 도구가 hwp→hwpx 로 바꿀 때 남긴 「옛 hwp 에서 바꾼 문서」 표시.
    # 새로 조판한 시험지에 남아 있으면 rhwp 같은 엔진이 옛 hwp 방식(키 큰 수식·글 줄 높이를 다시 재지 않음)으로 배치해
    # 분수 줄이 아래 줄과 겹치고 상자 안 글이 넘친다. 한글은 이 파일을 쓰지 않는다.
    CONVERSION_MARKS = ("META-INF/rhwp-hwp5-origin",)

    def drop_conversion_marks(self) -> list:
        gone = [n for n in self.CONVERSION_MARKS if n in self.files]
        for n in gone:
            del self.files[n]
        return gone

    def save(self, out):
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w") as z:
            z.writestr(zipfile.ZipInfo("mimetype"), self.files.get("mimetype", b"application/hwp+zip"),
                       compress_type=zipfile.ZIP_STORED)
            for name, data in self.files.items():
                if name == "mimetype":
                    continue
                ct = zipfile.ZIP_STORED if name.startswith("BinData/") else zipfile.ZIP_DEFLATED
                z.writestr(name, data, compress_type=ct)


# ====================================================================
# header.xml
# ====================================================================
LIST_OF = {"charPr": "charProperties", "paraPr": "paraProperties", "borderFill": "borderFills",
           "tabPr": "tabProperties", "style": "styles", "numbering": "numberings"}


def _elements(xml: str, tag: str) -> dict[int, str]:
    pat = re.compile(r'<hh:%s id="(\d+)"[^>]*?(?:/>|>.*?</hh:%s>)' % (tag, tag), re.S)
    return {int(m.group(1)): m.group(0) for m in pat.finditer(xml)}


def _attr(x: str, name: str, default=None):
    m = re.search(r'\b%s="([^"]*)"' % name, x)
    return m.group(1) if m else default


class Header:
    def __init__(self, xml: str):
        self.xml = xml
        self._cache: dict = {}
        self.fonts = {}
        m = re.search(r'<hh:fontface lang="HANGUL".*?</hh:fontface>', xml, re.S)
        if m:
            for fm in re.finditer(r'<hh:font id="(\d+)" face="([^"]*)"', m.group(0)):
                self.fonts[int(fm.group(1))] = fm.group(2)

    # ---- 목록
    def items(self, tag: str) -> dict[int, str]:
        return _elements(self.xml, tag)

    def get(self, tag: str, i: int) -> str | None:
        return self.items(tag).get(int(i))

    def has(self, tag: str, i) -> bool:
        return i is not None and self.get(tag, int(i)) is not None

    # ---- 정보
    def charpr_info(self, i: int) -> dict:
        x = self.get("charPr", i) or ""
        fr = re.search(r'<hh:fontRef hangul="(\d+)"', x)
        ratio = re.search(r'<hh:ratio hangul="(\d+)"', x)
        sp = re.search(r'<hh:spacing hangul="(-?\d+)"', x)
        ul = re.search(r'<hh:underline type="(\w+)"', x)
        return {
            "id": i,
            "height": int(_attr(x, "height", "1000")),
            "font": self.fonts.get(int(fr.group(1)) if fr else 0, "?"),
            "ratio": int(ratio.group(1)) if ratio else 100,
            "spacing": int(sp.group(1)) if sp else 0,
            "bold": "<hh:bold/>" in x,
            "italic": "<hh:italic/>" in x,
            "underline": bool(ul and ul.group(1) != "NONE"),
            "color": _attr(x, "textColor", "#000000"),
        }

    def parapr_info(self, i: int) -> dict:
        x = self.get("paraPr", i) or ""
        case = x.split("<hp:default>")[0]

        def mv(k):
            m = re.search(r'<hc:%s value="(-?\d+)"' % k, case)
            return int(m.group(1)) if m else 0

        ls = re.search(r'<hh:lineSpacing type="(\w+)" value="(-?\d+)"', case)
        hd = re.search(r'<hh:heading type="(\w+)" idRef="(\d+)"', x)
        return {
            "id": i,
            "align": (re.search(r'<hh:align horizontal="(\w+)"', x) or [None, "?"])[1],
            "heading": hd.group(1) if hd else "NONE",
            "numbering": int(hd.group(2)) if hd else 0,
            "intent": mv("intent"), "left": mv("left"), "right": mv("right"), "prev": mv("prev"), "next": mv("next"),
            "line_type": ls.group(1) if ls else "PERCENT",
            "line": int(ls.group(2)) if ls else 160,
            "tab": int(_attr(x, "tabPrIDRef", "0")),
        }

    def borderfill_info(self, i: int) -> dict:
        x = self.get("borderFill", i) or ""
        out = {"id": i}
        for side in ("left", "right", "top", "bottom"):
            m = re.search(r'<hh:%sBorder type="(\w+)" width="([^"]*)"' % side, x)
            out[side] = (m.group(1), m.group(2)) if m else ("NONE", "0.1 mm")
        out["fill"] = bool(re.search(r'faceColor="#(?!FFFFFF)[0-9A-Fa-f]{6}"', x))
        return out

    def numbering_charpr(self, nid: int):
        x = self.get("numbering", nid) or ""
        m = re.search(r'<hh:paraHead [^>]*level="1"[^>]*charPrIDRef="(\d+)"', x)
        if m and int(m.group(1)) < 4294967295:
            return int(m.group(1))
        return None

    # ---- 덧붙이기
    def _next_id(self, tag: str) -> int:
        ids = self.items(tag)
        return (max(ids) + 1) if ids else 0

    def _append(self, tag: str, x: str):
        lst = LIST_OF[tag]
        if "</hh:%s>" % lst in self.xml:
            self.xml = self.xml.replace("</hh:%s>" % lst, x + "</hh:%s>" % lst, 1)
        else:  # 빈 목록(<hh:tabProperties itemCnt="0"/>)
            self.xml = re.sub(r'<hh:%s itemCnt="\d+"\s*/>' % lst, '<hh:%s itemCnt="0">%s</hh:%s>' % (lst, x, lst), self.xml, 1)

    def finalize(self) -> str:
        for tag, lst in LIST_OF.items():
            m = re.search(r'<hh:%s itemCnt="\d+">(.*?)</hh:%s>' % (lst, lst), self.xml, re.S)
            if m:
                n = len(re.findall(r'<hh:%s id="' % tag, m.group(1)))
                self.xml = self.xml[:m.start()] + re.sub(r'itemCnt="\d+"', 'itemCnt="%d"' % n, m.group(0), 1) + self.xml[m.end():]
        return self.xml

    def add_charpr(self, base: int, *, bold=None, italic=None, underline=None, sup=False, sub=False,
                   height=None, color=None, ratio=None) -> int:
        """base 글자 모양을 복제해 굵게·기울임·밑줄·위아래 첨자·크기·장평만 바꾼 새 번호"""
        key = ("cp", base, bold, italic, underline, sup, sub, height, color, ratio)
        if key in self._cache:
            return self._cache[key]
        x = self.get("charPr", base)
        if x is None:
            raise KeyError("글자 모양 %s 이(가) 양식에 없습니다" % base)
        if bold is None and italic is None and underline is None and not (sup or sub or height or color or ratio):
            self._cache[key] = base
            return base
        nid = self._next_id("charPr")
        x = re.sub(r'^<hh:charPr id="\d+"', '<hh:charPr id="%d"' % nid, x)
        if height:
            x = re.sub(r'(<hh:charPr [^>]*?height=")\d+', r'\g<1>%d' % int(height), x, 1)
        if color:
            x = re.sub(r'(textColor=")[^"]*', r'\g<1>%s' % color, x, 1)
        if ratio:
            x = re.sub(r'<hh:ratio [^>]*/>', '<hh:ratio %s/>' % " ".join(
                '%s="%d"' % (k, int(ratio)) for k in ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user")), x, 1)
        if bold is not None or italic is not None:
            b = ("<hh:bold/>" in x) if bold is None else bold
            it = ("<hh:italic/>" in x) if italic is None else italic
            x = x.replace("<hh:bold/>", "").replace("<hh:italic/>", "")
            ins = ("<hh:italic/>" if it else "") + ("<hh:bold/>" if b else "")
            for anchor in ("<hh:underline", "<hh:strikeout", "<hh:outline", "<hh:shadow", "</hh:charPr>"):
                if anchor in x:
                    x = x.replace(anchor, ins + anchor, 1)
                    break
        if underline is not None:
            if "<hh:underline" in x:
                x = re.sub(r'<hh:underline type="\w+"', '<hh:underline type="%s"' % ("BOTTOM" if underline else "NONE"), x, 1)
            elif underline:
                x = x.replace("<hh:strikeout", '<hh:underline type="BOTTOM" shape="SOLID" color="#000000"/><hh:strikeout', 1)
        if sup or sub:
            x = x.replace("<hh:supscript/>", "").replace("<hh:subscript/>", "")
            x = x.replace("</hh:charPr>", ("<hh:supscript/>" if sup else "<hh:subscript/>") + "</hh:charPr>")
        self._append("charPr", x)
        self._cache[key] = nid
        return nid

    def add_parapr(self, base: int, *, align=None, intent=None, left=None, right=None, prev=None, next=None,
                   line=None, tab=None, keep_next=None, snap=None) -> int:
        """base 문단 모양을 복제해 정렬·여백·줄 간격·탭만 바꾼 새 번호(문단 번호 머리는 늘 끈다)
        intent < 0 이면 내어쓰기(첫 줄은 left, 둘째 줄부터 left+|intent|)."""
        key = ("pp", base, align, intent, left, right, prev, next, line, tab, keep_next, snap)
        if key in self._cache:
            return self._cache[key]
        x = self.get("paraPr", base)
        if x is None:
            raise KeyError("문단 모양 %s 이(가) 양식에 없습니다" % base)
        nid = self._next_id("paraPr")
        x = re.sub(r'^<hh:paraPr id="\d+"', '<hh:paraPr id="%d"' % nid, x)
        if tab is not None:
            x = re.sub(r'tabPrIDRef="\d+"', 'tabPrIDRef="%d"' % tab, x, 1)
        if snap is not None:
            x = re.sub(r'snapToGrid="\d"', 'snapToGrid="%d"' % (1 if snap else 0), x, 1)
        if align:
            x = re.sub(r'(<hh:align horizontal=")\w+', r'\g<1>' + align, x, 1)
        x = re.sub(r'<hh:heading [^>]*/>', '<hh:heading type="NONE" idRef="0" level="0"/>', x, 1)
        if keep_next is not None:
            x = re.sub(r'keepWithNext="\d"', 'keepWithNext="%d"' % (1 if keep_next else 0), x, 1)
        vals = {"intent": intent, "left": left, "right": right, "prev": prev, "next": next}

        def apply(seg, mul):
            for k, v in vals.items():
                if v is not None:
                    seg = re.sub(r'(<hc:%s value=")-?\d+' % k, lambda m: m.group(1) + str(int(round(v * mul))), seg, 1)
            if line is not None:
                seg = re.sub(r'<hh:lineSpacing type="\w+" value="-?\d+"', '<hh:lineSpacing type="PERCENT" value="%d"' % int(line), seg, 1)
            return seg

        if "<hp:default>" in x:  # 한글 규칙: 기본(default) 갈래의 여백은 HWPUNIT 값의 두 배로 적는다
            a, b = x.split("<hp:default>", 1)
            x = apply(a, 1) + "<hp:default>" + apply(b, 2)
        else:
            x = apply(x, 1)
        self._append("paraPr", x)
        self._cache[key] = nid
        return nid

    def add_tabpr(self, stops, kind="LEFT") -> int:
        stops = tuple(int(s) for s in stops)
        key = ("tab", stops, kind)
        if key in self._cache:
            return self._cache[key]
        nid = self._next_id("tabPr")
        items = "".join(
            '<hp:switch><hp:case hp:required-namespace="%s"><hh:tabItem pos="%d" type="%s" leader="NONE" unit="HWPUNIT"/></hp:case>'
            '<hp:default><hh:tabItem pos="%d" type="%s" leader="NONE"/></hp:default></hp:switch>' % (NS_UNIT, p, kind, p * 2, kind)
            for p in stops)
        self._append("tabPr", '<hh:tabPr id="%d" autoTabLeft="0" autoTabRight="0">%s</hh:tabPr>' % (nid, items))
        self._cache[key] = nid
        return nid

    def add_borderfill(self, left=False, right=False, top=False, bottom=False, width="0.12 mm") -> int:
        """선 있는 쪽만 SOLID. 양식에 똑같은 테두리가 있으면 그 번호를 쓴다."""
        key = ("bf", left, right, top, bottom, width)
        if key in self._cache:
            return self._cache[key]
        want = {"left": left, "right": right, "top": top, "bottom": bottom}
        for i in sorted(self.items("borderFill")):
            info = self.borderfill_info(i)
            if info["fill"]:
                continue
            ok = True
            for side, on in want.items():
                t, w = info[side]
                if on and not (t == "SOLID" and w == width):
                    ok = False
                if not on and t != "NONE":
                    ok = False
            x = self.get("borderFill", i)
            if ok and 'type="NONE"' in re.search(r'<hh:slash[^>]*>', x).group(0):
                self._cache[key] = i
                return i
        nid = self._next_id("borderFill")
        sides = "".join('<hh:%sBorder type="%s" width="%s" color="#000000"/>' % (s, "SOLID" if on else "NONE", width)
                        for s, on in want.items())
        x = ('<hh:borderFill id="%d" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
             '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
             '%s<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/></hh:borderFill>') % (nid, sides)
        self._append("borderFill", x)
        self._cache[key] = nid
        return nid

    def common_line_width(self) -> str:
        """양식 표 선에 가장 많이 쓴 굵기"""
        cnt = {}
        for i in self.items("borderFill"):
            info = self.borderfill_info(i)
            for side in ("left", "right", "top", "bottom"):
                t, w = info[side]
                if t == "SOLID":
                    cnt[w] = cnt.get(w, 0) + 1
        return max(cnt, key=cnt.get) if cnt else "0.12 mm"


# ====================================================================
# 쪽 설정
# ====================================================================
def page_geometry(sec: str) -> dict:
    m = re.search(r'<hp:pagePr landscape="(\w+)" width="(\d+)" height="(\d+)"', sec)
    mg = re.search(r'<hp:margin header="(\d+)" footer="(\d+)" gutter="(\d+)" left="(\d+)" right="(\d+)" top="(\d+)" bottom="(\d+)"', sec)
    W, H = (int(m.group(2)), int(m.group(3))) if m else (59528, 84188)
    if m and m.group(1) == "NARROWLY":  # 가로 용지
        W, H = max(W, H), min(W, H)
    hd, ft, gut, L, R, T, B = (int(x) for x in mg.groups()) if mg else (1417, 1417, 0, 2834, 2834, 2834, 2834)
    cols = [(int(c.group(1)), int(c.group(2))) for c in
            re.finditer(r'<hp:colPr [^>]*colCount="(\d+)"[^>]*sameGap="(\d+)"', sec)]
    n, gap = max(cols) if cols else (1, 0)
    text_w = W - L - R - gut
    col_w = (text_w - gap * (n - 1)) / n
    return {"width": W, "height": H, "left": L, "right": R, "top": T, "bottom": B, "header": hd, "footer": ft,
            "gutter": gut, "cols": n, "gap": gap, "text_w": text_w, "col_w": int(col_w),
            "paper": paper_name(W, H)}


def paper_name(W, H):
    w, h = sorted((W / MM, H / MM))
    for name, (a, b) in {"A4": (210, 297), "B4": (257, 364), "A3": (297, 420), "B5": (182, 257), "8절": (272, 394)}.items():
        if abs(w - a) < 3 and abs(h - b) < 3:
            return name
    return "%.0f×%.0fmm" % (w, h)


# ====================================================================
# 최상위 문단 나누기
# ====================================================================
def top_paragraphs(sec: str) -> list[tuple[int, int]]:
    """section XML 에서 최상위 <hp:p> 의 (시작, 끝) 위치 목록"""
    spans, depth, start = [], 0, None
    for m in re.finditer(r"<hp:p |</hp:p>", sec):
        if m.group(0) == "<hp:p ":
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, m.end()))
                start = None
    return spans


def plain_text(xml: str) -> str:
    return html.unescape("".join(re.findall(r"<hp:t>([^<]*)", xml)))


def own_text(pxml: str) -> str:
    """문단 자신의 글(안에 든 표·글상자의 글은 뺀다)"""
    x = re.sub(r"<hp:(tbl|rect|container|ellipse|polygon|footer|header)\b.*?</hp:\1>", "", pxml, flags=re.S)
    return plain_text(x)


# ====================================================================
# 글 폭 어림
# ====================================================================
WIDE = set("①②③④⑤⑥⑦⑧⑨⑩㉠㉡㉢㉣㉤㉥㉦㉧㉮㉯㉰ⓐⓑⓒⓓⓔ○●□■△▲▽▼◇◆☆★※→←↑↓⇒⇔〈〉《》「」『』【】…—")
NARROW = set("ilI.,:;'|!()[]{}`")


def char_w(ch: str, em: float) -> float:
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7A3 or 0x3131 <= o <= 0x318E or 0x4E00 <= o <= 0x9FFF:
        return em * 0.945
    if ch in WIDE or 0xFF00 <= o <= 0xFFEF or 0x2160 <= o <= 0x217F:
        return em * 0.91
    # 글꼴마다 다르므로 넉넉히(조금 넓게) 어림한다: 좁게 어림하면 한 줄에 넣은 선지·칸 글이 넘친다
    if ch == " ":
        return em * 0.42
    if ch in NARROW:
        return em * 0.34
    if ch in "°′″−×÷±≈≤≥·ㆍ–~":
        return em * 0.62
    if ch.isupper() or ch in "mwMW%@&":
        return em * 0.68
    return em * 0.56


class Metric:
    """글자 모양 하나의 폭 어림 도구"""

    def __init__(self, header: Header, charpr: int):
        i = header.charpr_info(charpr)
        self.size = i["height"]
        self.em = i["height"] * i["ratio"] / 100
        self.extra = i["height"] * i["spacing"] / 100

    def plain(self, t: str) -> float:
        return sum(char_w(c, self.em) + self.extra for c in t)


# ====================================================================
# 글 안 표시: <i><b><u><sub><sup>, $…$
# ====================================================================
TOKEN = re.compile(r"(\\\$|\$[^$]+\$|</?(?:i|b|u|sub|sup)>)")


def parse_inline(text: str):
    """→ [("t", 글, {"i","b",...}) | ("eq", tex, flags)]"""
    out, flags = [], set()
    for tok in TOKEN.split(text or ""):
        if not tok:
            continue
        if tok == "\\$":
            out.append(("t", "$", frozenset(flags)))
        elif tok.startswith("$") and tok.endswith("$") and len(tok) > 2:
            out.append(("eq", tok[1:-1], frozenset(flags)))
        elif re.fullmatch(r"</?(?:i|b|u|sub|sup)>", tok):
            name = tok.strip("</>")
            if tok.startswith("</"):
                flags.discard(name)
            else:
                flags.add(name)
        else:
            out.append(("t", tok, frozenset(flags)))
    return out


def strip_inline(text: str) -> str:
    """표시를 지운 맨 글(폭 어림·찾기용). 수식은 대충 글로"""
    t = re.sub(r"</?(?:i|b|u|sub|sup)>", "", text or "")
    return re.sub(r"\$([^$]+)\$", lambda m: re.sub(r"\\[a-zA-Z]+|[{}_^]", "", m.group(1)), t)


# ====================================================================
# 수식: LaTeX 꼴 → 한글 수식 스크립트
# ====================================================================
GREEK = ["alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta", "vartheta", "iota", "kappa",
         "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi", "varphi", "chi", "psi", "omega"]
SYM = {
    "times": " times ", "div": " div ", "cdot": " cdot ", "pm": " +- ", "mp": " -+ ",
    "leq": " <= ", "le": " <= ", "geq": " >= ", "ge": " >= ", "neq": " != ", "ne": " != ",
    "approx": " ≈ ", "sim": " ∼ ", "simeq": " ≃ ", "propto": " ∝ ", "infty": " inf ", "equiv": " ≡ ",
    "to": " -> ", "rightarrow": " -> ", "leftarrow": " <- ", "Rightarrow": " => ", "Leftarrow": " <= ",
    "leftrightarrow": " <-> ", "rightleftharpoons": " ⇌ ", "uparrow": " ↑ ", "downarrow": " ↓ ",
    "circ": " circ ", "degree": "°", "cdots": " cdots ", "ldots": " ... ", "dots": " ... ",
    "sum": " sum ", "int": " int ", "partial": " partial ", "nabla": " nabla ", "angle": " angle ",
    "triangle": " triangle ", "perp": " ⊥ ", "parallel": " ∥ ", "therefore": " therefore ", "because": " because ",
    "quad": "~~", "qquad": "~~~~", "%": "%", ",": "`", ";": "~", ":": "`", "!": "", " ": "~",
    "left": " left ", "right": " right ", "log": " log ", "ln": " ln ", "sin": " sin ", "cos": " cos ", "tan": " tan ",
    "lim": " lim ", "max": " max ", "min": " min ", "exp": " exp ",
}
# 대문자 그리스 문자는 글자 그대로 넣는다(한글 수식은 유니코드 글자를 그대로 그린다)
UPPER_GREEK = {"Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ",
               "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω"}
ACCENT = {"vec": "vec", "overline": "bar", "bar": "bar", "hat": "hat", "dot": "dot", "ddot": "ddot", "tilde": "tilde",
          "underline": "under"}
NUM = re.compile(r"[\d.]+(?:\{,\}\d+)*[만억조]?")


def _brace(s: str, i: int):
    """s[i] 가 '{' 이면 짝 괄호 안 글과 다음 위치, 아니면 글자 하나"""
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] != "{":
        if s[i] == "\\":
            m = re.match(r"\\[a-zA-Z]+", s[i:])
            if m:
                return m.group(0), i + len(m.group(0))
        return s[i], i + 1
    d = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0:
                return s[i + 1:j], j + 1
    return s[i + 1:], len(s)


UNKNOWN_TEX: set = set()


def tex_to_hwp(t: str) -> str:
    out, i = [], 0
    while i < len(t):
        c = t[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+|.)", t[i:])
            name = m.group(1)
            i += len(m.group(0))
            if name in ("frac", "dfrac", "tfrac"):
                a, i = _brace(t, i)
                b, i = _brace(t, i)
                out.append(" {%s} over {%s} " % (tex_to_hwp(a), tex_to_hwp(b)))
            elif name == "sqrt":
                if i < len(t) and t[i] == "[":
                    j = t.find("]", i)
                    n = t[i + 1:j]
                    a, i = _brace(t, j + 1)
                    out.append(" root {%s} of {%s} " % (tex_to_hwp(n), tex_to_hwp(a)))
                else:
                    a, i = _brace(t, i)
                    out.append(" sqrt {%s} " % tex_to_hwp(a))
            elif name in ("mathrm", "text", "textrm", "mathit", "textit", "operatorname", "mathbf", "textbf"):
                a, i = _brace(t, i)
                if name in ("mathit", "textit"):
                    out.append(" {%s} " % tex_to_hwp(a))
                else:
                    out.append('"%s"' % a.replace('"', "'"))
            elif name in ACCENT:
                a, i = _brace(t, i)
                out.append(" %s {%s} " % (ACCENT[name], tex_to_hwp(a)))
            elif name in GREEK:
                out.append(" %s " % name.replace("var", ""))
            elif name.lower() in GREEK and name[0].isupper():
                out.append(" %s " % UPPER_GREEK.get(name, name.upper()))
            elif name in SYM:
                out.append(SYM[name])
            elif name in ("{", "}"):
                out.append(" \"%s\" " % name)
            elif name in ("displaystyle", "limits", "nolimits"):
                pass
            else:
                UNKNOWN_TEX.add(name)
                out.append(" %s " % name)
        elif c.isdigit() and NUM.match(t, i):
            tok = NUM.match(t, i).group(0)
            i += len(tok)
            tok = tok.replace("{,}", ",")
            out.append('"%s"' % tok if ("," in tok or not tok[-1].isdigit()) else tok)
        elif t.startswith("{,}", i):
            out.append(",")
            i += 3
        elif c in "_^":
            a, j = _brace(t, i + 1)
            out.append("%s{%s}" % (c, tex_to_hwp(a)))
            i = j
        elif c == "{":
            a, i = _brace(t, i)
            out.append("{%s}" % tex_to_hwp(a))
        elif c == ":":
            out.append("~:~")
            i += 1
        elif c == " ":
            prev = out[-1][-1:] if out else ""
            nxt = t[i + 1:i + 2]
            if prev and nxt and (prev.isalnum() or prev in ')"') and (nxt.isalnum() or nxt in "("):
                out.append("~")
            i += 1
        elif c == "−":
            out.append("-")
            i += 1
        else:
            out.append(c)
            i += 1
    return re.sub(r" +", " ", "".join(out)).strip()


def eq_size(t: str, em: float = 1100):
    """수식 (폭, 높이, 기준선%) 어림. em = 둘레 글자 크기"""
    k = em / 1100
    if re.search(r"\\(d|t)?frac", t):
        w, i, rest = 0, 0, ""
        while i < len(t):
            m = re.match(r"\\(d|t)?frac", t[i:])
            if m:
                a, i = _brace(t, i + len(m.group(0)))
                b, i = _brace(t, i)
                w += max(eq_size(a, em)[0], eq_size(b, em)[0]) + 300 * k
            else:
                rest += t[i]
                i += 1
        return int(w + (eq_size(rest, em)[0] if rest.strip() else 0)), int(2750 * k), 62
    p = re.sub(r"\\(?:mathrm|text|textrm)\{([^}]*)\}", r" \1", t)
    p = re.sub(r"\\([a-zA-Z]+)", lambda m: "x" if m.group(1) in GREEK or m.group(1).lower() in GREEK else
               ("×" if m.group(1) in ("times", "cdot") else ("" if m.group(1) in ("left", "right", "displaystyle") else "ab")), p)
    sub = len(re.findall(r"[_^]\{([^}]*)\}", p)) + len(re.findall(r"[_^][^{]", p))
    p = re.sub(r"[_^]\{([^}]*)\}", r"\1", p).replace("{", "").replace("}", "").replace("_", "").replace("^", "")
    w = sum(900 * k if c in "=×:≈+−-<>" else char_w(c, em) for c in p if c.strip()) - sub * 180 * k + 112
    tall = "\\sqrt" in t or "^{" in t or "\\vec" in t or "\\overline" in t
    h = int((1300 if tall else 1100) * k)
    return int(max(w * 1.1, 400 * k)), h, (80 if tall else 85)   # 수식 글꼴은 넓게 그려지는 편이라 10% 넉넉히


def text_width(text: str, metric: Metric) -> float:
    w = 0.0
    for kind, s, flags in parse_inline(text):
        if kind == "eq":
            w += eq_size(s, metric.size)[0]
        else:
            f = 0.62 if ("sub" in flags or "sup" in flags) else 1.0
            w += metric.plain(s) * f
    return w


def tall_extra(text: str, size: float) -> float:
    """분수 같은 높은 수식이 든 줄이 더 높아지는 만큼"""
    return sum(max(0, eq_size(s, size)[1] - size) for kind, s, _ in parse_inline(text) if kind == "eq" and eq_size(s, size)[1] > size * 1.2)


# ====================================================================
# XML 조각
# ====================================================================
class Ids:
    def __init__(self, para=3000000, obj=1700000000):
        self.para = para
        self.obj = obj

    def p(self):
        self.para += 1
        return self.para

    def o(self):
        self.obj += 1
        return self.obj


def equation_xml(ids: Ids, tex: str, size: float) -> str:
    w, h, bl = eq_size(tex, size)
    return ('<hp:equation id="%d" zOrder="0" numberingType="EQUATION" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
            'dropcapstyle="None" version="Equation Version 60" baseLine="%d" textColor="#000000" baseUnit="%d" lineMode="CHAR" font="HYhwpEQ">'
            '<hp:script>%s</hp:script><hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
            'horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
            '<hp:outMargin left="56" right="56" top="0" bottom="0"/><hp:shapeComment>수식입니다.</hp:shapeComment></hp:equation>') % (
        ids.o(), bl, int(size), esc(tex_to_hwp(tex)), w, h)


def para_xml(ids: Ids, body: str, pp: int, style: int = 0, page_break=False, col_break=False) -> str:
    return '<hp:p id="%d" paraPrIDRef="%d" styleIDRef="%d" pageBreak="%d" columnBreak="%d" merged="0">%s</hp:p>' % (
        ids.p(), pp, style, 1 if page_break else 0, 1 if col_break else 0, body)


def run_xml(text: str, cp: int) -> str:
    return '<hp:run charPrIDRef="%d"><hp:t>%s</hp:t></hp:run>' % (cp, esc(text))


def obj_run(obj: str, cp: int) -> str:
    return '<hp:run charPrIDRef="%d">%s</hp:run>' % (cp, obj)


def cell_xml(col, row, w, h, paras, bf, colspan=1, rowspan=1, valign="CENTER", margin=(141, 141, 141, 141)) -> str:
    return ('<hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" dirty="0" borderFillIDRef="%d">'
            '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="%s" linkListIDRef="0" linkListNextIDRef="0" '
            'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">%s</hp:subList>'
            '<hp:cellAddr colAddr="%d" rowAddr="%d"/><hp:cellSpan colSpan="%d" rowSpan="%d"/><hp:cellSz width="%d" height="%d"/>'
            '<hp:cellMargin left="%d" right="%d" top="%d" bottom="%d"/></hp:tc>') % (
        bf, valign, "".join(paras), col, row, colspan, rowspan, int(w), int(h), *[int(v) for v in margin])


def table_xml(ids: Ids, rows: int, cols: int, w, h, trs, bf, inmargin=(141, 141, 141, 141), outmargin=(0, 0, 0, 0),
              split="CELL", repeat=0) -> str:
    return ('<hp:tbl id="%d" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
            'dropcapstyle="None" pageBreak="%s" repeatHeader="%d" rowCnt="%d" colCnt="%d" cellSpacing="0" borderFillIDRef="%d" noAdjust="0">'
            '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
            '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
            'horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
            '<hp:outMargin left="%d" right="%d" top="%d" bottom="%d"/><hp:inMargin left="%d" right="%d" top="%d" bottom="%d"/>%s</hp:tbl>') % (
        ids.o(), split, repeat, rows, cols, bf, int(w), int(h), *[int(v) for v in outmargin], *[int(v) for v in inmargin],
        "".join("<hp:tr>%s</hp:tr>" % "".join(r) for r in trs))


def image_size(raw: bytes):
    """(가로 px, 세로 px). Pillow 가 있으면 쓰고, 없으면 PNG·JPEG 머리에서 읽는다."""
    try:
        import io
        from PIL import Image  # noqa
        return Image.open(io.BytesIO(raw)).size
    except Exception:
        pass
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", raw[16:24])
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw):
            if raw[i] != 0xFF:
                i += 1
                continue
            mk = raw[i + 1]
            if mk in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", raw[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", raw[i + 2:i + 4])[0]
            i += 2 + seg
    raise ValueError("그림 크기를 읽지 못했습니다(PNG·JPEG만 됩니다. 다른 형식은 Pillow 를 설치하세요)")


def picture_xml(ids: Ids, bin_id: str, px_w: int, px_h: int, W: int) -> tuple[str, int]:
    H = round(W * px_h / px_w)
    a = ids.o()
    b = ids.o()
    xml = ('<hp:pic id="%d" zOrder="0" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
           'dropcapstyle="None" href="" groupLevel="0" instid="%d" reverse="0">'
           '<hp:offset x="0" y="0"/><hp:orgSz width="%d" height="%d"/><hp:curSz width="%d" height="%d"/><hp:flip horizontal="0" vertical="0"/>'
           '<hp:rotationInfo angle="0" centerX="%d" centerY="%d" rotateimage="1"/><hp:renderingInfo>'
           '<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/><hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
           '<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
           '<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="%d" y="0"/><hc:pt2 x="%d" y="%d"/><hc:pt3 x="0" y="%d"/></hp:imgRect>'
           '<hp:imgClip left="0" right="%d" top="0" bottom="%d"/><hp:inMargin left="0" right="0" top="0" bottom="0"/>'
           '<hp:imgDim dimwidth="%d" dimheight="%d"/>'
           '<hc:img binaryItemIDRef="%s" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/><hp:effects></hp:effects>'
           '<hp:sz width="%d" widthRelTo="ABSOLUTE" height="%d" heightRelTo="ABSOLUTE" protect="0"/>'
           '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" '
           'horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
           '<hp:outMargin left="0" right="0" top="0" bottom="0"/></hp:pic>') % (
        a, b, W, H, W, H, W // 2, H // 2, W, W, H, H, px_w * 75, px_h * 75, px_w * 75, px_h * 75, bin_id, W, H)
    return xml, H


def check_xml(s: str, what: str):
    import xml.dom.minidom
    try:
        xml.dom.minidom.parseString(s.encode("utf-8"))
    except Exception as e:  # 만든 XML 이 깨졌으면 한글이 못 연다
        raise SystemExit("[오류] %s XML 이 올바르지 않습니다: %s" % (what, e))


def load_json(path):
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt_pts(p) -> str:
    try:
        f = float(p)
    except (TypeError, ValueError):
        return str(p)
    return str(int(f)) if f == int(f) else ("%g" % f)
