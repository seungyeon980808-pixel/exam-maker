# explain — 정답과 해설 · 문항 검토 용지 · 점검표 PDF

`exam.json` 하나로 교사용 PDF 세 가지를 만든다. 색 없이 평가원식 흑백이다.

| 파일 | 내용 |
|---|---|
| `<제목> 정답과 해설_(<판>).pdf` | 정답표(번호 · 정답 · 배점, 12문항씩) → 문항마다 정답 · 성취기준 · 단원 · 난이도 · 답 형식 · 배점 · 출처 → 출제 의도 · 출제 근거 · 핵심 개념 상자 → 해설(〈보기〉별 · 선지별 문단). 두 단. 서술형은 모범 답안과 채점 기준 표 |
| `<제목> 문항 검토 용지_(<판>).pdf` | 한 문항에 한 쪽. 문항 정보 표 + 성취기준 원문 / ① 참고 자료 \| ② 출제 문항(시험지 모양, 그림 포함) / ③ 출제 의도 · 근거 \| ④ 문항 해설 / ⑤ 체크리스트 · AI에게 요청 \| ⑥ 메모 (2열 × 3줄) |
| `<제목> 교과서·수준·교육과정 점검표_(<판>).pdf` | `--check check.json`을 줄 때만. A4 가로. 기준 → 대조한 교육과정 원문 → 문항별 Claude · GPT · 종합 판정과 교과서 대조 · 수준 · 교육과정 · 고친 점 → 요약 |

제목 · 판은 `exam.json`의 `meta.title` · `meta.version`에서 온다(점검표 판은 `check.json`의 `version`이 있으면 그것).

## 준비

- Python 3.8 이상(표준 라이브러리만 쓴다)
- Typst 0.13 이상 — 윈도우: `winget install --id Typst.Typst` (또는 https://github.com/typst/typst/releases 에서 받아 PATH에 넣기)

## 실행

```bat
:: 윈도우(명령 프롬프트) — 이 폴더에서
py make_explain.py ..\..\examples\sample\exam.json 결과
py make_explain.py 내시험\exam.json 결과 --check 내시험\check.json
```

```sh
# 맥
python3 make_explain.py ../../examples/sample/exam.json 결과
```

| 옵션 | 뜻 |
|---|---|
| `--check check.json` | 점검표도 만들고, 검토 용지 ③ 칸에 점검 판정 · 고친 점, 성취기준 원문을 넣는다 |
| `--paper jis-b4` / `a4` | 해설 · 검토 용지 용지. 기본은 시험지와 같은 B4(`jis-b4`). 점검표는 늘 A4 가로 |
| `--only explain` / `review` / `check` | 하나만 만든다(여러 번 줄 수 있음) |
| `--typst <경로>` | typst 실행 파일을 직접 지정(PATH에 없을 때. 환경 변수 `TYPST`도 된다) |
| `--only-bundled-fonts` | 컴퓨터 글꼴을 쓰지 않고 `fonts/`만으로 만든다(글꼴 점검용) |
| `--keep-typ` | 만든 `.typ`와 서식을 `<out>/_typ/`에 남긴다(조판 오류 볼 때) |

끝에 「확인할 것」 목록이 나온다. 정답이 ①~⑤가 아님, 선지가 5개가 아님, `sol.intent`·`basis`·`concept` 빠짐, 서술형 채점 기준 없음, 그림 파일 없음, 짝이 맞지 않는 꼬리표, 모르는 수식 명령, 그리고 **〈보기〉 해설의 (참)/(거짓)으로 계산한 정답이 `ans`와 다를 때**를 알려 준다.

## exam.json에서 읽는 것

형식은 `references/exam-json.md`. 이 도구가 쓰는 칸:

- `meta`: `school` · `year` · `semester` · `grade` · `exam` · `subject` · `title` · `version` · `textbook`
- 문항: `no` · `kind` · `pts` · `unit` · `standard` · `level` · `ans` · `stem` · `blocks` · `ask` · `bogi` · `choices` · `sol` · `src` · `rubric`
- `sol.concept`은 글 하나 또는 글 배열(배열이면 항목마다 한 줄).
- 〈보기〉 문항에서 `sol.bogi`가 `ㄱ(참) …`, `ㄴ(거짓) …`(또는 `(옳음)`·`(옳지 않음)`)으로 시작하고 `sol.choices`가 없으면, 「선지: ① ㄱ(×) ② … ④ ㄱ, ㄷ(○ 정답) …」 한 줄을 저절로 붙인다.
- 글 안 표시: `<i> <b> <u> <sub> <sup>`, `$…$`(LaTeX 꼴: `\frac` `\sqrt` `_` `^` `\text` `\mathrm` 그리스 문자 `\times` `\Delta` `\approx` `\rightleftharpoons` 등), 줄바꿈 `\n`.
- 그림(`fig`)은 `exam.json`이 있는 폴더 기준 상대 경로. 없는 그림은 「그림 파일 없음」 칸으로 그리고 알린다.

**이 도구만 읽는 선택 칸**(없어도 된다):

| 칸 | 뜻 |
|---|---|
| `ref_fig` | 검토 용지 ① 참고 자료 칸에 넣을 원본 그림(교과서 쪽 · 기출 문항을 자른 것). `exam.json` 기준 상대 경로. 없으면 ① 칸에 출처 · 교과서 이름만 적힌다 |
| `ref_label` | ① 칸 제목 옆 설명(예: `"교과서 132쪽 그림 3"`) |
| `standard_text` | 그 문항의 성취기준 원문(`check.json`의 `standards`보다 먼저) |

## check.json 형식

교과서 · 수준 · 교육과정 점검 결과. 예시: `check.example.json`.

```json
{
  "version": "v0.2",
  "criteria": "기준 설명 한 문단 (선택, 없으면 기본 문장)",
  "standards": {"[12생과02-03]": "성취기준 원문"},
  "rules": [
    ["[12생과02-03] 성취기준 해설", "교육과정 문서의 성취기준 해설 원문"],
    ["적용 시 고려 사항", "교육과정 문서의 적용 시 고려 사항 원문"]
  ],
  "items": {
    "1": {
      "교과서 대조": "풀이 요소마다 교과서 쪽 · 문장 대조",
      "수준": "학년 · 수학 수준 판단",
      "교육과정": "성취기준 해설 · 적용 시 고려 사항 원문과 대조한 결과(「…」로 인용)",
      "GPT 판정": "그대로",
      "Claude 판정": "고치면",
      "종합": "고치면",
      "고친 점": "무엇을 어떻게 고쳤는지(또는 고칠 안)"
    }
  },
  "summary": "요약 한 줄 (선택, 없으면 종합 판정 개수로 만든다)"
}
```

- 판정은 `그대로` · `고치면` · `교체` 셋 중 하나로 시작한다(`고치면(가벼움)`처럼 덧붙여도 됨). `고치면`은 굵게, `교체`는 「■ 교체」로 찍힌다.
- `종합`이 없으면 두 판정 중 무거운 쪽(교체 > 고치면 > 그대로).
- `items`는 문항 번호를 열쇠로 하는 객체, 또는 `{"no": 1, …}`의 배열.
- `standards`는 검토 용지의 「성취기준 원문」 줄에 들어간다.
- 모든 글 칸에 `$…$`와 `<i>` 같은 표시를 쓸 수 있다.

## 글꼴

| 자리 | 먼저 쓰는 것(fonts/) | 없을 때 넘어가는 순서(컴퓨터 글꼴) |
|---|---|---|
| 본문 명조(문항 · 해설) | Noto Serif KR Static | 함초롬바탕(HCR Batang) → 바탕(Batang) → AppleMyungjo |
| 고딕(번호 · 제목 · 표 머리 · 안내) | Pretendard Regular · Bold | 함초롬돋움(HCR Dotum) → 맑은 고딕(Malgun Gothic) → Apple SD Gothic Neo |
| 수식 · 기울임 글자 | New Computer Modern Math · New Computer Modern(Typst에 들어 있음) | — |

- `make_explain.py`가 `typst fonts`로 이 컴퓨터에 있는 글꼴만 골라 `--input`으로 넘기므로 「없는 글꼴」 경고가 나지 않는다.
- 명조와 고딕 목록을 서로 뒤에 이어 붙인다. 고딕에 없는 ㉠ ⓐ ⇌ ∝ 같은 기호는 명조에서, 명조에 없는 ₂ ₃는 고딕에서 찾는다.
- `fonts/`의 명조에는 **한자가 없다**(용량 때문에 뺌). 한자는 한글(한컴오피스)이 깔린 윈도우의 함초롬바탕이나 윈도우 기본 바탕 · 맑은 고딕에서 나온다. 글꼴이 하나도 없으면 네모로 나온다.
- `fonts/`(약 13MB):
  - `NotoSerifKRStatic-Regular.ttf` — Noto Serif KR(가변 글꼴, 판 2.003)에서 굵기 400을 고정하고 한자(CJK 통합 한자)를 빼고, 설치된 가변 Noto Serif KR과 겹치지 않게 이름을 「Noto Serif KR Static」으로 바꾼 것. SIL Open Font License 1.1(`OFL-NotoSerifKR.txt`). 가변 글꼴을 그대로 쓰면 Typst가 가장 가는 굵기(ExtraLight)로 찍어서 고정 굵기로 바꿨다.
  - `Pretendard-Regular.otf` · `Pretendard-Bold.otf` — 원본 그대로. SIL Open Font License 1.1, 예약 글꼴 이름 「Pretendard」(`OFL-Pretendard.txt`).
  - 두 글꼴 모두 OFL이라 저장소에 함께 배포해도 되고, 문서(PDF)에 넣어 쓰는 데 제한이 없다. 글꼴 파일만 따로 팔 수는 없다.
- Noto 글꼴을 다시 만들 때(fontTools 필요, 도구 실행에는 필요 없음): `fontTools.varLib.instancer`로 `wght=400` 고정 → `fontTools.subset`으로 U+3400–9FFF · U+F900–FAFF · U+20000 이상을 빼고 모든 OpenType 기능 유지 → name 표 1 · 4 · 6 · 16을 「Noto Serif KR Static」으로.

## 서식(templates/)

| 파일 | 뜻 |
|---|---|
| `common.typ` | 글꼴 · 선 · 〈보기〉 상자 · 선지 칸 나누기 · 자료 블록(표 · 그림 · 상자 · 대화 · 수식 · 나란히) · 문항 모양 · 해설 본문 · 채점 기준 표 |
| `explain.typ` | 정답과 해설 |
| `review.typ` | 문항 검토 용지 |
| `check.typ` | 점검표 |

`make_explain.py`는 임시 폴더에 서식과 `data.typ`(exam.json을 바꾼 것), 그림 사본을 두고 `typst compile --root <임시 폴더> --font-path fonts`로 만든다. 서식을 고치면 세 PDF에 함께 반영된다.

## 알려진 한계

- 수식 변환은 시험 문항에 흔한 LaTeX만 다룬다(행렬 · 정렬 환경 없음). 모르는 명령은 글자로 넣고 알린다.
- 검토 용지 ② 칸은 Typst로 다시 그린 문항이라 한글(HWPX) 시험지와 줄바꿈 · 그림 크기가 조금 다를 수 있다. 칸보다 길면 55%까지 줄여 넣는다.
- 선지 칸 나누기(5 · 3 · 2 · 1칸)는 글자 수로만 정한다.
