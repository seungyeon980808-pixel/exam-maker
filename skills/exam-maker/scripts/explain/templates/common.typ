// 공용 서식: 글꼴 · 선 · 문항 모양(검토 용지 ② 칸) · 해설 본문.
// 정답과 해설 · 문항 검토 용지 · 점검표가 함께 쓴다. 색은 쓰지 않는다(평가원식 흑백).
// 글꼴 목록은 make_explain.py가 이 컴퓨터에 있는 것만 골라 sys.inputs로 넘긴다.

#let split-fonts(key, fallback) = {
  let v = sys.inputs.at(key, default: "")
  if v == "" { fallback } else { v.split("|") }
}
// 본문 명조(문항 · 해설 글) / 고딕(번호 · 제목 · 표 머리 · 안내)
#let serif = split-fonts("serif", ("Noto Serif KR Static", "HCR Batang", "Batang", "Pretendard"))
#let sans = split-fonts("sans", ("Pretendard", "HCR Dotum", "Malgun Gothic", "Noto Serif KR Static"))
#let math-font = "New Computer Modern Math"   // typst에 들어 있는 글꼴
#let latin-italic = "New Computer Modern"      // 기울임 글자(변수 m, v …)

#let hair = 0.35pt + black   // 가는 선
#let rule = 0.8pt + black    // 굵은 선
#let gray = luma(90)         // 작은 안내 글씨만
#let marks = ("①", "②", "③", "④", "⑤")
#let gana = ("ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ")
#let num2(k) = if k < 10 { "0" + str(k) } else { str(k) }

// 글 안의 <i> <b>: make_explain.py가 이 두 함수로 바꿔 넣는다
#let it(body) = text(font: (latin-italic,) + serif, style: "italic", body)
#let bf(body) = text(font: sans, weight: "bold", body)

// 문항 · 해설 글 규칙
#let exam-text(size: 9.4pt, body) = {
  set text(font: serif, size: size, lang: "ko", region: "kr")
  set par(spacing: 0.72em, justify: false, leading: 0.72em)
  show regex("[^\s]*[\u{AC00}-\u{D7A3}/][^\s]*"): box   // 한글이 든 어절은 어절 단위로만 줄바꿈
  show math.equation.where(block: false): it => it + sym.wj   // 수식 바로 뒤에서 줄이 갈리지 않게
  show math.equation: set text(font: (math-font,) + serif)   // 수식 안 한글은 명조로
  show math.equation.where(block: false): set text(top-edge: "bounds", bottom-edge: "bounds")   // 분수 같은 높은 수식이 윗줄 · 아랫줄과 겹치지 않게
  show math.frac: it => math.display(it)   // 분수는 크게
  body
}

// ── 자료 블록
#let data-table(head, rows, size: 1em) = {
  let all = if head.len() > 0 { (head,) + rows } else { rows }
  let n = all.at(0).len()
  let last = all.len() - 1
  align(center, table(
    columns: (auto,) * n,
    stroke: (x, y) => (top: if y == 0 { rule } else { hair }, bottom: if y == last { rule } else { none },
      left: if x > 0 { hair } else { none }),
    inset: (x: 2.4mm, y: 3.6pt), align: center + horizon,
    ..all.enumerate().map(((y, row)) => row.map(c =>
      if y == 0 and head.len() > 0 { text(font: sans, size: 0.88 * size, c) } else { text(size: size, c) })).flatten(),
  ))
}
#let caption(c) = if c != none { align(center, text(font: sans, size: 0.8em, c)) }

#let render-block(b) = {
  let t = b.type
  if t == "text" { b.body }
  else if t == "fig" {
    if b.src == none { align(center, box(width: 60%, height: 18mm, stroke: hair, align(center + horizon, text(font: sans, size: 0.8em, fill: gray)[그림 파일 없음: #b.missing]))) }
    else { align(center, image(b.src, width: b.width * 100%)) }
    caption(b.caption)
  }
  else if t == "table" { data-table(b.head, b.rows); caption(b.caption) }
  else if t == "box" {
    block(width: 100%, inset: (x: 3mm, y: 2.6mm), stroke: hair,
      stack(spacing: 2mm, ..b.blocks.map(render-block)))
  }
  else if t == "talk" {
    block(width: 100%, inset: (x: 3mm, y: 2.6mm), stroke: hair,
      grid(columns: (auto, 1fr), column-gutter: 2.4mm, row-gutter: 2mm,
        ..b.lines.map(((who, said)) => (text(font: sans, weight: "bold", size: 0.9em, who), said)).flatten()))
  }
  else if t == "eq" { align(center, b.body) }
  else if t == "pair" {
    grid(columns: (1fr,) * b.blocks.len(), column-gutter: 4mm, align: center + bottom,
      ..b.blocks.map(render-block))
  }
}

// ── 〈보기〉: 위 선 가운데에 글자를 얹는 평가원 방식
#let bogi-box(items) = block(width: 100%, inset: (top: 4mm, bottom: 3.2mm, x: 3.6mm), stroke: hair)[
  #place(top + center, dy: -4mm - 0.55em, box(fill: white, inset: (x: 1.8mm), text(font: sans, size: 0.82em, tracking: 2pt)[〈보기〉]))
  #grid(columns: (5.2mm, 1fr), row-gutter: 2.4mm,
    ..items.enumerate().map(((i, t)) => ([#gana.at(i).], t)).flatten())
]

// ── 선지: 글자 수로 한 줄 5칸 · 3칸 · 2칸 · 1칸
#let choices-grid(cs, lens) = {
  if cs.len() == 0 { return [] }
  let k = if lens.any(n => n > 14) { 1 } else if lens.any(n => n > 8) { 2 } else if lens.any(n => n > 6) { 3 } else { cs.len() }
  let item(i) = box[#marks.at(i)#h(1.2mm)#cs.at(i)]
  if k == 1 { grid(columns: (5.2mm, 1fr), row-gutter: 1.8mm, ..range(cs.len()).map(i => (marks.at(i), cs.at(i))).flatten()) }
  else { grid(columns: (1fr,) * k, row-gutter: 2.2mm, ..range(cs.len()).map(item)) }
}

// ── 문항 하나(시험지 모양): 「1.」 번호 뒤에 발문, 둘째 줄부터 번호만큼 들여 씀
#let problem(q, gap: 2.4mm) = {
  let p = q.problem
  let nw = if q.no < 10 { 5.2mm } else { 7mm }
  block(width: 100%, breakable: false)[
    #set par(hanging-indent: nw)
    #box(width: nw, text(font: sans, weight: "bold", size: 1.06em)[#q.no.])#p.lead#if p.ask == none [ #text(font: sans, size: 0.84em)[\[#q.pts;점\]]]
    #set par(hanging-indent: 0mm)
    #block(inset: (left: nw), width: 100%, above: gap)[
      #for b in p.blocks { block(above: gap, below: gap, width: 100%, render-block(b)) }
      #if p.ask != none [#block(above: gap, below: 0mm)[#p.ask #text(font: sans, size: 0.84em)[\[#q.pts;점\]]]]
      #if p.bogi.len() > 0 { v(gap + 1mm); bogi-box(p.bogi) }
      #if p.choices.len() > 0 { v(gap + 0.4mm); choices-grid(p.choices, p.choice-lens) }
    ]
  ]
}

// 칸 너비에 맞추되 너무 길면 줄여서 넣는다
#let fit(body, max-h) = layout(size => {
  let h = measure(block(width: size.width, body)).height
  if h <= max-h { body } else {
    let f = calc.max(max-h / h, 0.55)
    scale(x: f * 100%, y: f * 100%, reflow: true, origin: top + left, block(width: size.width / f, body))
  }
})

// ── 해설 본문: 〈보기〉별 · 선지별 문단, 둘째 줄부터 들여 씀. 서술형은 모범 답안 + 채점 기준 표
#let rubric-table(q, size: 1em) = table(columns: (14mm, 1fr), stroke: hair, inset: (x: 2mm, y: 1.6mm), align: (center + horizon, left + horizon),
  table.cell(fill: luma(235), text(font: sans, weight: "bold", size: 0.82 * size)[점수]),
  table.cell(fill: luma(235), text(font: sans, weight: "bold", size: 0.82 * size)[채점 기준]),
  ..q.rubric.map(((s, t)) => (text(font: sans, size: 0.9 * size, s + "점"), t)).flatten())

#let explain-body(q, gap: 2mm) = {
  set par(hanging-indent: 4.6mm)
  if q.kind == "서술형" {
    block(below: gap)[#bf[모범 답안] #q.ans-text]
    if q.rubric.len() > 0 { set par(hanging-indent: 0mm); block(below: gap, rubric-table(q)) }
  }
  for p in q.bogi-sol { block(below: gap, p) }
  if q.choice-line != none { block(below: gap, q.choice-line) }
  for p in q.choice-sol { block(below: gap, p) }
  if q.kind != "서술형" and q.bogi-sol.len() == 0 and q.choice-sol.len() == 0 { text(fill: gray)[(해설 없음)] }
}
