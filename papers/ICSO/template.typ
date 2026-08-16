// SPIE proceedings style table: horizontal rules only (top / header / bottom),
// no vertical lines. First `columns.len()` positional args are the header row.
#let spie-table(columns: (), inset: 4pt, ..cells) = {
  let cells = cells.pos()
  let ncol = if type(columns) == int { columns } else { columns.len() }
  table(
    columns: columns,
    inset: inset,
    stroke: none,
    table.hline(stroke: 1pt),
    table.header(..cells.slice(0, ncol)),
    table.hline(stroke: 0.5pt),
    ..cells.slice(ncol),
    table.hline(stroke: 1pt),
  )
}

#let spie-paper(
  title: [],
  authors: [],
  affiliations: [],
  corresponding-email: none,
  abstract: [],
  keywords: (),
  body,
) = {
  set document(title: title)
  set page(
    paper: "a4",
    margin: (
      left: 1.93cm,
      right: 1.93cm,
      top: 2.54cm,
      bottom: 4.94cm,
    ),
    header: none,
    footer: none,
    numbering: none,
  )

  // SPIE A4 proceedings style: one column, Times-like 10 pt body text.
  set text(
    font: ("Times New Roman", "Yu Mincho", "MS Mincho"),
    size: 10pt,
    lang: "ja",
  )
  set par(justify: true, leading: 12pt, spacing: 0.65em)
  set enum(numbering: "1.")
  set list(indent: 1.2em)
  set math.equation(numbering: "(1)")
  set figure.caption(separator: [. ])
  show figure.where(kind: table): set figure.caption(position: top)
  show figure.caption: it => {
    block(inset: (left: 2.2em, right: 0pt))[
      #set text(size: 9pt)
      #set par(justify: true, leading: 11pt)
      #it
    ]
  }

  set heading(numbering: "1.")
  show heading.where(level: 1): it => {
    v(1.2em)
    align(center)[#text(size: 11pt, weight: "bold")[#it]]
    v(0.6em)
  }
  show heading.where(level: 2): it => {
    v(0.8em)
    align(left)[#text(size: 10pt, weight: "bold")[#it]]
    v(0.3em)
  }

  align(center)[#text(size: 16pt, weight: "bold")[#title]]
  v(0.8em)

  align(center)[#text(size: 12pt)[#authors]]
  v(0.35em)

  align(center)[#text(size: 10pt)[#affiliations]]

  if corresponding-email != none {
    v(0.6em)
    align(left)[#text(size: 9pt)[\*#corresponding-email]]
  }

  v(1.2em)
  align(center)[#text(size: 11pt, weight: "bold")[ABSTRACT]]
  v(0.4em)
  block[
    #set text(size: 10pt)
    #set par(justify: true, leading: 12pt)
    #abstract
  ]

  if keywords.len() > 0 {
    v(0.6em)
    align(left)[
      #text(weight: "bold")[Keywords:] #keywords.join(", ")
    ]
  }

  v(1.2em)
  body
}
