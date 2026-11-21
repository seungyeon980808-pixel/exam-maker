# exam.json → 시안(코멘트판) HTML 한 장.
#   왼쪽: 시험지 모양 문항 / 오른쪽 위: 정답·해설·출처·검토 / 그 아래: 부분별 코멘트 칸(적으면 자동 저장).
#   --prev 옛판.json 을 주면 바뀐 문항은 「이전 판 | 바뀐 판」을 나란히 보여 준다(적용 전 비교 시안).
# 실행: python make_board.py <exam.json> [--prev 판/exam_v0.1.json] [--out 시안폴더]
#   → <시안폴더>/index.html (+ 그림 복사). 코멘트 서버: node comment_server.cjs <시안폴더>
import argparse, html, json, re, shutil, sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = "①②③④⑤⑥⑦"
GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "theta": "θ", "lambda": "λ", "mu": "μ", "pi": "π",
         "rho": "ρ", "sigma": "σ", "omega": "ω", "Omega": "Ω", "times": "×", "div": "÷", "pm": "±", "cdot": "·", "le": "≤", "ge": "≥",
         "neq": "≠", "approx": "≈", "rightarrow": "→", "to": "→", "leftarrow": "←", "infty": "∞", "circ": "°", "prime": "′"}


def brace(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0:
                return s[i + 1:j], j + 1
    return s[i + 1:], len(s)


def tex(s):
    """$…$ 안의 LaTeX 꼴을 간단한 HTML로(시안 보기용; 한글 시험지는 hwpx 빌더가 한글 수식으로 바꾼다)."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            name = m.group(1) if m else ""
            i += len(name) + 1
            if name == "frac":
                while i < len(s) and s[i] == " ":
                    i += 1
                a, i = brace(s, i)
                b, i = brace(s, i)
                out.append(f'<span class="frac"><span>{tex(a)}</span><span>{tex(b)}</span></span>')
            elif name == "sqrt":
                a, i = brace(s, i)
                out.append(f"√<span style='border-top:1px solid'>{tex(a)}</span>")
            elif name in ("mathrm", "text", "rm"):
                a, i = brace(s, i)
                out.append(f'<span style="font-style:normal">{html.escape(a)}</span>')
            elif name in GREEK:
                out.append(GREEK[name])
            elif name in (",", ";", "quad"):
                out.append(" ")
            else:
                out.append(name)
        elif c in "^_":
            i += 1
            if i < len(s) and s[i] == "{":
                a, i = brace(s, i)
            else:
                a, i = s[i:i + 1], i + 1
            tag = "sup" if c == "^" else "sub"
            out.append(f"<{tag}>{tex(a)}</{tag}>")
        elif c.isalpha() and c.isascii():
            out.append(f"<i>{c}</i>")
            i += 1
        elif c in "{}":
            i += 1
        else:
            out.append(html.escape(c))
            i += 1
    return "".join(out)


def rich(t):
    """글 안의 $…$ 수식만 바꾸고, <i><b><u><sub><sup><br>는 그대로 둔다."""
    if t is None:
        return ""
    return re.sub(r"\$(.+?)\$", lambda m: f'<span class="math">{tex(m.group(1))}</span>', str(t))


def img(src, width, base):
    return f'<img src="{html.escape(src)}" style="width:{int(float(width or 0.8) * 100)}%">'


def table_html(b):
    head = "".join(f"<th>{rich(h)}</th>" for h in b.get("head", []))
    rows = "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in r) + "</tr>" for r in b.get("rows", []))
    t = f'<table class="data">{"<tr>" + head + "</tr>" if head else ""}{rows}</table>'
    return t


def block_html(b, base):
    k = b.get("type")
    cap = f'<div class="cap">{rich(b["caption"])}</div>' if b.get("caption") else ""
    if k == "text":
        return f"<p>{rich(b.get('text'))}</p>"
    if k == "fig":
        return f'<div class="solo">{img(b.get("src", ""), b.get("width"), base)}</div>{cap}'
    if k == "table":
        return f'<div class="solo">{table_html(b)}</div>{cap}'
    if k == "box":
        return '<div class="box">' + "".join(block_html(x, base) for x in b.get("blocks", [])) + "</div>"
    if k == "talk":
        return '<div class="box talk">' + "".join(f"<p>{rich(n)} : {rich(t)}</p>" for n, t in b.get("lines", [])) + "</div>"
    if k == "eq":
        return f'<div class="eq">{tex(b.get("tex", ""))}</div>'
    if k == "pair":
        return '<div class="pair">' + "".join(f"<div>{block_html(x, base)}</div>" for x in b.get("blocks", [])) + "</div>"
    return f"<p>[알 수 없는 블록 {html.escape(str(k))}]</p>"


def plain_len(t):
    return len(re.sub(r"<[^>]+>|\$", "", str(t)))


def choices_html(it):
    ch = it.get("choices") or []
    if not ch:
        return '<div class="essay"></div>' if it.get("kind") == "서술형" else ""
    longest = max(plain_len(c) for c in ch)
    if longest > 14:
        return '<div class="choices v">' + "".join(f"<p>{NUM[i]} {rich(c)}</p>" for i, c in enumerate(ch)) + "</div>"
    if longest > 7:
        return '<div class="choices c3">' + "".join(f"<span>{NUM[i]} {rich(c)}</span>" for i, c in enumerate(ch)) + "</div>"
    return '<div class="choices">' + "".join(f"<span>{NUM[i]} {rich(c)}</span>" for i, c in enumerate(ch)) + "</div>"


def pts_txt(p):
    return f"{p:g}" if isinstance(p, (int, float)) else str(p)


def item_html(it, base):
    pt = f' <span class="pt">[{pts_txt(it.get("pts", ""))}점]</span>'
    ask = it.get("ask")
    head = "서술형 " if it.get("kind") == "서술형" else ""
    h = [f'<p class="q"><b>{head}{it.get("no")}.</b> {rich(it.get("stem", ""))}{"" if ask else pt}</p>']
    h += [block_html(b, base) for b in it.get("blocks", [])]
    if ask:
        h.append(f"<p>{rich(ask)}{pt}</p>")
    if it.get("bogi"):
        h.append('<div class="bogi">' + "".join(f"<p>{'ㄱㄴㄷㄹㅁㅂ'[i]}. {rich(b)}</p>" for i, b in enumerate(it["bogi"])) + "</div>")
    h.append(choices_html(it))
    return "\n".join(h)


def sol_html(it, rv):
    s = it.get("sol") or {}
    p = []
    meta = f'{it.get("no")}번 · {it.get("kind", "선택형")} · {html.escape(str(it.get("unit", "")))} · {html.escape(str(it.get("standard", "")))} · 난이도 {it.get("level", "")} · {pts_txt(it.get("pts", ""))}점'
    p.append(f"<h4>{meta}</h4><p><b>정답</b> {rich(it.get('ans', ''))}</p>")
    for key, lab in (("intent", "출제 의도"), ("basis", "출제 근거"), ("concept", "핵심 개념")):
        if s.get(key):
            p.append(f"<h4>{lab}</h4><p>{rich(s[key])}</p>")
    if s.get("bogi"):
        p.append("<h4>〈보기〉 해설</h4>" + "".join(f"<p>{rich(x)}</p>" for x in s["bogi"]))
    if s.get("choices"):
        p.append("<h4>선지 해설</h4>" + "".join(f"<p>{rich(x)}</p>" for x in s["choices"]))
    if it.get("rubric"):
        p.append("<h4>채점 기준</h4>" + "".join(f"<p>{r.get('점수', '')}점: {rich(r.get('기준', ''))}</p>" for r in it["rubric"]))
    p.append(f"<h4>내용 출처</h4><p>{rich(it.get('src', '')) or '<span class=muted>없음</span>'}</p>")
    rvh = "".join(f"<p><b>{html.escape(str(k))}</b> {html.escape(str(v))}</p>" for k, v in (rv or {}).items())
    p.append("<h4>검토 (GPT · Claude 격리 풀이)</h4>" + (rvh or '<p class="muted">검토 전</p>'))
    return '<div class="sol">' + "".join(p) + "</div>"


def comment_html(it):
    keys = ["전체", "발문"] + (["자료"] if it.get("blocks") else []) + (["보기"] if it.get("bogi") else []) + (["선지"] if it.get("choices") else []) + ["해설", "그림"]
    return '<div class="cms">' + "".join(
        f'<div class="lab{" all" if k == "전체" else ""}">{k}</div><textarea data-q="{it.get("no")}" data-part="{k}" placeholder="{k} 코멘트"></textarea>' for k in keys) + "</div>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam")
    ap.add_argument("--prev", help="비교할 이전 판 exam.json")
    ap.add_argument("--review", help="격리 풀이 결과 review.json (기본: exam.json 옆)")
    ap.add_argument("--out", help="시안 폴더 (기본: exam.json 옆 시안/)")
    a = ap.parse_args()
    ep = Path(a.exam).resolve()
    exam = json.loads(ep.read_text(encoding="utf-8"))
    meta, items = exam.get("meta", {}), exam.get("items", [])
    out = Path(a.out).resolve() if a.out else ep.parent / "시안"
    out.mkdir(parents=True, exist_ok=True)
    rp = Path(a.review) if a.review else ep.parent / "review.json"
    review = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    prev = {}
    if a.prev:
        pe = json.loads(Path(a.prev).read_text(encoding="utf-8"))
        prev = {str(x.get("no")): x for x in pe.get("items", [])}

    # 그림을 시안 폴더로 복사(상대 경로 유지)
    def copy_figs(blocks, root):
        for b in blocks:
            if b.get("type") == "fig" and b.get("src"):
                s = (root / b["src"]).resolve()
                d = out / b["src"]
                if s.exists() and s != d:
                    d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(s, d)
            copy_figs(b.get("blocks", []), root)
    for it in items:
        copy_figs(it.get("blocks", []), ep.parent)
    for it in prev.values():
        copy_figs(it.get("blocks", []), Path(a.prev).resolve().parent)

    secs, changed = [], []
    for it in items:
        no = str(it.get("no"))
        old = prev.get(no)
        is_changed = bool(a.prev) and (old is None or json.dumps(old, sort_keys=True, ensure_ascii=False) != json.dumps(it, sort_keys=True, ensure_ascii=False))
        if is_changed:
            changed.append(no)
        papers = ""
        if is_changed and old is not None:
            papers += f'<div class="paper old"><span class="tag old">이전 판</span>{item_html(old, ep.parent)}</div>'
            papers += f'<div class="paper"><span class="tag new">바뀐 판</span>{item_html(it, ep.parent)}</div>'
        else:
            tag = '<span class="tag new">새 문항</span>' if is_changed else ""
            papers += f'<div class="paper">{tag}{item_html(it, ep.parent)}</div>'
        cls = "qwrap cmp" if (is_changed and old is not None) else "qwrap"
        secs.append(f'<section class="{cls}" id="q{no}">{papers}<div class="right">{sol_html(it, review.get(no))}{comment_html(it)}</div></section>')

    total = sum(float(it.get("pts", 0) or 0) for it in items)
    seq = " ".join(str(it.get("ans", "")) for it in items if it.get("kind", "선택형") == "선택형")
    title = f'{meta.get("title", "시험")} {meta.get("version", "")}'
    info = f'{len(items)}문항 · {total:g}점 · 선택형 정답 {html.escape(seq)}'
    if a.prev:
        info += f' · 이전 판과 다른 문항: {", ".join(changed) or "없음"}'
    css = (HERE / "style.css").read_text(encoding="utf-8")
    js = (HERE / "board.js").read_text(encoding="utf-8")
    key = re.sub(r"\W+", "-", f'{meta.get("title", "exam")}-{meta.get("version", "")}')
    page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} 코멘트판</title><style>{css}</style></head><body data-key="{html.escape(key)}" data-version="{html.escape(str(meta.get("version", "")))}">
<div class="top"><b>{html.escape(title)} · 코멘트판</b><span>{info}</span><span id="st">불러오는 중…</span>
<button id="copy" type="button">코멘트 전체 복사(Claude에게 붙여 넣기)</button></div>
{"".join(secs)}
<script>{js}</script></body></html>'''
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"시안: {out / 'index.html'}  ({info})")


if __name__ == "__main__":
    sys.exit(main())
