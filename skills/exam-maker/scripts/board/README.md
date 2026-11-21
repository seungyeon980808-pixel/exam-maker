# 코멘트판(시안)

```
python make_board.py <작업폴더>/exam.json                         # → <작업폴더>/시안/index.html
python make_board.py exam.json --prev 판/exam_v0.1.json            # 비교 시안: 바뀐 문항은 「이전 판 | 바뀐 판」, 바뀐 곳 노란 칠
node comment_server.cjs <작업폴더>/시안 8883                        # 코멘트 자동 저장 서버(이 컴퓨터 안에서만)
```
브라우저로 `http://127.0.0.1:8883` 을 연다.

- 왼쪽: 시험지 모양 문항 / 오른쪽 위: 정답·출제 의도·근거·핵심 개념·해설·출처·격리 풀이 검토 / 그 아래: 코멘트 칸(전체·발문·자료·보기·선지·해설·그림).
- 적으면 0.6초 뒤 `시안/comments_<판>.json` 에 저장된다(바로 앞 저장본은 `.bak.json`). Claude는 이 파일을 읽어 반영한다.
- 서버 없이 파일로 열면 이 브라우저에만 저장된다. 그때는 위쪽 「코멘트 전체 복사」 단추로 Claude 대화창에 붙여 넣는다.
- `review.json`(격리 풀이 요약)이 exam.json 옆에 있으면 「검토」 칸에 같이 보인다.
- `node test_server.cjs <시안폴더>` : 서버 자체 검사.
