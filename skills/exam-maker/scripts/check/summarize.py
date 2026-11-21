# 격리 풀이 결과를 정답과 맞대 요약한다 → <폴더>/요약.md, 그리고 exam.json 옆 review.json(코멘트판 오른쪽 「검토」 칸).
# 실행: python summarize.py <exam.json> <격리세트폴더>
import json, re, sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

ANS = re.compile(r"최종\s*답\s*[:：]\s*([①②③④⑤]|서술형)")


def final(p):
    if not p.exists():
        return None
    m = ANS.findall(p.read_text(encoding="utf-8"))
    return m[-1] if m else "?"


def issues(p):
    if not p.exists():
        return 0, 0
    t = p.read_text(encoding="utf-8")
    return len(re.findall(r"^\|\s*높음", t, re.M)), len(re.findall(r"^\|\s*중간", t, re.M))


def verdict(p):
    if not p.exists():
        return None
    t = p.read_text(encoding="utf-8")
    for v in ("교체 권장", "고치면 출제 가능", "그대로 출제 가능"):
        if v in t.split("종합 판정")[-1]:
            return v
    return "?"


def main():
    ep, d = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    res = d / "결과"
    exam = json.loads(ep.read_text(encoding="utf-8"))
    rows, review = [], {}
    for it in exam.get("items", []):
        no = int(it["no"]); q = f"Q{no:02d}"
        ans = it.get("ans") if it.get("kind", "선택형") == "선택형" else "서술형"
        rv = {}
        line = [str(no), str(ans)]
        for who, lab in (("gpt", "GPT"), ("claude", "Claude")):
            f = final(res / f"{who}_정답_{q}.md")
            hi, mid = issues(res / f"{who}_정답_{q}.md")
            if f is None:
                cell = "—"
            else:
                ok = "일치" if f == ans else ("서술형" if f == "서술형" else f"불일치({f})")
                cell = f"{ok} · 시비 높음 {hi} 중간 {mid}"
            rv[lab] = cell
            line.append(cell)
            v = verdict(res / f"{who}_범위_{q}.md")
            rv[f"{lab} 범위"] = v or "—"
            line.append(v or "—")
        review[str(no)] = rv
        rows.append(line)
    head = "| 번호 | 정답 | GPT 풀이 | GPT 범위 | Claude 풀이 | Claude 범위 |\n|---|---|---|---|---|---|\n"
    md = "# 격리 풀이 요약\n\n" + head + "\n".join("| " + " | ".join(r) + " |" for r in rows) + "\n\n" \
         "불일치·시비 높음·「교체 권장」인 문항은 결과 파일을 열어 근거를 읽고 선생님과 상의한다.\n"
    (d / "요약.md").write_text(md, encoding="utf-8")
    (ep.parent / "review.json").write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    print(md)
    print("review.json:", ep.parent / "review.json")


if __name__ == "__main__":
    sys.exit(main())
