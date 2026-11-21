# exam.json → 격리 풀이 세트(정답·해설·출처를 뺀 문항지). GPT와 Claude가 이 폴더만 보고 따로 푼다.
# 실행: python make_check_set.py <exam.json> <출력폴더> [--textbook 교과서.txt] [--curriculum 교육과정.txt]
#        [--level "고등학교 2학년"] [--range "항상성과 몸의 조절"]
# 출력: Qnn.md(문항지), Qnn_그림n.png, 교과서.txt, 교육과정.txt, 지침_정답.md, 지침_범위.md
import argparse, html, json, re, shutil, sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

HERE = Path(__file__).resolve().parent
NUM = "①②③④⑤⑥⑦"


def plain(t):
    """시안용 표시를 읽기 쉬운 글로: <sub>2</sub> → ₂, $\\frac{a}{b}$ → (a)/(b)."""
    t = str(t or "")
    t = re.sub(r"<sub>(\d+)</sub>", lambda m: m.group(1).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")), t)
    t = re.sub(r"<sup>(\d+)</sup>", lambda m: m.group(1).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")), t)
    t = re.sub(r"<u>(.*?)</u>", r"\1(밑줄)", t)
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", t)
    t = t.replace("\\times", "×").replace("\\Delta", "Δ").replace("\\cdot", "·").replace("\\", "")
    t = t.replace("$", "")
    return html.unescape(t).strip()


def blocks_text(blocks, q, out, ind=""):
    lines = []
    for b in blocks:
        k = b.get("type")
        if k == "text":
            lines.append(ind + plain(b.get("text")))
        elif k == "fig":
            q["n"] += 1
            src = Path(q["root"]) / b.get("src", "")
            name = f"Q{q['no']:02d}_그림{q['n']}{src.suffix or '.png'}"
            if src.exists():
                shutil.copy2(src, out / name)
                q["figs"].append(name)
                lines.append(ind + f"[그림: {name}]")
            else:
                lines.append(ind + f"[그림 없음: {b.get('src')}]")
            if b.get("caption"):
                lines.append(ind + plain(b["caption"]))
        elif k == "table":
            lines.append(ind + "[표]")
            if b.get("head"):
                lines.append(ind + "| " + " | ".join(plain(h) for h in b["head"]) + " |")
            for r in b.get("rows", []):
                lines.append(ind + "| " + " | ".join(plain(c) for c in r) + " |")
            lines.append(ind + "[표 끝]")
            if b.get("caption"):
                lines.append(ind + plain(b["caption"]))
        elif k == "box":
            lines.append(ind + "[상자]")
            lines += blocks_text(b.get("blocks", []), q, out, ind + "  ")
            lines.append(ind + "[상자 끝]")
        elif k == "talk":
            lines += [ind + f"{plain(n)} : {plain(t)}" for n, t in b.get("lines", [])]
        elif k == "eq":
            lines.append(ind + "    " + plain(b.get("tex")))
        elif k == "pair":
            lines.append(ind + "(나란히 놓인 자료)")
            lines += blocks_text(b.get("blocks", []), q, out, ind + "  ")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exam")
    ap.add_argument("out")
    ap.add_argument("--textbook", help="학생들이 배운 교과서 본문 글(txt)")
    ap.add_argument("--curriculum", help="교육과정 원문(성취기준·해설·적용 시 고려 사항) txt")
    ap.add_argument("--level", default="", help='예: "고등학교 2학년"')
    ap.add_argument("--range", default="", help="시험 범위(단원)")
    ap.add_argument("--only", default="", help="1,3,5 처럼 일부만")
    a = ap.parse_args()
    ep = Path(a.exam).resolve()
    exam = json.loads(ep.read_text(encoding="utf-8"))
    meta = exam.get("meta", {})
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    only = {int(x) for x in a.only.split(",") if x.strip()}

    n = 0
    for it in exam.get("items", []):
        no = int(it.get("no"))
        if only and no not in only:
            continue
        q = {"no": no, "n": 0, "figs": [], "root": str(ep.parent)}
        pts = it.get("pts", "")
        lines = [f"{'서술형 ' if it.get('kind') == '서술형' else ''}{no}. {plain(it.get('stem'))}" + ("" if it.get("ask") else f" [{pts}점]")]
        lines += blocks_text(it.get("blocks", []), q, out)
        if it.get("ask"):
            lines.append(f"{plain(it['ask'])} [{pts}점]")
        if it.get("bogi"):
            lines.append("〈보기〉")
            lines += [f"  {'ㄱㄴㄷㄹㅁㅂ'[i]}. {plain(b)}" for i, b in enumerate(it["bogi"])]
            lines.append("〈보기 끝〉")
        if it.get("choices"):
            lines.append("   ".join(f"{NUM[i]} {plain(c)}" for i, c in enumerate(it["choices"])))
        elif it.get("kind") == "서술형":
            lines.append("(서술형: 답을 문장으로 쓴다)")
        txt = "\n".join(l for l in lines if l.strip())
        if q["figs"]:
            txt += "\n\n[붙인 그림] " + ", ".join(q["figs"])
        (out / f"Q{no:02d}.md").write_text(txt + "\n", encoding="utf-8")
        n += 1

    have_tb = have_cur = False
    if a.textbook and Path(a.textbook).exists():
        shutil.copy2(a.textbook, out / "교과서.txt"); have_tb = True
    if a.curriculum and Path(a.curriculum).exists():
        shutil.copy2(a.curriculum, out / "교육과정.txt"); have_cur = True

    level = a.level or f'{meta.get("grade", "")}학년'
    subj = meta.get("subject", "과학")
    rng = a.range or ", ".join(sorted({str(it.get("unit", "")) for it in exam.get("items", []) if it.get("unit")}))
    tb = meta.get("textbook", "학생들이 배운 교과서")
    fill = {"{LEVEL}": level, "{SUBJECT}": subj, "{RANGE}": rng, "{TEXTBOOK}": tb,
            "{TB_LINE}": f"같은 폴더의 「교과서.txt」는 학생들이 배운 교과서({tb}) 본문이다. 범위·용어·수치를 확인할 때 읽는다." if have_tb else "교과서 본문은 주어지지 않았다. 일반적인 해당 학년 교과서 수준으로 판단하고, 교과서 확인이 필요한 곳은 「교과서 확인 필요」로 표시한다.",
            "{CUR_LINE}": "같은 폴더의 「교육과정.txt」는 교육부 고시 2022 개정 교육과정 원문(성취기준·성취기준 해설·적용 시 고려 사항)이다." if have_cur else "교육과정 원문은 주어지지 않았다. 아는 범위에서 판단하되 확인이 필요한 곳은 「원문 확인 필요」로 표시한다."}
    for name in ("지침_정답.md", "지침_범위.md"):
        t = (HERE / "templates" / name).read_text(encoding="utf-8")
        for k, v in fill.items():
            t = t.replace(k, v)
        (out / name).write_text(t, encoding="utf-8")
    print(f"격리 세트: {out}  문항 {n}개 · 교과서 {'있음' if have_tb else '없음'} · 교육과정 {'있음' if have_cur else '없음'}")
    print("정답·해설·출처는 넣지 않았습니다. 다음: python run_check.py", out)


if __name__ == "__main__":
    sys.exit(main())
