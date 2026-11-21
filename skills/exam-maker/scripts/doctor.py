# 설치 확인: 출제에 필요한 프로그램이 다 있는지 본다. 실행: python doctor.py
import importlib.util, json, os, platform, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):  # 윈도우 명령 창(cp949)에서도 한글·기호가 깨지지 않게
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass
from pathlib import Path

ok_all = True


def line(ok, name, detail=""):
    global ok_all
    ok_all &= ok
    print(f"{'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))


def ver(cmd):
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        r = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "있음"
    except Exception as e:
        return f"있음(버전 확인 실패: {e})"


print(f"운영체제: {platform.system()} {platform.release()} · Python {sys.version.split()[0]}")
line(sys.version_info >= (3, 9), "Python 3.9 이상", sys.version.split()[0])
v = ver(["node", "--version"]); line(bool(v), "Node.js 20 이상", v or "없음 → winget install OpenJS.NodeJS.LTS")
v = ver(["typst", "--version"]); line(bool(v), "Typst (해설지 PDF)", v or "없음 → winget install Typst.Typst")
v = ver(["codex", "--version"]); line(bool(v), "Codex CLI (GPT 격리 풀이·그림)", v or "없음 → npm i -g @openai/codex")
auth = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
line(auth.exists(), "Codex 로그인", "됨" if auth.exists() else "안 됨 → 명령 창에서 codex login (ChatGPT 계정)")
for mod, pipname, why in (("pymupdf", "pymupdf", "PDF 읽기·자르기·쪽 그림"), ("PIL", "pillow", "그림 처리")):
    line(importlib.util.find_spec(mod) is not None, f"파이썬 {pipname} ({why})", "" if importlib.util.find_spec(mod) else f"없음 → python -m pip install {pipname}")
if platform.system() == "Windows":
    has = importlib.util.find_spec("pyhwpx") is not None or importlib.util.find_spec("win32com") is not None
    line(has, "한글 자동화(pyhwpx/pywin32)", "" if has else "없음 → python -m pip install pyhwpx pywin32")
    hwp = any(Path(p).exists() for p in (r"C:\Program Files (x86)\HNC", r"C:\Program Files\HNC", r"C:\Program Files (x86)\Hnc", r"C:\Program Files\Hnc"))
    line(hwp, "한글(한컴오피스) 설치", "" if hwp else "못 찾음 — 설치 위치가 다르면 무시해도 됨")
else:
    print("ℹ️  윈도우가 아니라 한글 자동화(hwp→hwpx, 쪽 그림)는 건너뜁니다. hwpx 만들기는 됩니다.")
fig = Path.home() / ".claude" / "plugins" / "marketplaces" / "5e-figure" / "figure.mjs"
print(("✅" if fig.exists() else "ℹ️ ") + " 5E 그림 엔진(5e-figure) " + ("설치됨" if fig.exists() else "없음 → install.ps1을 다시 실행하면 같이 설치(없어도 gpt_image.py로 대신함)"))
mcp = Path(os.environ.get("EXAM_MAKER_HOME", Path.home() / ".exam-maker")) / "curriculum-mcp" / "node_modules" / "korean-secondary-learning-map-mcp"
print(("✅" if mcp.exists() else "ℹ️ ") + " 교육과정 MCP " + ("설치됨" if mcp.exists() else "아직 설치 전(Claude 앱이 처음 연결할 때 자동 설치)"))
print("\n" + ("모두 준비됐습니다." if ok_all else "❌ 표시된 것을 설치한 뒤 다시 실행하세요."))
