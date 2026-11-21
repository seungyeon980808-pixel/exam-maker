# 격리 풀이: 문항마다 GPT(codex exec)와 Claude(claude -p)가 서로 모르게, 정답 없이 따로 푼다.
# 실행: python run_check.py <격리세트폴더> [--kind 정답|범위|둘다] [--who gpt|claude|둘다] [--jobs 4] [--only 1,3]
# 결과: <폴더>/결과/gpt_정답_Q01.md, claude_정답_Q01.md …  → 다음: python summarize.py <exam.json> <폴더>
# - 두 모델 모두 이 폴더만 읽기 전용으로 본다(쓰기·셸·웹 금지).
# - Claude 몫은 기본으로 「결과/claude_할일_<종류>_Qnn.txt」로 남긴다. Claude Code 세션이 문항마다 하위 에이전트를
#   따로 띄워(문항끼리·GPT 결과를 서로 못 보게) 그 파일 내용대로 풀고 결과/claude_<종류>_Qnn.md로 저장한다(SKILL.md 참고).
#   claude 명령줄이 로그인되어 있으면 --claude-cli 로 바로 돌릴 수도 있다.
import argparse, concurrent.futures as cf, re, shutil, subprocess, sys, time
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path


def figs_of(md_text):
    return sorted(set(re.findall(r"Q\d+_그림\d+\.[A-Za-z]+", md_text)))


def prompt(d, kind, q):
    guide = (d / f"지침_{kind}.md").read_text(encoding="utf-8")
    body = q.read_text(encoding="utf-8")
    return f"{guide}\n\n----- 문항 -----\n{body}\n"


def run_gpt(codex, d, res, kind, q, effort):
    out = res / f"gpt_{kind}_{q.stem}.md"
    args = [codex, "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", str(d),
            "-c", f'model_reasoning_effort="{effort}"']
    for f in figs_of(q.read_text(encoding="utf-8")):
        args += ["-i", str(d / f)]
    args += ["-o", str(out), "-"]
    t = time.time()
    with open(res / f".gpt_{kind}_{q.stem}.log", "w", encoding="utf-8") as log:
        r = subprocess.run(args, input=prompt(d, kind, q), text=True, encoding="utf-8", stdout=log, stderr=subprocess.STDOUT)
    return f"GPT {kind} {q.stem}: {'완료' if out.exists() and r.returncode == 0 else '실패(로그 확인)'} {time.time() - t:.0f}초 {last_line(out)}"


def run_claude(claude, d, res, kind, q):
    out = res / f"claude_{kind}_{q.stem}.md"
    p = prompt(d, kind, q) + f"\n(그림 파일과 교과서.txt·교육과정.txt는 이 폴더 {d} 에 있다. Read 도구로 연다. 이 폴더 밖의 파일은 읽지 않는다.)\n"
    if not claude:
        (res / f"claude_할일_{kind}_{q.stem}.txt").write_text(p, encoding="utf-8")
        return f"Claude {kind} {q.stem}: 할일 파일로 남김(세션 하위 에이전트가 풂)"
    args = [claude, "-p", "--add-dir", str(d), "--allowedTools", "Read",
            "--disallowedTools", "Bash,Write,Edit,WebFetch,WebSearch,Task"]
    t = time.time()
    with open(out, "w", encoding="utf-8") as fo, open(res / f".claude_{kind}_{q.stem}.log", "w", encoding="utf-8") as log:
        r = subprocess.run(args, input=p, text=True, encoding="utf-8", stdout=fo, stderr=log, cwd=str(d))
    return f"Claude {kind} {q.stem}: {'완료' if r.returncode == 0 else '실패(로그 확인)'} {time.time() - t:.0f}초 {last_line(out)}"


def last_line(p):
    try:
        ls = [l for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
        return ls[-1][:40] if ls else ""
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--kind", default="정답", choices=["정답", "범위", "둘다"])
    ap.add_argument("--who", default="둘다", choices=["gpt", "claude", "둘다"])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--claude-cli", action="store_true", help="Claude 몫을 claude -p 로 바로 돌림(명령줄 로그인 필요)")
    ap.add_argument("--effort", default="high", help="GPT 추론 강도(low|medium|high)")
    a = ap.parse_args()
    d = Path(a.dir).resolve()
    res = d / "결과"
    res.mkdir(exist_ok=True)
    only = {int(x) for x in a.only.split(",") if x.strip()}
    qs = sorted(q for q in d.glob("Q[0-9][0-9].md") if not only or int(q.stem[1:]) in only)
    kinds = ["정답", "범위"] if a.kind == "둘다" else [a.kind]
    codex = shutil.which("codex")
    claude = shutil.which("claude") if a.claude_cli else None
    if a.who in ("gpt", "둘다") and not codex:
        print("codex 명령을 찾지 못했습니다. `npm i -g @openai/codex` 뒤 `codex login`을 하세요.", file=sys.stderr)
        return 2
    jobs = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for kind in kinds:
            for q in qs:
                if a.who in ("gpt", "둘다"):
                    jobs.append(ex.submit(run_gpt, codex, d, res, kind, q, a.effort))
                if a.who in ("claude", "둘다"):
                    jobs.append(ex.submit(run_claude, claude, d, res, kind, q))
        for j in cf.as_completed(jobs):
            print(j.result(), flush=True)
    print(f"끝. 결과 폴더: {res}")
    if a.who != "gpt" and not claude:
        print("※ Claude 몫은 결과/claude_할일_*.txt 로 남겼습니다. 세션에서 하위 에이전트로 문항마다 따로 풀고 결과/claude_<종류>_Qnn.md로 저장하세요.")


if __name__ == "__main__":
    sys.exit(main())
