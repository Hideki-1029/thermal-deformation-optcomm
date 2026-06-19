#let phantom-paragraph() = {
  set text(size: 11pt)
  let a = par(box())
  a
  context v(-0.8 * measure(2 * a).width)
}

#let project(
  id: "",
  title-ja: "",
  title-en: "",
  abstract: [],
  authors: (),
  affiliations: (),
  keywords: (),
  n-columns: 2,
  body,
) = {
  // General settings
  set document(author: authors.map(a => a.name-ja), title: title-ja)
  // Prioritize YuMincho because MS Mincho does not support bold.
  set text(font: ("Times New Roman", "Yu Mincho", "YuMincho", "MS Mincho"), lang: "ja")
  set page(paper: "a4", margin: (x: 23mm, y: 25mm))

  // Heading settings
  set heading(numbering: "1.1.")
  show heading: it => {
    // Workaround for the limitation of Typst.
    // See https://github.com/typst/typst/issues/311#issuecomment-2023038611
    {
      set text(size: 9.5pt, weight: "bold")
      set block(spacing: 0.65em)
      {
        // Add a vertical space before the heading, if not the first heading.
        let selector = selector(heading).before(here())
        let level = counter(selector)
        // level.display()
        if level.display() != "1" and it.level == 1 {
          v(9.5pt)
        }
      }
      it
    }
    phantom-paragraph()
  }

  // Section reference settings
  show ref: it => {
    let el = it.element
    if el != none and el.func() == heading {
      context {
        let heading_counts = counter(heading).at(it.element.location())
        if el.depth == 1 {
          // 章
          [第#heading_counts.at(0)章]
          // counts
        } else if el.depth == 2 {
          // 節
          [第#heading_counts.at(0).#heading_counts.at(1)節]
        } else if el.depth == 3 {
          // 項
          [第#heading_counts.at(0).#heading_counts.at(1).#heading_counts.at(2)項]
        } else {
          it
        }
      }
    } else {
      it
    }
  }

  // Paragraph settings
  set par(spacing: 0.65em)

  // Equation settings
  set math.equation(numbering: "(1)")

  // Figure settings
  show figure.where(kind: table): set figure.caption(position: top)
  set table(stroke: .5pt)
  set figure.caption(separator: [　])

  // Title (Japanese).
  align(center)[#text(size: 16pt)[#id\u{3000}#title-ja]]

  v(10.5pt)

  // Author information (Japanese).
  align(center)[
    #set text(size: 10.5pt)
    #authors.map(author => author.name-ja).join("，")
  ]

  v(10.5pt)

  v(1.2em)

  if abstract != [] {
    align(center)[
      #block(width: 88%)[
        #set text(size: 9pt)
        #set par(justify: true, leading: 13pt - 9pt + 0.65pt, first-line-indent: 0em)
        #align(center)[#text(weight: "bold")[Abstract]]
        #align(left)[#abstract]
      ]
    ]

    v(1.2em)
  }

  // Main body.
  set text(size: 9.5pt)
  // We need to subtract 9.5pt (the font size) from 15pt to get the correct line spacing.
  // 0.65pt in Typst is equivalent to no line spacing in MS Word.
  set par(justify: true, leading: 15pt - 9.5pt + 0.65pt, first-line-indent: 1em)
  if n-columns == 1 {
    body
  } else {
    show: columns.with(n-columns, gutter: 7mm)
    body
  }
}
