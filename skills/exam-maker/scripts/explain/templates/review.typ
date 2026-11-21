// 문항 검토 용지: 한 문항에 한 쪽, 검정 한 가지.
// 위: 문항 정보 표 + 성취기준 원문
// 1줄: ① 참고 자료 | ② 출제 문항(시험지 모양, 그림 포함)
// 2줄: ③ 출제 의도 · 근거 | ④ 문항 해설
// 3줄: ⑤ 체크리스트(작게) · AI에게 요청 | ⑥ 메모(남는 높이 전부)
// 다 쓴 뒤 스캔하면 쪽마다 오른쪽 위 「문항 번호 · 판」으로 어느 문항인지 찾는다.
#import "common.typ": *

#let box-o = box(width: 3.2mm, height: 3.2mm, stroke: 0.5pt, baseline: 15%)
#let checks = ("정답이 하나뿐인가", "성취기준과 맞는가", "교육과정 밖 개념은 없는가", "자료(그림·표·그래프)가 정확한가",
  "발문과 조건이 분명한가", "선지가 고르게 매력적인가", "오탈자·표기")
#let blank(w) = box(width: w, height: 3mm, stroke: (bottom: hair))
#let ai-requests = ([숫자 · 조건만 바꾸기], [더 어렵게], [더 쉽게], [발문 · 조건 분명하게],
  [〈보기〉 #blank(5mm) 다시 짓기], [오답 선지 더 매력적으로], [정답 번호 → #blank(5mm)], [교과서 용어 · 기호로],
  [그림을 다른 원본으로], [다른 자료로 교체], [해설 더 자세히], [배점 → #blank(5mm)점])
#let sec(t, note: none) = block(below: 1.8mm, width: 100%)[
  #text(weight: "bold", size: 9.4pt, t)#if note != none { h(2mm) + text(size: 7.6pt, fill: gray, note) }
  #v(-1.2mm)#line(length: 100%, stroke: hair)]
#let cell(body) = block(width: 100%, inset: 3mm, body)
#let cell-fill(body) = block(width: 100%, height: 100%, inset: 3mm, body)
#let th(t) = text(size: 7.4pt, weight: "bold", t)

#let ref-image(path, max-h: 82mm) = layout(size => {
  let h = measure(image(path, width: size.width)).height
  if h <= max-h { image(path, width: size.width) } else { align(center, image(path, height: max-h)) }
})

#let review(meta, q) = {
  // ── 맨 위: 문서 이름 · 검토자 / 문항 번호(스캔 때 찾는 표지)
  grid(columns: (1fr, auto), align: bottom,
    [#text(weight: "bold", size: 15pt)[#meta.subject 문항 검토 용지]#h(3mm)#text(fill: gray)[#meta.school · #meta.term #meta.exam · 판 #meta.version]
     #v(1.4mm)
     #text(fill: gray)[검토자 #box(width: 30mm, stroke: (bottom: hair), height: 3mm)#h(5mm)검토일 #box(width: 26mm, stroke: (bottom: hair), height: 3mm)]],
    box(stroke: 1.2pt, inset: (x: 4mm, y: 2.4mm), text(weight: "bold", size: 20pt)[문항 #num2(q.no)]))
  v(2mm)
  line(length: 100%, stroke: 1.4pt)
  v(1.6mm)
  // ── 문항 정보 표
  table(columns: (9mm, 1.5fr, 1.6fr, 1.8fr, 0.8fr, 1fr, 1.1fr, 0.8fr, 0.8fr), stroke: hair, inset: (x: 2mm, y: 1.8mm), align: center + horizon,
    th[번호], th[성취기준], th[단원], th[출처], th[난이도], th[답 형식], th[자료], th[정답], th[배점],
    text(weight: "bold", size: 10pt, str(q.no)), q.std, q.unit, text(size: 7.6pt, q.src), q.level, q.form, q.data,
    if q.kind == "서술형" [서술형] else { text(size: 10pt, q.ans) }, [#q.pts;점],
    table.cell(colspan: 9, align: left, inset: (x: 2.4mm, y: 2mm))[#th[성취기준 원문]#h(2mm)#q.std #if q.std-text != none { q.std-text } else { text(fill: gray)[(원문은 check.json의 standards에 넣으면 나온다)] }])
  v(1mm)
  block(width: 100%, height: 1fr, stroke: rule, grid(columns: (1fr, 1fr), rows: (auto, auto, 1fr),
    stroke: (x, y) => (left: if x > 0 { hair } else { none }, top: if y > 0 { hair } else { none }),
    // 1줄: ① 참고 자료 | ② 출제 문항
    cell[
      #sec([① 참고 자료], note: q.ref-label)
      #if q.ref != none { ref-image(q.ref) } else [
        #set text(size: 8.2pt)
        #text(weight: "bold")[출처]#h(1.6mm)#q.src
        #if meta.textbook != "" [#v(0.8mm)#text(weight: "bold")[교과서]#h(1.6mm)#meta.textbook]
        #v(1.2mm)
        #text(size: 7.6pt, fill: gray)[참고한 원본(교과서 쪽 · 기출)을 붙이거나 적는다.]
        #v(14mm)]],
    cell[
      #sec([② 출제 문항], note: [판 #meta.version · #q.no;번])
      #exam-text(size: 8.8pt, fit(problem(q, gap: 2mm), if meta.paper == "a4" { 82mm } else { 118mm }))],
    // 2줄: ③ 출제 의도 · 근거 | ④ 문항 해설
    cell[
      #sec([③ 출제 의도 · 근거], note: [#q.std · #q.level])
      #set text(size: 8.2pt)
      #text(weight: "bold")[의도] #q.intent
      #v(0.8mm)
      #text(weight: "bold")[근거] #q.basis
      #if q.concepts.len() > 0 [
        #v(0.8mm)
        #text(weight: "bold")[핵심 개념]
        #set list(marker: [–], body-indent: 1.6mm, spacing: 1.2mm)
        #for k in q.concepts [- #k
        ]]
      #if q.check != none [
        #v(1mm)
        #text(size: 7.8pt)[#text(weight: "bold")[점검] Claude #q.check.claude · GPT #q.check.gpt → #text(weight: "bold", q.check.final)]
        #if q.check.fix != none [#linebreak()#text(size: 7.8pt)[#text(weight: "bold")[고친 점] #q.check.fix]]]],
    cell[
      #sec([④ 문항 해설], note: if q.kind == "서술형" [서술형 · #q.pts;점] else [정답 #q.ans])
      #exam-text(size: 8.6pt)[#set par(leading: 0.7em); #explain-body(q, gap: 2.2mm)]],
    // 3줄: ⑤ 체크리스트(작게) · AI에게 요청 | ⑥ 메모(세로로 길게)
    cell-fill[
      #sec([⑤ 체크리스트], note: [○ 적절 · △ 수정 · × 교체])
      #table(columns: (1fr, 5.2mm, 5.2mm, 5.2mm), stroke: hair, inset: (x: 1.6mm, y: 0.85mm),
        align: (left + horizon, center + horizon, center + horizon, center + horizon),
        [], th[○], th[△], th[×],
        ..checks.map(c => (text(size: 7.8pt, c), [], [], [])).flatten())
      #v(1.4mm)
      #set text(size: 7.8pt)
      #grid(columns: (auto, 1fr), column-gutter: 2mm, row-gutter: 1.8mm,
        [예상 난이도], [#box-o 쉬움#h(1.4mm)#box-o 보통#h(1.4mm)#box-o 어려움],
        [최종 판정], [#box-o 그대로#h(1.4mm)#box-o 수정 후#h(1.4mm)#box-o 교체])
      #v(1.4mm)
      #sec([AI에게 요청], note: [체크하면 스캔 뒤 그대로 반영])
      #grid(columns: (1fr, 1fr), column-gutter: 2mm, row-gutter: 1.1mm, ..ai-requests.map(t => [#box-o #t]))],
    cell-fill[
      #sec([⑥ 메모], note: [고칠 곳 · 의견 · AI에게 할 말])
      #block(width: 100%, height: 1fr, layout(size => {
        let k = calc.floor(size.height / 8.5mm)   // 제목 아래 남는 높이에 들어가는 만큼만
        for i in range(calc.max(k, 0)) { place(top + left, dy: (i + 1) * 8.5mm - 0.3pt, line(length: 100%, stroke: 0.3pt + luma(170))) }
      }))],
  ))
}

#let doc(meta, items) = {
  set document(title: meta.title + " 문항 검토 용지")
  set text(font: sans, size: 8.6pt, lang: "ko", region: "kr")
  set par(justify: false, leading: 0.62em)
  show math.equation: set text(font: (math-font,) + serif)   // 수식 안 한글은 명조로
  show math.equation.where(block: false): set text(top-edge: "bounds", bottom-edge: "bounds")   // 분수 같은 높은 수식이 윗줄 · 아랫줄과 겹치지 않게
  set page(paper: meta.paper, margin: (x: 14mm, top: 12mm, bottom: 12mm),
    footer: context grid(columns: (1fr, auto),
      text(size: 7.6pt, fill: gray)[#meta.school · #meta.term #meta.exam · #meta.subject · 검토 용지 판 #meta.version],
      text(size: 8pt, weight: "bold")[#counter(page).display() / #counter(page).final().first()]))
  for (i, q) in items.enumerate() {
    if i > 0 { pagebreak() }
    review(meta, q)
  }
}
