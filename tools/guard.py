# 올리기 전 시험 보안 검사: 저장소에 시험 파일·학교 정보가 섞였는지 본다. 하나라도 걸리면 종료 코드 1.
# 실행: python tools/guard.py   (git에 올라갈 파일만 검사)
import re, subprocess, sys
from pathlib import Path
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = Path(__file__).resolve().parents[1]
ALLOW = {"skills/exam-maker/scripts/hwpx/templates/기본양식.hwpx"}
BAD_EXT = {".hwp", ".hwpx", ".pdf", ".docx", ".xlsx", ".pptx", ".exampool", ".5e"}
# 실제 학교·사람 이름이나 내 컴퓨터 경로가 섞이면 안 된다(예시는 「예시고등학교」「○○」만).
BAD_TEXT = [r"/Users/", r"C:\\\\Users\\\\", r"GoogleDrive-", r"고등학교에 있습니다", r"저작권은 .{1,20}학교",
            r"대왕중", r"한광고", r"출제자\s*[가-힣]{2,4}\s*\(인\)"]

files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8").stdout.split("\n")
bad = []
for f in filter(None, files):
    p = ROOT / f
    if f in ALLOW:
        continue
    if p.suffix.lower() in BAD_EXT:
        bad.append(f"시험·문서 파일: {f}")
        continue
    if p.suffix.lower() in {".py", ".md", ".json", ".js", ".cjs", ".mjs", ".css", ".html", ".typ", ".txt", ".yml"}:
        try:
            t = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in BAD_TEXT:
            if f.endswith("tools/guard.py"):
                break
            for m in re.finditer(pat, t):
                bad.append(f"{f}: 「{m.group(0)}」")
                break
    if p.exists() and p.stat().st_size > 20 * 1024 * 1024:
        bad.append(f"20MB 넘는 파일: {f}")
if bad:
    print("❌ 올리면 안 되는 것이 있습니다:")
    print("\n".join("  - " + b for b in bad))
    sys.exit(1)
print(f"✅ 시험 보안 검사 통과 (파일 {len([f for f in files if f])}개)")
