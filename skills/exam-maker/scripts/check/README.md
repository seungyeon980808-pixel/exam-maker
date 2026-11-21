# 격리 풀이 검사

판마다 GPT와 Claude가 **정답·해설을 모른 채, 서로 모르게** 문항을 풀어 정답 유일성·출제 오류 시비·범위를 찾는다.

```
python make_check_set.py exam.json 검사/v0.2 --textbook 자료/교과서.txt --curriculum 자료/교육과정.txt --level "고등학교 2학년"
python run_check.py 검사/v0.2 --kind 둘다 --jobs 4
python summarize.py exam.json 검사/v0.2
```

- `make_check_set.py` : 문항지 `Q01.md`…(정답·해설·출처 없음), 그림 `Q01_그림1.png`, `교과서.txt`, `교육과정.txt`, 지침 2개
  - `지침_정답.md` : 직접 풀이 + 시비 점검 A~H + 시비 목록(심각도) + 「최종 답: ③」
  - `지침_범위.md` : 교과서만으로 풀리는지(풀이 요소 대조표), 학년 수준, 교육과정(성취기준 해설·적용 시 고려 사항) 대조
- `run_check.py` : GPT는 `codex exec`(읽기 전용, 그림 첨부)로 바로 돌린다. Claude 몫은 `결과/claude_할일_<종류>_Qnn.txt` 로 남긴다 →
  Claude Code 세션이 **문항마다 하위 에이전트를 하나씩** 띄워 그 파일 내용 그대로 풀게 하고, 답을 `결과/claude_<종류>_Qnn.md` 로 저장하게 한다
  (에이전트는 격리 세트 폴더만 읽는다. exam.json·GPT 결과·다른 문항 결과는 보여 주지 않는다).
  명령줄 `claude`가 로그인되어 있으면 `--claude-cli` 로 바로 돌릴 수도 있다.
- `summarize.py` : 「최종 답」을 정답과 맞대고 시비 높음·중간 개수, 범위 판정을 모아 `요약.md` 와 `review.json`(코멘트판 검토 칸)을 만든다.

교육과정 원문 자르기: `python ../curriculum/cut_curriculum.py 생명과학 자료/교육과정.txt --grep 핵형,염색체`
