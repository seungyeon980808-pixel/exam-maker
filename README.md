# exam-maker — 학교 정기고사 함께 출제하기 (Claude Code 스킬)

## 설치: Claude에게 이 링크만 주세요
Claude 앱 → **Code** 탭 → 아무 폴더나 열고 이렇게 말하면 됩니다.
```
https://github.com/seungyeon980808-pixel/exam-maker 설치해 줘
```

> **Claude에게 (이 저장소 설치를 부탁받았을 때)**
> 1. 운영체제를 확인한다. **윈도우**면 PowerShell에서 아래 한 줄을 실행한다(사용자에게 「설치 스크립트를 실행한다」고 한 줄 알리고 승인받는다):
>    ```powershell
>    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/seungyeon980808-pixel/exam-maker/main/install.ps1 | iex"
>    ```
>    Node.js·Python·Typst·Git(없을 때만, winget) → 파이썬 도구 → Codex·Claude 명령줄 → 이 플러그인 → 교육과정 MCP → `codex login`(브라우저에서 ChatGPT 로그인) → 설치 확인까지 한다. 관리자 확인 창이 뜨면 사용자에게 「예」를 누르게 한다.
>    「PowerShell을 다시 열고 한 번 더」라는 말이 나오면 같은 명령을 한 번 더 실행한다.
> 2. **맥**이면: `brew install node python typst` → `python3 -m pip install pymupdf pillow` → `npm i -g @openai/codex @anthropic-ai/claude-code` → `claude plugin marketplace add seungyeon980808-pixel/exam-maker` → `claude plugin install exam-maker@exam-maker` → `codex login`.
> 3. 끝나면 사용자에게 **Claude 앱을 완전히 껐다 켜라**고 안내하고, 다시 켠 뒤 「기말고사 출제를 시작하자」라고 말하면 된다고 알려 준다. 플러그인이 켜지면 `exam-maker` 스킬과 `curriculum-kr-secondary` MCP가 보인다.

선생님과 Claude가 대화하며 중간·기말고사 한 세트를 처음부터 만드는 스킬입니다.

```
질문(범위·배점·양식) → 출제 계획표 → 문항 쓰기 → 코멘트판 시안 ⇄ 코멘트·수정(판 올리기)
   → 그림(원본 잘라 쓰기 → GPT) → GPT·Claude 격리 풀이 + 교과서·수준·교육과정 대조
   → 학교 양식 한글(hwpx) 시험지·정답표 → 한글에서 마지막 조판 → 정답과 해설·문항 검토 용지 → v1.0
```

## 들어 있는 것
| 폴더 | 하는 일 |
|---|---|
| `skills/exam-maker/SKILL.md` | 출제 순서와 규칙 (Claude가 먼저 읽음) |
| `scripts/board` | 문항 원본(`exam.json`) → HTML 코멘트판·비교 시안, 코멘트 자동 저장 서버 |
| `scripts/check` | 정답 없는 격리 문항지 → GPT(codex)·Claude 따로 풀기 → 요약 |
| `scripts/curriculum` | 2022 개정 과학과 교육과정 원문(고시 제2022-33호 별책 9)에서 과목별 성취기준 해설·적용 시 고려 사항 잘라내기 |
| `scripts/hwpx` | 학교 양식 hwpx의 모양을 빌려 시험지·정답표 hwpx 만들기, 윈도우 한글 자동화(hwp→hwpx, PDF·쪽 그림) |
| `scripts/explain` | 정답과 해설·문항 검토 용지·점검표 PDF (Typst) |
| `scripts/figure` | 원본 그림 잘라 쓰기, GPT 그림 생성 |
| `.mcp.json` | 교육과정 MCP(중·고 성취기준 3,838개) 자동 연결 |

## 손으로 설치하기 (윈도우)
[`skills/exam-maker/references/설치-windows.md`](skills/exam-maker/references/설치-windows.md) 를 따릅니다. 요약:
```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Typst.Typst
winget install Git.Git
python -m pip install pymupdf pillow pyhwpx pywin32
npm install -g @openai/codex
codex login
```

스킬 설치(PowerShell):
```powershell
npm install -g @anthropic-ai/claude-code
claude plugin marketplace add seungyeon980808-pixel/exam-maker
claude plugin install exam-maker@exam-maker
```
앱을 다시 시작한 뒤 「exam-maker 설치 확인해 줘」 → 「기말고사 출제를 시작하자」.

## 시험 보안
- 이 저장소에는 **도구와 서식만** 있습니다. 시험 문항·학교 양식·교과서는 각자 컴퓨터의 작업 폴더에만 둡니다.
- 예시 문항(`examples/sample`)은 지어낸 가짜 문항입니다.
- 올리기 전 `python tools/guard.py` 로 시험 파일이 섞이지 않았는지 검사합니다.

## 출처·라이선스
- 이 저장소: MIT
- 교육과정 MCP: [korean-secondary-learning-map-mcp](https://github.com/raphysicst-create/korean-secondary-learning-map-mcp) (npm에서 내려받아 실행)
- 교육과정 원문: 교육부 고시 제2022-33호 [별책 9] 과학과 교육과정
