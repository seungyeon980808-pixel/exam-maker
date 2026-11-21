# 원본이 없을 때: GPT(Codex 로그인, 이미지 생성 기능)로 시험지용 그림을 만든다. Claude가 직접 그리지 않는다.
# 실행: python gpt_image.py "<그림 요청>" <출력.png> [--ref 참고그림.png ...] [--style 선화|사진]
#   --ref: 바꿔 그릴 원본(교과서 그림 등)이나 참고 그림. 원본을 시험지용 흑백 선화로 다시 그릴 때 쓴다.
# 필요: npm i -g @openai/codex  →  codex login (ChatGPT 계정)
import argparse, shutil, subprocess, sys, tempfile, time
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

RULES = """시험지에 넣을 그림 한 장을 만들어 지정한 파일로 저장한다.
- 흑백(회색조) 인쇄용, 흰 바탕, 깔끔한 선. 그림자·배경·장식·캐릭터 금지.
- 그림 안에 설명 문장·제목·출처 글자를 넣지 않는다. 필요한 라벨(A, B, ㉠, (가) 등)만, 요청에 있는 것만 넣는다.
- 장면이 (가)(나)처럼 여러 개면 한 장에 몰아 그리지 말고 요청한 한 장면만 그린다.
- 글자 규칙: 수치+단위는 정자·붙여 씀(3m, 60kg, 25°C), 물리량 기호는 기울임(m, v), 첨자는 정자(v₀의 0).
- 과학적으로 정확해야 한다(구조·비율·방향).
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request")
    ap.add_argument("out")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--style", default="선화", choices=["선화", "사진"])
    a = ap.parse_args()
    codex = shutil.which("codex")
    if not codex:
        sys.exit("codex 명령이 없습니다: npm i -g @openai/codex 뒤 codex login")
    out = Path(a.out).resolve()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        style = "펜 선화(line art)" if a.style == "선화" else "흑백 사진처럼 사실적인 그림"
        prompt = RULES + f"\n그림 방식: {style}\n요청: {a.request}\n" \
            + ("첨부한 그림을 바탕으로 위 규칙에 맞게 다시 그린다.\n" if a.ref else "") \
            + f"이미지 생성 도구로 그림을 만들고, 결과를 현재 폴더에 figure.png 로 저장한 뒤 「저장함」이라고만 답한다."
        args = [codex, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write", "-C", str(td)]
        for r in a.ref:
            args += ["-i", str(Path(r).resolve())]
        args += ["-"]
        t = time.time()
        r = subprocess.run(args, input=prompt, text=True, encoding="utf-8", capture_output=True)
        cand = sorted(td.rglob("*.png"), key=lambda p: p.stat().st_mtime)
        if not cand:
            print(r.stdout[-1500:], r.stderr[-1500:], sep="\n", file=sys.stderr)
            sys.exit("그림을 받지 못했습니다. 위 로그를 보고 요청을 고쳐 다시 시도하세요(codex login 상태도 확인).")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cand[-1], out)
        print(f"그림: {out} ({time.time() - t:.0f}초)")


if __name__ == "__main__":
    main()
