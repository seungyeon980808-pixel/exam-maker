// 정답과 해설(교사용): 정답표(번호 · 정답 · 배점) → 문항마다 정답 · 문항 정보 · 출처 · 출제 의도 · 근거 · 핵심 개념 · 해설(두 단)
#import "common.typ": *

#let doc(meta, items) = {
  set document(title: meta.title + " 정답과 해설")
  set text(font: serif, lang: "ko", region: "kr")
  // 가운데 세로선: 첫 쪽은 해설 두 단이 시작하는 높이부터
  set page(paper: meta.paper, margin: (x: 18mm, top: 20mm, bottom: 20mm),
    background: context {
      let p = here().page()
      let starts = query(<cols-start>)
      let y0 = if starts.len() > 0 and starts.first().location().page() == p { starts.first().location().position().y } else if starts.len() > 0 and starts.first().location().page() > p { none } else { 20mm }
      if y0 != none { place(top + center, dy: y0, line(angle: 90deg, length: page.height - y0 - 22mm, stroke: hair)) }
    },
    footer: context align(center, text(font: sans, size: 8pt)[#meta.subject #meta.exam 정답과 해설 · #counter(page).display() · 판 #meta.version]))
  show: exam-text.with(size: 9.4pt)

  // ── 머리
  grid(columns: (1fr, auto), align: bottom,
    text(font: sans, size: 8.4pt)[#meta.school#h(2mm)|#h(2mm)#meta.term #meta.exam],
    text(font: sans, size: 8.4pt)[교사용 · 배부 금지])
  v(1.6mm)
  line(length: 100%, stroke: 1.6pt)
  v(4mm)
  align(center, text(font: sans, weight: "bold", size: 20pt)[#meta.heading 정답과 해설])
  if meta.subtitle != "" { v(1mm); align(center, text(font: sans, size: 9pt, fill: gray, meta.subtitle)) }
  v(4mm)
  line(length: 100%, stroke: rule)
  v(0.7mm)
  line(length: 100%, stroke: hair)
  v(4mm)

  // ── 정답표: 12문항씩 한 줄
  {
    let per = 12
    set text(font: sans)
    for c in range(calc.ceil(items.len() / per)) {
      let qs = items.slice(c * per, calc.min(items.len(), (c + 1) * per))
      let pad = (none,) * (per - qs.len())
      table(columns: (14mm,) + (1fr,) * per, stroke: hair, inset: (y: 2.2mm), align: center + horizon,
        table.cell(fill: luma(235))[#text(size: 8pt, weight: "bold")[번호]], ..qs.map(q => table.cell(fill: luma(235), text(weight: "bold", size: 9pt, str(q.no)))), ..pad,
        text(size: 8pt, weight: "bold")[정답], ..qs.map(q => if q.kind == "서술형" { text(size: 7.6pt)[서술형] } else { text(font: serif, size: 11pt, q.ans) }), ..pad,
        text(size: 8pt, weight: "bold")[배점], ..qs.map(q => text(size: 8pt, q.pts)), ..pad)
      v(2mm)
    }
    align(right, text(size: 8pt)[총 #items.len();문항 · #meta.total;점])
  }
  v(4mm)

  // ── 문항별 해설(두 단)
  [#metadata("cols") <cols-start>]
  columns(2, gutter: 12mm)[
    #for q in items {
      block(breakable: true, below: 7mm, width: 100%)[
        #block(sticky: true, width: 100%)[
          #grid(columns: (auto, 1fr), column-gutter: 2mm, align: horizon,
            text(font: sans, weight: "bold", size: 11pt)[#q.no.],
            [#text(font: sans, weight: "bold", size: 10pt)[#if q.kind == "서술형" [서술형] else [정답 #q.ans]]#h(2mm)#text(font: sans, size: 7.6pt, fill: gray)[#q.std · #q.unit · #q.level · #q.form · #q.pts;점]])
          #v(0.6mm)
          #line(length: 100%, stroke: hair)
          #v(0.4mm)
          #text(font: sans, size: 7.6pt, fill: gray)[출처: #q.src]]
        #v(1.2mm)
        #block(breakable: false, width: 100%, inset: (x: 2.4mm, y: 2mm), stroke: hair)[
          #set text(font: sans, size: 8.2pt)
          #set par(leading: 0.62em)
          #text(weight: "bold")[출제 의도]#h(1.6mm)#q.intent
          #v(0.8mm)
          #text(weight: "bold")[출제 근거]#h(1.6mm)#q.basis
          #if q.concepts.len() > 0 [
            #v(0.8mm)
            #text(weight: "bold")[핵심 개념]
            #set list(marker: [•], body-indent: 1.4mm, spacing: 1.1mm)
            #for k in q.concepts [- #k
            ]]]
        #v(1.6mm)
        #text(font: sans, weight: "bold", size: 8.6pt)[해설]
        #v(0.6mm)
        #explain-body(q, gap: 2mm)
      ]
    }
    #if meta.textbook != "" [
      #v(2mm)
      #line(length: 100%, stroke: hair)
      #text(font: sans, size: 7.2pt, fill: gray)[교과서: #meta.textbook]]
  ]
}
