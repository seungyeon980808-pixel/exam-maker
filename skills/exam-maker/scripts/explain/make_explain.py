# -*- coding: utf-8 -*-
"""exam.json → 정답과 해설 · 문항 검토 용지 · (check.json이 있으면) 교과서·수준·교육과정 점검표 PDF.

쓰는 법:
    python make_explain.py <exam.json> <out폴더> [--check check.json] [--paper jis-b4|a4]

Python 표준 라이브러리와 typst 실행 파일만 쓴다(윈도우 · 맥 모두).
글꼴은 이 폴더의 fonts/를 먼저 쓰고, 없는 글자는 컴퓨터에 있는 글꼴(함초롬 · 맑은 고딕 · 바탕 …)로 넘어간다.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
FONTS = HERE / "fonts"

# 앞에 있을수록 먼저 쓴다. 이 컴퓨터에 있는 것만 골라 typst에 넘긴다.
SERIF_CANDIDATES = ["Noto Serif KR Static", "HCR Batang", "함초롬바탕", "Batang", "바탕", "AppleMyungjo"]
SANS_CANDIDATES = ["Pretendard", "HCR Dotum", "함초롬돋움", "Malgun Gothic", "맑은 고딕", "Apple SD Gothic Neo"]

WARN = []


def warn(msg):
    WARN.append(msg)


# ───────────────────────────── 글 → Typst 마크업

def esc_text(t):
    """Typst 마크업에서 글자 그대로 나오게 특수 문자를 이스케이프한다."""
    t = t.replace("\\", "\\\\")
    for ch in "#$*_`<>@[]~/-+='\"":
        t = t.replace(ch, "\\" + ch)
    return t


def str_lit(t):
    """Typst 문자열 값."""
    return '"' + t.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε", "zeta": "ζ",
    "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "ϕ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ",
    "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
}
SYMBOLS = {
    "times": "×", "div": "÷", "cdot": "⋅", "pm": "±", "mp": "∓", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "ne": "≠", "neq": "≠", "approx": "≈", "propto": "∝", "to": "→", "rightarrow": "→", "leftarrow": "←",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "leftrightarrow": "↔", "rightleftharpoons": "⇌", "infty": "∞",
    "circ": "∘", "degree": "°", "cdots": "⋯", "ldots": "…", "dots": "…", "sim": "∼", "simeq": "≃",
    "equiv": "≡", "prime": "′", "partial": "∂", "nabla": "∇", "sum": "∑", "int": "∫", "angle": "∠",
    "triangle": "△", "perp": "⊥", "parallel": "∥", "ll": "≪", "gg": "≫", "uparrow": "↑", "downarrow": "↓",
    "therefore": "∴", "because": "∵", "in": "∈", "cdotp": "⋅", "ell": "ℓ", "hbar": "ℏ",
    "lbrace": "\\{", "rbrace": "\\}", "langle": "⟨", "rangle": "⟩",
}
SPACES = {",": "thin", ";": "med", ":": "med", "!": "", " ": "space", "quad": "quad", "qquad": "wide"}
FUNCS = {"sin", "cos", "tan", "log", "ln", "exp", "lim", "max", "min"}
TEXTISH = {"text", "mathrm", "textrm", "rm", "operatorname", "textnormal", "mbox"}
ONE_ARG = {"mathbf": "bold", "boldsymbol": "bold", "bm": "bold", "mathit": "italic", "vec": "arrow",
           "overline": "overline", "bar": "macron", "hat": "hat", "dot": "dot", "ddot": "dot.double",
           "underline": "underline", "tilde": "tilde", "overrightarrow": "arrow"}


class TexConv:
    """간단한 LaTeX 수식 → Typst 수식. 시험 문항에 나오는 정도(분수 · 첨자 · 근호 · 그리스 문자 · 기호 · \\text)만."""

    def __init__(self, s):
        self.s = s
        self.i = 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def read_cmd(self):
        # self.s[self.i] == "\\"
        self.i += 1
        if self.i >= len(self.s):
            return ""
        c = self.s[self.i]
        if c.isalpha():
            j = self.i
            while j < len(self.s) and self.s[j].isalpha():
                j += 1
            name = self.s[self.i:j]
            self.i = j
            return name
        self.i += 1
        return c

    def raw_group(self):
        """{ … } 안 글자를 그대로(\\text 용)."""
        self.skip_space()
        if self.peek() != "{":
            c = self.peek()
            self.i += 1
            return c
        depth, j = 0, self.i
        while j < len(self.s):
            if self.s[j] == "{":
                depth += 1
            elif self.s[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        inner = self.s[self.i + 1:j]
        self.i = j + 1
        return inner

    def skip_space(self):
        while self.peek() == " ":
            self.i += 1

    def arg(self):
        self.skip_space()
        c = self.peek()
        if c == "{":
            self.i += 1
            return self.seq("}")
        if c == "\\":
            return self.command(self.read_cmd())
        if c == "":
            return ""
        self.i += 1
        return self.char(c)

    def char(self, c):
        if c.isascii() and c.isalpha():
            return c
        if c.isdigit() or c == ".":
            return c
        if c in "/&#\"@,;$_":
            return "\\" + c
        if c == "~":
            return " "
        if c == "'":
            return "'"
        if c in "+-=<>()[]|!*:?":
            return c
        if c == " ":
            return " "
        if re.match(r"[\uAC00-\uD7A3\u3131-\u318E]", c):
            return str_lit(c)
        return c

    def command(self, name):
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            a = self.arg()
            b = self.arg()
            return "frac(%s, %s)" % (a or '""', b or '""')
        if name == "sqrt":
            self.skip_space()
            if self.peek() == "[":
                j = self.s.find("]", self.i)
                n = TexConv(self.s[self.i + 1:j]).seq(None)
                self.i = j + 1
                return "root(%s, %s)" % (n, self.arg())
            return "sqrt(%s)" % self.arg()
        if name in TEXTISH:
            return str_lit(self.raw_group())
        if name in ONE_ARG:
            return "%s(%s)" % (ONE_ARG[name], self.arg())
        if name in ("left", "right", "big", "Big", "bigl", "bigr", "Bigl", "Bigr", "displaystyle", "limits"):
            if name in ("left", "right"):
                self.skip_space()
                c = self.peek()
                if c == "\\":
                    return self.command(self.read_cmd())
                self.i += 1
                return "" if c == "." else self.char(c)
            return ""
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        if name in SPACES:
            return " " + SPACES[name] + " " if SPACES[name] else ""
        if name in FUNCS:
            return " " + name + " "
        if name == "\\":
            return " \\ "
        if name in "{}%#$_&":
            return "\\" + name
        if name == "circ":
            return "∘"
        warn("모르는 수식 명령 \\%s — 글자로 넣음" % name)
        return str_lit(name)

    def seq(self, stop):
        out = []
        prev = ""
        while self.i < len(self.s):
            c = self.s[self.i]
            if stop and c == stop:
                self.i += 1
                break
            if c == "\\":
                piece = self.command(self.read_cmd())
            elif c == "{":
                self.i += 1
                piece = self.seq("}")
            elif c in "^_":
                self.i += 1
                a = self.arg()
                if c == "^" and a in ("∘", "\\circ"):
                    piece = "°"
                else:
                    piece = "%s(%s)" % (c, a)
            elif c == " ":
                self.i += 1
                piece = " "
            else:
                self.i += 1
                piece = self.char(c)
            # 글자와 글자(또는 숫자) 사이를 띄워 Typst가 여러 글자 이름으로 읽지 않게
            if piece and prev and piece[0].isascii() and piece[0].isalnum() and prev[-1].isascii() and prev[-1].isalnum():
                if not (prev[-1].isdigit() and (piece[0].isdigit())) and not (prev[-1].isdigit() and piece[0] == "."):
                    out.append(" ")
            out.append(piece)
            if piece:
                prev = piece
        return "".join(out)


def tex2typ(src):
    s = src.strip()
    if not s:
        return '""'
    return TexConv(s).seq(None).strip() or '""'


TAGS = {"i": "#it[", "b": "#bf[", "u": "#underline[", "sub": "#sub[", "sup": "#super["}
TOKEN = re.compile(r"(\$[^$]+\$|</?(?:i|b|u|sub|sup)>|\n)")


def markup(s):
    """exam.json 글(＜i＞＜b＞＜u＞＜sub＞＜sup＞, $…$ 수식, 줄바꿈) → Typst 마크업."""
    if s is None:
        return ""
    s = str(s).replace("<보기>", "〈보기〉").replace("\r\n", "\n")
    out, stack = [], []
    for part in TOKEN.split(s):
        if not part:
            continue
        if part == "\n":
            out.append("#linebreak();")  # 「;」로 식을 끝내야 뒤의 (가)를 함수 호출로 읽지 않는다
        elif part.startswith("$") and part.endswith("$") and len(part) > 2:
            out.append("$" + tex2typ(part[1:-1]) + "$")
        else:
            m = re.fullmatch(r"<(/?)(i|b|u|sub|sup)>", part)
            if m:
                if m.group(1) == "":
                    out.append(TAGS[m.group(2)])
                    stack.append(m.group(2))
                elif stack and stack[-1] == m.group(2):
                    out.append("];")
                    stack.pop()
                else:
                    warn("짝이 맞지 않는 </%s> — 무시함: %s" % (m.group(2), s[:40]))
            else:
                out.append(esc_text(part))
    if stack:
        warn("닫히지 않은 꼬리표 <%s> — 끝에서 닫음: %s" % (">, <".join(stack), s[:40]))
        out.append("];" * len(stack))
    return "".join(out)


def c(s):
    return "[" + markup(s) + "]"


def plain(s):
    s = re.sub(r"</?(?:i|b|u|sub|sup)>", "", str(s or ""))
    return re.sub(r"\$([^$]*)\$", lambda m: re.sub(r"\\[a-zA-Z]+|[{}^_]", "", m.group(1)), s)


def fmt_pts(p):
    try:
        f = float(p)
    except (TypeError, ValueError):
        return str(p or "")
    return str(int(f)) if f == int(f) else ("%g" % f)


# ───────────────────────────── 문항 → Typst 값

class Ctx:
    def __init__(self, exam_dir, build):
        self.exam_dir = exam_dir
        self.build = build
        self.figs = 0

    def copy_fig(self, src, tag):
        if not src:
            return None
        p = Path(src)
        if not p.is_absolute():
            p = self.exam_dir / p
        if not p.is_file():
            warn("그림 파일이 없음: %s" % src)
            return None
        self.figs += 1
        name = "fig/%s_%02d%s" % (tag, self.figs, p.suffix.lower())
        dst = self.build / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)
        return "/" + name


def block_typ(b, ctx, no):
    t = b.get("type", "text")
    if t == "text":
        return "(type: \"text\", body: %s)" % c(b.get("text", ""))
    if t == "fig":
        src = ctx.copy_fig(b.get("src"), "q%02d" % no)
        try:
            w = float(b.get("width", 0.8))
        except (TypeError, ValueError):
            w = 0.8
        w = min(max(w, 0.1), 1.0)
        cap = c(b["caption"]) if b.get("caption") else "none"
        return "(type: \"fig\", src: %s, width: %s, caption: %s, missing: %s)" % (
            str_lit(src) if src else "none", w, cap, str_lit(str(b.get("src", ""))))
    if t == "table":
        head = "(" + "".join(c(x) + ", " for x in b.get("head", [])) + ")"
        rows = "(" + "".join("(" + "".join(c(x) + ", " for x in r) + "), " for r in b.get("rows", [])) + ")"
        cap = c(b["caption"]) if b.get("caption") else "none"
        return "(type: \"table\", head: %s, rows: %s, caption: %s)" % (head, rows, cap)
    if t in ("box", "pair"):
        inner = "(" + "".join(block_typ(x, ctx, no) + ", " for x in b.get("blocks", [])) + ")"
        return "(type: %s, blocks: %s)" % (str_lit(t), inner)
    if t == "talk":
        lines = "(" + "".join("(%s, %s), " % (c(w), c(s)) for w, s in b.get("lines", [])) + ")"
        return "(type: \"talk\", lines: %s)" % lines
    if t == "eq":
        return "(type: \"eq\", body: $ %s $)" % tex2typ(b.get("tex", ""))
    warn("%d번: 모르는 블록 종류 %r — 글로 넣음" % (no, t))
    return "(type: \"text\", body: %s)" % c(b.get("text", ""))


DATA_NAMES = {"fig": "그림", "table": "표", "box": "탐구", "talk": "대화", "eq": "식"}


def data_kinds(blocks):
    out = []
    for b in blocks:
        t = b.get("type")
        if t == "pair":
            out += data_kinds(b.get("blocks", []))
        elif t in DATA_NAMES:
            out.append(DATA_NAMES[t])
            if t == "box":
                out += [k for k in data_kinds(b.get("blocks", [])) if k != "탐구"]
    seen = []
    for k in out:
        if k not in seen:
            seen.append(k)
    return seen


TRUTH = re.compile(r"^\s*([ㄱ-ㅎ])\s*\.?\s*\(\s*(참|거짓|옳음|옳지\s*않음|맞음|틀림|○|×|O|X)\s*[),]")


def choice_line(q, warn_no):
    """〈보기〉 해설의 (참)/(거짓)으로 선지마다 맞는지 적은 한 줄. 정답과 어긋나면 알린다."""
    sol = q.get("sol") or {}
    bogi_sol = sol.get("bogi") or []
    choices = q.get("choices") or []
    if not bogi_sol or not choices or sol.get("choices"):
        return None
    truth = {}
    for p in bogi_sol:
        m = TRUTH.match(plain(p))
        if not m:
            return None
        truth[m.group(1)] = m.group(2) in ("참", "옳음", "맞음", "○", "O")
    want = {k for k, v in truth.items() if v}
    parts, right = [], []
    for i, ch in enumerate(choices):
        got = set(re.findall(r"[ㄱ-ㅎ]", plain(ch)))
        ok = got == want
        if ok:
            right.append(i)
        parts.append("%s %s(%s)" % ("①②③④⑤"[i] if i < 5 else str(i + 1), markup(ch), "○ 정답" if ok else "×"))
    ans = str(q.get("ans", "")).strip()
    if len(right) != 1:
        warn("%d번: 〈보기〉 해설의 참·거짓으로 맞는 선지가 %d개로 나옴 — 확인 필요" % (warn_no, len(right)))
    elif ans and "①②③④⑤"[right[0]] != ans:
        warn("%d번: 〈보기〉 해설로 맞는 선지는 %s인데 정답은 %s — 확인 필요" % (warn_no, "①②③④⑤"[right[0]], ans))
    return "[선지: " + " ".join(parts) + "]"


def verdict_rank(v):
    v = (v or "").strip()
    return 2 if v.startswith("교체") else 1 if v.startswith("고치면") else 0


def item_typ(q, ctx, std_text, chk):
    no = int(q.get("no", 0))
    kind = q.get("kind", "선택형")
    sol = q.get("sol") or {}
    blocks = q.get("blocks") or []
    bogi = q.get("bogi") or []
    choices = q.get("choices") or []
    stem, ask = q.get("stem", ""), q.get("ask", "")
    if not stem and ask:
        stem, ask = ask, ""
    form = "서술형" if kind == "서술형" else ("합답형" if bogi else "선다형")
    data = "+".join(data_kinds(blocks)) or "글"
    ans = str(q.get("ans", "")).strip()

    # 점검
    if kind != "서술형":
        if ans not in "①②③④⑤" or not ans:
            warn("%d번: 정답 %r이 ①~⑤가 아님" % (no, ans))
        if len(choices) != 5:
            warn("%d번: 선지가 %d개" % (no, len(choices)))
    for k in ("intent", "basis", "concept"):
        if not sol.get(k):
            warn("%d번: sol.%s 없음" % (no, k))
    if kind == "서술형" and not q.get("rubric"):
        warn("%d번: 서술형인데 rubric(채점 기준) 없음" % no)

    concept = sol.get("concept", "")
    concepts = concept if isinstance(concept, list) else ([concept] if concept else [])
    rubric = q.get("rubric") or []
    ref = ctx.copy_fig(q.get("ref_fig"), "ref%02d" % no) if q.get("ref_fig") else None

    if chk:
        cl, gp = chk.get("Claude 판정", ""), chk.get("GPT 판정", "")
        final = chk.get("종합") or (cl if verdict_rank(cl) >= verdict_rank(gp) else gp)
        check = "(claude: %s, gpt: %s, final: %s, fix: %s)" % (
            str_lit(cl or "—"), str_lit(gp or "—"), str_lit(final or "—"),
            c(chk["고친 점"]) if chk.get("고친 점") and chk.get("고친 점") != "—" else "none")
    else:
        check = "none"

    # ㄱ·ㄴ·ㄷ 조합 선지는 글자 수와 상관없이 한 줄 5개(확정 규칙)
    combo = bool(choices) and all(re.fullmatch(r"[ㄱ-ㅎ,\s]+", plain(x) or "x") for x in choices)
    lines = [
        "  (",
        "    no: %d, kind: %s, pts: %s, unit: %s, std: %s, level: %s, form: %s, data: %s, ans: %s," % (
            no, str_lit(kind), str_lit(fmt_pts(q.get("pts"))), c(q.get("unit", "")), str_lit(q.get("standard", "")),
            str_lit(q.get("level", "")), str_lit(form), str_lit(data), str_lit(ans if kind != "서술형" else "서술형")),
        "    ans-text: %s, src: %s," % (c(q.get("ans", "")), c(q.get("src", ""))),
        "    intent: %s, basis: %s, concepts: (%s)," % (c(sol.get("intent", "")), c(sol.get("basis", "")), "".join(c(x) + ", " for x in concepts)),
        "    bogi-sol: (%s), choice-sol: (%s)," % ("".join(c(x) + ", " for x in sol.get("bogi") or []), "".join(c(x) + ", " for x in sol.get("choices") or [])),
        "    choice-line: %s," % (choice_line(q, no) or "none"),
        "    rubric: (%s)," % "".join("(%s, %s), " % (str_lit(fmt_pts(r.get("점수", ""))), c(r.get("기준", ""))) for r in rubric),
        "    problem: (lead: %s, ask: %s, blocks: (%s), bogi: (%s), choices: (%s), choice-lens: (%s))," % (
            c(stem), c(ask) if ask else "none", "".join(block_typ(b, ctx, no) + ", " for b in blocks),
            "".join(c(x) + ", " for x in bogi), "".join(c(x) + ", " for x in choices),
            "".join("%d, " % (1 if combo else len(plain(x))) for x in choices)),
        "    ref: %s, ref-label: %s, std-text: %s, check: %s," % (
            str_lit(ref) if ref else "none", c(q.get("ref_label", "")), c(std_text) if std_text else "none", check),
        "  ),",
    ]
    return "\n".join(lines)


# ───────────────────────────── 점검표

def load_check(path, exam):
    ck = json.loads(Path(path).read_text(encoding="utf-8"))
    items = ck.get("items", {})
    if isinstance(items, list):
        items = {str(x.get("no")): x for x in items}
    else:
        items = {str(k): v for k, v in items.items()}
    return ck, items


def check_typ(ck, items, meta, version):
    textbook = meta.get("textbook", "")
    criteria = ck.get("criteria") or (
        "기준: ① 교과서%s만으로 풀 수 있는가 ② 학년 수준을 넘지 않는가 ③ 교육과정(성취기준 · 성취기준 해설 · 적용 시 고려 사항)에 "
        "어긋나지 않는가. GPT와 Claude가 서로 보지 않고 각각 심사했고, 풀이 요소마다 교과서 쪽 · 문장을 대조했다." % (
            "(%s)" % textbook if textbook else ""))
    rules = ck.get("rules") or []
    rows, groups = [], {"그대로": [], "고치면": [], "교체": []}
    for k in sorted(items, key=lambda x: (len(x), x)):
        r = items[k]
        cl, gp = r.get("Claude 판정", ""), r.get("GPT 판정", "")
        final = r.get("종합") or (cl if verdict_rank(cl) >= verdict_rank(gp) else gp)
        groups[["그대로", "고치면", "교체"][verdict_rank(final)]].append(k)
        rows.append("(no: %s, claude: %s, gpt: %s, final: %s, textbook: %s, level: %s, curriculum: %s, fix: %s)" % (
            str_lit(k), str_lit(cl), str_lit(gp), str_lit(final), c(r.get("교과서 대조", "")), c(r.get("수준", "")),
            c(r.get("교육과정", "")), c(r.get("고친 점", "") or "—")))
    summary = ck.get("summary") or "요약 — " + ", ".join(
        "%s %d문항(%s)" % (g, len(v), "·".join(v)) for g, v in groups.items() if v)
    return "#let check = (version: %s, criteria: %s, rules: (%s), rows: (%s), summary: %s)\n" % (
        str_lit(version), c(criteria), "".join("(%s, %s), " % (c(a), c(b)) for a, b in rules),
        "".join(x + ", " for x in rows), c(summary))


# ───────────────────────────── 글꼴 · typst

def find_typst(given):
    for t in [given, os.environ.get("TYPST"), shutil.which("typst"), shutil.which("typst.exe")]:
        if t and (Path(t).is_file() or shutil.which(t)):
            return t
    sys.exit("typst를 찾지 못했다. https://github.com/typst/typst/releases 에서 받아 PATH에 넣거나 --typst 로 경로를 준다.\n"
             "  윈도우: winget install --id Typst.Typst")


def pick_fonts(typst, only_bundled):
    cmd = [typst, "fonts"]
    if FONTS.is_dir():
        cmd += ["--font-path", str(FONTS)]
    if only_bundled:
        cmd.append("--ignore-system-fonts")
    r = subprocess.run(cmd, capture_output=True)
    have = {x.strip().lower() for x in r.stdout.decode("utf-8", "replace").splitlines() if x.strip()}
    serif = [f for f in SERIF_CANDIDATES if f.lower() in have]
    sans = [f for f in SANS_CANDIDATES if f.lower() in have]
    if not serif and sans:
        serif = sans[:]
    if not sans and serif:
        sans = serif[:]
    if not serif:
        warn("한글 글꼴을 하나도 찾지 못함 — 글자가 네모로 나올 수 있다(fonts/ 폴더를 확인)")
    # 한쪽 글꼴에 없는 글자(고딕의 ㉠ ⇌, 명조의 ₂ 등)는 다른 쪽에서 찾도록 서로 뒤에 붙인다
    return serif + [f for f in sans if f not in serif], sans + [f for f in serif if f not in sans]


def compile_typ(typst, build, main, out_pdf, serif, sans, only_bundled):
    cmd = [typst, "compile", "--root", str(build)]
    if FONTS.is_dir():
        cmd += ["--font-path", str(FONTS)]
    if only_bundled:
        cmd.append("--ignore-system-fonts")
    cmd += ["--input", "serif=" + "|".join(serif), "--input", "sans=" + "|".join(sans), str(build / main), str(out_pdf)]
    r = subprocess.run(cmd, capture_output=True)
    msg = r.stderr.decode("utf-8", "replace").strip()
    if r.returncode != 0:
        print(msg, file=sys.stderr)
        sys.exit("만들지 못함: %s (위 오류 참고, --keep-typ 로 .typ를 남겨 볼 수 있다)" % out_pdf.name)
    if msg:
        for line in msg.splitlines():
            if line.startswith("warning:"):
                warn("typst: " + line[len("warning:"):].strip())


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip()


# ───────────────────────────── 실행

def main():
    for stream in (sys.stdout, sys.stderr):   # 윈도우 콘솔(cp949)에서 · → 같은 글자로 멈추지 않게
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="exam.json으로 정답과 해설 · 문항 검토 용지 · 점검표 PDF를 만든다.")
    ap.add_argument("exam", help="exam.json")
    ap.add_argument("out", help="PDF를 둘 폴더")
    ap.add_argument("--check", help="check.json(교과서 · 수준 · 교육과정 점검 결과). 있으면 점검표도 만든다")
    ap.add_argument("--paper", default="jis-b4", help="해설 · 검토 용지 용지: jis-b4(기본, 시험지와 같은 B4) · a4")
    ap.add_argument("--only", choices=["explain", "review", "check"], action="append", help="이것만 만든다(여러 번 가능)")
    ap.add_argument("--typst", help="typst 실행 파일 경로")
    ap.add_argument("--only-bundled-fonts", action="store_true", help="컴퓨터 글꼴 없이 fonts/만으로(점검용)")
    ap.add_argument("--keep-typ", action="store_true", help="만든 .typ를 <out>/_typ/에 남긴다")
    a = ap.parse_args()

    exam_path = Path(a.exam).resolve()
    exam = json.loads(exam_path.read_text(encoding="utf-8"))
    meta, items = exam.get("meta", {}), exam.get("items", [])
    if not items:
        sys.exit("문항이 없다: %s" % exam_path)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    typst = find_typst(a.typst)
    serif, sans = pick_fonts(typst, a.only_bundled_fonts)

    ck, ck_items = (None, {})
    if a.check:
        ck, ck_items = load_check(a.check, exam)
    standards = dict((ck or {}).get("standards") or {})
    version = meta.get("version", "v0.1")
    title = meta.get("title") or "%s %s" % (meta.get("subject", ""), meta.get("exam", ""))
    want = set(a.only or ["explain", "review", "check"])

    term = " ".join(x for x in [
        "%s학년도" % meta["year"] if meta.get("year") else "",
        "%s학기" % meta["semester"] if meta.get("semester") else "",
        "%s학년" % meta["grade"] if meta.get("grade") else ""] if x)
    total = sum(float(q.get("pts") or 0) for q in items)

    with tempfile.TemporaryDirectory(prefix="explain_") as tmp:
        build = Path(tmp)
        shutil.copytree(TEMPLATES, build / "tmpl")
        ctx = Ctx(exam_path.parent, build)
        data = ["// make_explain.py가 exam.json에서 만든 파일(손으로 고치지 않는다)",
                "#import \"/tmpl/common.typ\": it, bf",
                "#let meta = (title: %s, school: %s, term: %s, exam: %s, subject: %s, heading: %s, subtitle: \"\", version: %s, textbook: %s, paper: %s, total: %s)" % (
                    str_lit(title), str_lit(meta.get("school", "")), str_lit(term), str_lit(meta.get("exam", "")),
                    str_lit(meta.get("subject", "")), str_lit(meta.get("subject", "") or title), str_lit(version),
                    str_lit(meta.get("textbook", "")), str_lit(a.paper), str_lit(fmt_pts(total))),
                "#let items = ("]
        for q in items:
            std = q.get("standard", "")
            data.append(item_typ(q, ctx, q.get("standard_text") or standards.get(std), ck_items.get(str(q.get("no")))))
        data.append(")")
        if ck is not None:
            data.append(check_typ(ck, ck_items, meta, ck.get("version") or version))
            missing = [str(q.get("no")) for q in items if str(q.get("no")) not in ck_items]
            if missing:
                warn("check.json에 없는 문항: %s" % ", ".join(missing))
        (build / "data.typ").write_text("\n".join(data) + "\n", encoding="utf-8")

        jobs = []
        if "explain" in want:
            jobs.append(("해설.typ", "explain", "doc(meta, items)", "%s 정답과 해설_(%s).pdf" % (title, version)))
        if "review" in want:
            jobs.append(("검토용지.typ", "review", "doc(meta, items)", "%s 문항 검토 용지_(%s).pdf" % (title, version)))
        if "check" in want and ck is not None:
            jobs.append(("점검표.typ", "check", "doc(meta, check)",
                         "%s 교과서·수준·교육과정 점검표_(%s).pdf" % (title, ck.get("version") or version)))
        made = []
        for main_name, tmpl, call, pdf in jobs:
            (build / main_name).write_text(
                "#import \"/tmpl/%s.typ\": doc\n#import \"/data.typ\": *\n#%s\n" % (tmpl, call), encoding="utf-8")
            target = out / safe_name(pdf)
            compile_typ(typst, build, main_name, target, serif, sans, a.only_bundled_fonts)
            made.append(target)
        if a.keep_typ:
            keep = out / "_typ"
            if keep.exists():
                shutil.rmtree(keep)
            shutil.copytree(build, keep)

    print("글꼴: 명조 %s / 고딕 %s" % (" → ".join(serif) or "없음", " → ".join(sans) or "없음"))
    for p in made:
        print("만듦:", p)
    if WARN:
        print("\n확인할 것 %d개:" % len(WARN))
        for w in dict.fromkeys(WARN):
            print("  -", w)


if __name__ == "__main__":
    main()
