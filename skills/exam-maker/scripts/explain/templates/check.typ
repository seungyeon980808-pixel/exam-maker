// 교과서 · 수준 · 교육과정 점검표(A4 가로): 기준 → 대조한 교육과정 원문 → 문항별 판정 표 → 요약
#import "common.typ": *

#let verdict(v) = if v == none or v == "" [—] else if v.starts-with("교체") { text(weight: "bold")[■ #v] } else if v.starts-with("고치면") { text(weight: "bold", v) } else { v }

#let doc(meta, check) = {
  set document(title: meta.title + " 교과서·수준·교육과정 점검표")
  set page(paper: "a4", flipped: true, margin: (x: 12mm, y: 12mm),
    footer: context align(center, text(font: sans, size: 7.5pt, fill: luma(90))[#meta.subject #meta.exam #check.version · 교과서·수준·교육과정 점검표 · #counter(page).display()]))
  set text(font: sans, size: 8.4pt, lang: "ko", region: "kr")
  set par(leading: 0.58em, justify: false)
  show math.equation: set text(font: (math-font,) + serif)   // 수식 안 한글은 명조로
  show math.equation.where(block: false): set text(top-edge: "bounds", bottom-edge: "bounds")   // 분수 같은 높은 수식이 윗줄 · 아랫줄과 겹치지 않게
  let hl = 0.4pt + luma(120)

  text(size: 14pt, weight: "bold")[#meta.title #check.version — 교과서·수준·교육과정 점검표]
  v(1mm)
  text(fill: luma(70), check.criteria)
  v(1.5mm)
  if check.rules.len() > 0 {
    block(stroke: hl, inset: 2.4mm, width: 100%)[#text(weight: "bold")[대조한 교육과정 원문] #v(0.6mm)
      #for (k, v) in check.rules [- #text(weight: "bold", k) 「#v」
      ]]
    v(2mm)
  }
  table(columns: (10mm, 16mm, 16mm, 17mm, 1fr, 0.75fr, 1fr, 1fr), stroke: hl, inset: (x: 1.5mm, y: 1.4mm),
    align: (center + horizon,) * 4 + (left + top,) * 4,
    table.header([*번호*], [*Claude*], [*GPT*], [*종합*], [*교과서 대조*], [*수준*], [*교육과정*], [*고친 점*]),
    ..check.rows.map(r => ([*#r.no*], verdict(r.claude), verdict(r.gpt), verdict(r.final), r.textbook, r.level, r.curriculum, r.fix)).flatten())
  v(2mm)
  text(size: 8pt, check.summary)
}
