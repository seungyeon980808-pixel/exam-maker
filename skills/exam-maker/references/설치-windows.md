# 윈도우 노트북 설치 (처음 한 번)

필요한 것: Claude 유료 구독 + **Claude 데스크톱 앱**(Code 탭), ChatGPT 구독(Codex), 한글(한컴오피스).

## 1. 프로그램 (PowerShell에서, 관리자 아니어도 됨)
```powershell
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.12
winget install Typst.Typst
winget install Git.Git
```
설치 뒤 PowerShell을 닫았다 다시 연다.

## 2. 파이썬 도구·Codex
```powershell
python -m pip install pymupdf pillow pyhwpx pywin32
npm install -g @openai/codex
codex login
```
`codex login`은 브라우저가 열리면 ChatGPT 계정으로 로그인한다.

## 3. 스킬 설치 (Claude 앱 Code 탭에서)
```
/plugin marketplace add seungyeon980808-pixel/exam-maker
/plugin install exam-maker@exam-maker
```
설치 뒤 Claude 앱을 다시 시작한다. 교육과정 MCP는 처음 연결될 때 자동으로 내려받는다(인터넷 필요, 1분 안쪽).

## 4. 확인
Claude에게 「exam-maker 설치 확인해 줘」라고 하면 `scripts/doctor.py`를 돌려 빠진 것을 알려 준다.

## 5. 한글 자동화 보안 창
처음 한글 자동화를 쓸 때 「한글을 이용하여 위 파일에 접근하려는 시도…」 창이 뜨면 **「모두 허용」**을 누른다.
(창이 매번 뜨면 pyhwpx가 보안 모듈을 등록하도록 Claude에게 「한글 보안 모듈 등록해 줘」라고 한다.)

## 시험 보안
작업 폴더(예: `문서\출제작업\`)는 OneDrive·구글 드라이브 동기화 폴더 밖에 두는 것을 권한다. 시험 파일을 GitHub에 올리지 않는다.
