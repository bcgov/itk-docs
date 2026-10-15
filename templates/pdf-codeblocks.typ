// Light gray background for fenced code blocks in PDF output.
#show raw.where(block: true): it => {
  block(
    width: 100%,
    fill: luma(245),
    inset: 8pt,
    radius: 3pt,
    stroke: luma(220),
    it,
  )
}

// Style hyperlinks like conventional web links (except in the contents).
#let toc-active = state("toc-active", false)
#show link: it => context {
  if toc-active.get() { it } else { underline(text(fill: rgb("#0563C1"), it)) }
}

// Tables: left-aligned, ragged-right, no hyphenation for narrow cells.
#show table: set par(justify: false)
#show table: set text(hyphenate: false)

// Contents: one unbreakable block per source. Source titles in caps, nav
// groups as small grey labels, pages with a single marker, dot leaders and
// page numbers.
#let toc-leader = box(width: 1fr, repeat(gap: 0.3em, text(fill: luma(185))[.]))
#let toc-page(target) = context {
  let found = query(target)
  if found.len() > 0 { str(counter(page).at(found.first().location()).first()) }
}
#let toc-step = 1.1em
#let toc-row(entry) = {
  let indent = (entry.depth - 1) * toc-step
  if entry.target == none {
    (
      grid.cell(colspan: 2, inset: (top: 0.35em), pad(left: indent, text(
        size: 0.78em,
        weight: "semibold",
        tracking: 0.05em,
        fill: luma(95),
        upper(entry.title),
      ))),
    )
  } else {
    (
      grid(
        columns: (indent, 0.9em, 1fr),
        [],
        text(fill: luma(160))[–],
        [#link(entry.target, entry.title)#toc-leader],
      ),
      align(right + bottom, link(entry.target, toc-page(entry.target))),
    )
  }
}
#let toc-source(title, target, entries) = {
  toc-active.update(true)
  block(breakable: false, above: 1.3em, below: 0em, width: 100%, grid(
    columns: (1fr, 2em),
    column-gutter: 0.3em,
    row-gutter: 0.42em,
    link(target, [#text(weight: "bold", tracking: 0.06em, upper(title))#toc-leader]),
    align(right + bottom, text(weight: "bold", link(target, toc-page(target)))),
    ..entries.map(toc-row).flatten(),
  ))
  toc-active.update(false)
}
