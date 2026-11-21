# 과학과 교육과정 원문(별책 9)에서 한 과목 부분만 잘라 격리 세트용 「교육과정.txt」를 만든다.
# 실행: python cut_curriculum.py <과목> <출력.txt> [--grep 낱말,낱말]
#   과목: 과학(중학교), 통합과학(1·2), 과학탐구실험(1·2), 물리학, 화학, 생명과학, 지구과학,
#         역학과 에너지, 전자기와 양자, 물질과 에너지, 화학 반응의 세계, 세포와 물질대사, 생물의 유전,
#         지구시스템과학, 행성우주과학, 과학의 역사와 문화, 기후변화와 환경생태, 융합과학 탐구
#   --grep 을 주면 그 낱말이 든 줄(앞뒤 몇 줄 포함)을 맨 앞에 따로 모아 준다(성취기준 해설·적용 시 고려 사항 찾기용).
import argparse, re, sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

SRC = Path(__file__).resolve().parent / "별책9_과학과_교육과정_2022.txt"
# 원문에서 「1. 성격 및 목표」가 나오는 차례(18번) = 과목 차례. 통합과학1·2, 과학탐구실험1·2는 한 덩어리로 나온다.
ORDER = ["과학", "통합과학", "과학탐구실험", "물리학", "화학", "생명과학", "지구과학",
         "역학과 에너지", "전자기와 양자", "물질과 에너지", "화학 반응의 세계", "세포와 물질대사", "생물의 유전",
         "지구시스템과학", "행성우주과학", "과학의 역사와 문화", "기후변화와 환경생태", "융합과학 탐구"]
ALIAS = {"중학교 과학": "과학", "통합과학1": "통합과학", "통합과학2": "통합과학", "과학탐구실험1": "과학탐구실험", "과학탐구실험2": "과학탐구실험"}


def starts(text):
    """과목마다 「1. 성격 및 목표」 줄이 시작하는 자리."""
    import re as _re
    hits = [m.start() for m in _re.finditer(r"(?m)^1\. 성격 및 목표\s*$", text)]
    return dict(zip(ORDER, hits)) if len(hits) == len(ORDER) else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("out")
    ap.add_argument("--grep", default="")
    a = ap.parse_args()
    text = SRC.read_text(encoding="utf-8")
    pos = starts(text)
    a.subject = ALIAS.get(a.subject, a.subject)
    if a.subject not in pos:
        print("과목을 찾지 못했습니다. 찾은 과목:", ", ".join(pos), file=sys.stderr)
        return 2
    s = pos[a.subject]
    later = sorted(v for v in pos.values() if v > s)
    e = later[0] if later else len(text)
    part = text[s:e].strip()
    head = f"교육부 고시 제2022-33호 [별책 9] 과학과 교육과정 — 「{a.subject}」 부분 원문(PDF에서 글자만 뽑음)\n\n"
    if a.grep:
        words = [w.strip() for w in a.grep.split(",") if w.strip()]
        ls = part.splitlines()
        keep = sorted({j for i, l in enumerate(ls) if any(w in l for w in words) for j in range(max(0, i - 2), min(len(ls), i + 4))})
        hits, prev = [], -9
        for j in keep:
            if j != prev + 1:
                hits.append("…")
            hits.append(ls[j]); prev = j
        if hits:
            head += "## 찾는 낱말이 든 문단(" + ", ".join(words) + ")\n\n" + "\n".join(hits) + "\n\n## 과목 전체 원문\n\n"
    Path(a.out).write_text(head + part + "\n", encoding="utf-8")
    print(f"{a.subject}: {len(part):,}자 → {a.out}")


if __name__ == "__main__":
    sys.exit(main())
