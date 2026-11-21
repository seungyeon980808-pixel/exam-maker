# 학교 양식 hwpx 시험지 만들기 (`scripts/hwpx/`)

문항 원본 `exam.json`(형식: `references/exam-json.md`)을 **학교 시험지 양식(hwpx)의 글자·문단·테두리 모양을 빌려** 한글 시험지로 만든다.
양식의 머리(표지 표·결재란·안내 상자·꼬리말)는 그대로 두고, 양식 안의 예시 문항 자리를 지운 뒤 새 문항으로 채운다.

> **시험 보안**: 실제 시험 문항(`exam.json`)·학교 양식 파일·만든 시험지는 이 저장소에 넣지 않는다. 작업 폴더(저장소 밖)에서만 다룬다.

## 파일

| 파일 | 하는 일 | 어디서 |
|---|---|---|
| `inspect_form.py` | 양식 살펴보기 → `form_map.json` 초안 | 맥·윈도우 |
| `build_exam.py` | `exam.json` + 양식 → 시험지 hwpx | 맥·윈도우 |
| `build_answers.py` | `exam.json` → 정답표 hwpx(정답·배점·단원·성취기준·난이도, 서술형 모범 답안·채점 기준) | 맥·윈도우 |
| `hangul_win.py` | 한글 자동화: hwp→hwpx, PDF, 쪽 그림, 한글로 열기 | **윈도우 + 한글** |
| `hwpx_common.py` | 위 스크립트가 같이 쓰는 부품 | |
| `templates/기본양식.hwpx` | 학교 정보 없는 중립 양식(B4 2단, 머리에 「○○학교 ○학년 ○○ ○○고사」) | |

필요한 것: Python 3.9 이상(표준 라이브러리만으로 동작, Pillow 가 있으면 PNG·JPG 밖의 그림도 넣는다).
윈도우에서 `hangul_win.py` 를 쓰려면 `pip install pyhwpx pymupdf` (pyhwpx 대신 `pywin32` 도 됨).

## 흐름

```text
학교 양식 받기 ─(hwp면)→ to-hwpx ─→ inspect_form ─→ form_map 확인·고치기 ─→ build_exam ─→ pages 로 쪽 그림 확인 ─→ 한글에서 손보기
```

### 1. 양식 받기
학교가 준 시험지 양식 파일을 작업 폴더에 둔다. 양식이 없으면 `templates/기본양식.hwpx` 를 쓴다(2단계·3단계 건너뜀).

### 2. hwp 면 hwpx 로 (윈도우)
```bat
python hangul_win.py to-hwpx 학교양식.hwp 학교양식.hwpx
```
처음 실행하면 한글이 「파일에 접근하려는 시도」 승인 창을 띄울 수 있다 → **「모두 허용」**.
pyhwpx 를 설치해 두면 보안 모듈을 스스로 등록해 이 창이 거의 안 뜬다(자세한 것은 `hangul_win.py` 맨 위 설명).

### 3. 양식 살펴보기
```bat
python inspect_form.py 학교양식.hwpx --out form_map.json
```
출력에서 확인할 것
- **[머리]**: 그대로 둘 문단(표지 표·결재란·[배점 현황] 상자 등). **[예시 문항 시작]** 번호가 맞는지. 틀리면 `form_map.json` 의 `body_start.index` 를 고친다.
- **[머리 글자 바꾸기 미리보기]**: 학교·학년·과목·고사 이름이 `{school}` `{grade}` `{subject}` `{exam}` 등 meta 값으로 바뀔 자리. 엉뚱한 곳이 바뀌면 `replace` 규칙을 지우거나 고친다(정규식, 위에서부터 차례로).
- **[문단 모양]·[글자 모양]** 목록(번호 · 글꼴 · 크기 · 줄 간격 · 내어쓰기 + 실제 문장 앞 20자)과 **[역할 추측]**:
  `question`(문항 발문) · `text`(묻는 문장·본문) · `choice`(선지) · `bogi_title`·`bogi_item`(〈보기〉) · `box_text`(상자 안) · `table_text`(표 칸).
  역할마다 `paraPr`·`charPr` 번호가 양식의 어느 문장 모양인지 목록에서 찾아 맞춘다. `question.number_charPr` 는 문항 번호 글자 모양(비우면 발문 모양의 굵게).

`form_map.json` 의 다른 칸

| 칸 | 기본 | 뜻 |
|---|---|---|
| `bogi_label` | 양식에서 찾은 것 또는 `〈보기〉` | 〈보기〉 머리 글 |
| `line_width` | 양식에서 가장 많이 쓴 굵기 | 상자·표·〈보기〉 선 굵기 |
| `points_format` | `[{pts}점]` | 묻는 문장 끝 배점(소수 가능) |
| `number_format` | `{no}.` | 문항 번호(번호는 글자로 적는다. 한글에서 문항 순서를 바꾸면 번호도 손으로 고친다) |
| `ask_indent` | `1.0` | 묻는 문장 첫 줄 들여쓰기(글자 수) |
| `essay_title` | `서술형` | 서술형 구역 머리 띠 |
| `update_summary` | `true` | 머리의 「총 N문항」「N문항×P점 + … = T점」을 선택형 문항으로 다시 셈 |
| `use_styles` | 없음(=false) | true 면 양식 스타일 번호도 쓴다(양식 「문제」 스타일에 문단 번호가 묶여 있으면 번호가 겹치니 보통 끈다) |

### 4. 시험지 만들기
```bat
python build_exam.py exam.json 학교양식.hwpx 시험지.hwpx --map form_map.json
python build_exam.py exam.json 학교양식.hwpx 3번만.hwpx --map form_map.json --only 3
python build_exam.py exam.json templates\기본양식.hwpx 시험지.hwpx            (양식 없을 때)
```
- `--pages N` : 꼬리말 「총( N )쪽」 의 N 을 바꾼다(5단계에서 쪽 수를 본 뒤 다시 만들 때).
- 만드는 모양(확정 규칙)
  - 모든 문단 줄 간격 = `meta.line_spacing`(%). 〈보기〉 머리 글 칸만 얇게 하려고 130%.
  - 〈보기〉: 머리 줄은 가는 선 + 가운데 〈보기〉, 안쪽 좌우·아래 여백 1.5mm, ㄱ. ㄴ. ㄷ. 은 번호 뒤에 맞춰 내어쓰기.
  - 선지: ㄱ·ㄴ·ㄷ 조합은 시험지 전체에서 자리마다 같은 폭인 **1×5 칸**. 그 밖은 실제 글 폭으로 **한 줄 5개 → 3+2 → 한 줄에 하나**,
    두 줄로 넘는 선지는 번호(①) 뒤에 맞춰 내어쓰기. 짧은 선지 줄도 테두리 없는 칸이라 한글·미리보기에서 자리가 같다.
  - 배점은 묻는 문장 끝 `[3점]`. 서술형은 선택형 뒤 「서술형」 띠 아래.
  - 블록: `fig`(그림, BinData 로 넣음) · `table` · `box` · `talk`(대화 상자) · `pair`(나란히 두 자료) · `eq`(가운데 수식) · `text`.
    글 안 `<i><b><u><sub><sup>`, `$…$`(LaTeX 꼴 → 한글 수식: `\frac` `\sqrt` `_` `^` `\times` `\Delta` `\mathrm` 등).
  - 머리 칸의 글이 meta 값으로 길어져 칸 폭을 넘으면 그 칸 글자 크기를 줄인다(출력에 「글자 크기를 N%로 줄임」).
- 출력의 `[경고]` 를 꼭 읽는다(못 찾은 그림, 한글 수식으로 못 바꾼 LaTeX 명령, 양식에 없는 모양 번호).

### 5. 쪽 그림으로 확인 (윈도우)
```bat
python hangul_win.py pages 시험지.hwpx 쪽그림
```
한글이 조판한 그대로 PDF 로 저장한 뒤 `쪽그림\page-1.png …` 를 만든다(같은 폴더에 PDF 도 남김). Claude 는 이 PNG 를 읽어
〈보기〉 상자·조합 선지 줄·수식·표·그림·단 넘김을 눈으로 확인하고, 고칠 것은 **exam.json 을 고쳐 다시 만든다**.
표·상자 높이는 글 폭을 어림해 적어 두지만 한글은 열 때 실제 글에 맞춰 다시 늘린다.

### 6. 한글에서 손보기
```bat
python hangul_win.py open 시험지.hwpx
```
단 넘김 위치, 문항이 쪽 끝에서 잘리는 곳, 그림 크기처럼 사람 눈으로 정할 마지막 조판을 한글에서 고친다.
PDF 가 필요하면 `python hangul_win.py to-pdf 시험지.hwpx 시험지.pdf`.

### 정답표
```bat
python build_answers.py exam.json 정답표.hwpx --form 학교양식.hwpx --map form_map.json
python build_answers.py exam.json 정답표.hwpx                       (기본 서식)
```
A4 세로 한 단. 번호·유형·정답·배점·단원·성취기준·난이도 표, 배점 합계와 정답 분포, 서술형 모범 답안·채점 기준 표.

## 알아 둘 것
- 양식의 예시 문항은 **body_start 부터 끝까지** 지운다. 양식 맨 끝에 「끝」 표시 같은 것이 있었다면 그것도 지워지니 한글에서 다시 넣는다.
- 첫 문단에 떠 있는 머리 표(결재란 등)는 위치 기준을 「쪽」으로 바꾼다(첫 문단이라 자리는 같고, 두 단 모두 그 표를 피해 흐른다).
- 양식에 구역 파일이 여러 개면 첫 구역만 채운다.
- 맥에서는 `hangul_win.py` 를 쓸 수 없다. 맥에서 만든 hwpx 는 윈도우의 한글에서 열어 확인한다.
