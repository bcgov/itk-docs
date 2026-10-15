from __future__ import annotations

import re


TAB_MARKER = re.compile(r'^=== "([^"]+)"\s*$')
ADMONITION_MARKER = re.compile(r"^(!!!|\?\?\?\+?)\s+(.+?)\s*$")
ADMONITION_TITLE = re.compile(r'\s+"([^"]*)"\s*$')
EXTERNAL_LINK_PATTERN = re.compile(
    r"(?<!!)"  # do not match images
    r"\[([^\]]+)\]\((https?://[^)\s]+)(\s+\"[^\"]*\")?\)"
)


def mark_external_links(markdown: str, icon_path: str) -> str:
    """Embed a pop-out icon inside absolute http(s) Markdown link labels."""

    def replace(match: re.Match[str]) -> str:
        label, target, title = match.group(1), match.group(2), match.group(3) or ""
        if icon_path in label or "external-link.svg" in label:
            return match.group(0)
        icon = f"![]({icon_path}){{width=0.7em}}"
        return f"[{label}{icon}]({target}{title})"

    return EXTERNAL_LINK_PATTERN.sub(replace, markdown)


def _trim_blank_edges(lines: list[str]) -> list[str]:
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _quote_block(label: str, content: list[str]) -> list[str]:
    quoted = [f"> **{label}**", ">"]
    for line in content:
        quoted.append(f"> {line}" if line else ">")
    quoted.append("")
    return quoted


def _admonition_label(body: str) -> str:
    title_match = ADMONITION_TITLE.search(body)
    if title_match:
        title = title_match.group(1)
        type_and_modifiers = body[: title_match.start()].strip()
    else:
        title = None
        type_and_modifiers = body.strip()

    admonition_type = type_and_modifiers.split(maxsplit=1)[0]
    type_label = admonition_type.replace("-", " ").replace("_", " ").title()
    if title is None or title == "":
        return type_label
    return f"{type_label}: {title}"


def _collect_indented_block(lines: list[str], start: int) -> tuple[list[str], int]:
    content: list[str] = []
    index = start
    while index < len(lines):
        current = lines[index]
        if current == "" or current.startswith("    "):
            content.append(current[4:] if current.startswith("    ") else current)
            index += 1
            continue
        break
    return _trim_blank_edges(content), index


def expand_admonitions(markdown: str) -> str:
    """Convert admonition/details blocks into labeled blockquotes for PDF."""
    lines = markdown.splitlines()
    result: list[str] = []
    index = 0
    in_fence = False

    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            result.append(line)
            index += 1
            continue
        if in_fence or not (marker := ADMONITION_MARKER.match(line)):
            result.append(line)
            index += 1
            continue

        label = _admonition_label(marker.group(2))
        content, index = _collect_indented_block(lines, index + 1)
        # Expand nested admonitions/tabs that may appear inside this block.
        nested = prepare_pdf_markdown("\n".join(content)).rstrip("\n").splitlines()
        result.extend(_quote_block(label, nested))

    return "\n".join(result).rstrip() + "\n"


def expand_tabs(markdown: str) -> str:
    """Convert pymdownx.tabbed groups into labeled blockquotes for PDF."""
    lines = markdown.splitlines()
    result: list[str] = []
    index = 0
    in_fence = False

    while index < len(lines):
        line = lines[index]
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            result.append(line)
            index += 1
            continue
        if in_fence or not TAB_MARKER.match(line):
            result.append(line)
            index += 1
            continue

        while index < len(lines) and (marker := TAB_MARKER.match(lines[index])):
            label = marker.group(1)
            content, index = _collect_indented_block(lines, index + 1)
            nested = prepare_pdf_markdown("\n".join(content)).rstrip("\n").splitlines()
            result.extend(_quote_block(label, nested))

    return "\n".join(result).rstrip() + "\n"


TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
TABLE_TOTAL_DASHES = 100
TABLE_MAX_COLUMN_WEIGHT = 60
MINIMAL_SEPARATOR_DASHES = 6


def _split_row(line: str) -> list[str]:
    row = line.strip()
    row = row.removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", row)]


def _plain_length(cell: str) -> int:
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    return len(re.sub(r"[*_`]", "", cell))


def _table_separator(header: list[str], separator: list[str], body: list[list[str]]) -> str:
    """Rebuild a pipe-table separator: no centering, widths proportional to content.

    Pandoc derives relative column widths from the dash counts, so the minimal
    separators that converted tables carry (``:--:``, ``----``) give meaningless
    widths. Tables whose authors spaced the dashes out deliberately keep their
    widths and are only un-centered.
    """
    columns = len(separator)
    dash_counts = [cell.strip(":").count("-") for cell in separator]
    right_aligned = [cell.endswith(":") and not cell.startswith(":") for cell in separator]

    if columns > 1 and max(dash_counts) <= MINIMAL_SEPARATOR_DASHES:
        rows = [header, *body]
        weights = []
        for index in range(columns):
            cells = [row[index] for row in rows if index < len(row)]
            longest = max((_plain_length(cell) for cell in cells), default=1)
            longest_word = max(
                (len(word) for cell in cells for word in re.sub(r"[*_`]", "", cell).split()),
                default=1,
            )
            weights.append(max(min(longest, TABLE_MAX_COLUMN_WEIGHT), longest_word + 2, 4))
        total = sum(weights)
        dash_counts = [max(3, round(weight / total * TABLE_TOTAL_DASHES)) for weight in weights]

    cells = [
        f"{'-' * dashes}:" if right else f":{'-' * dashes}"
        for dashes, right in zip(dash_counts, right_aligned)
    ]
    return "|" + "|".join(cells) + "|"


def normalize_pdf_tables(markdown: str) -> str:
    lines = markdown.splitlines()
    in_fence = False
    index = 0
    while index < len(lines):
        stripped = lines[index].lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
        if (
            not in_fence
            and "|" in lines[index]
            and index + 1 < len(lines)
            and "-" in lines[index + 1]
            and TABLE_SEPARATOR_PATTERN.match(lines[index + 1])
            and len(_split_row(lines[index])) == len(_split_row(lines[index + 1]))
        ):
            end = index + 2
            while end < len(lines) and lines[end].strip() and "|" in lines[end]:
                end += 1
            header = _split_row(lines[index])
            separator = _split_row(lines[index + 1])
            body = [_split_row(line) for line in lines[index + 2 : end]]
            lines[index + 1] = _table_separator(header, separator, body)
            index = end
            continue
        index += 1
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else "")


TOC_ENTRY_PATTERN = re.compile(r"^(?P<indent> *)- (?:\[(?P<title>.+)\]\(#(?P<anchor>[^)]+)\)|(?P<label>.+))$")


def _typst_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def typst_contents(markdown: str) -> str:
    """Render the Contents list as Typst (see toc-source in pdf-codeblocks.typ).

    Gives the PDF its own TOC layout without touching ordinary lists, and keeps
    each source's entries together on one page.
    """
    lines = markdown.splitlines()
    try:
        start = lines.index("## Contents") + 1
    except ValueError:
        return markdown
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("#")),
        len(lines),
    )

    sources: list[tuple[str, str, list[str]]] = []
    for line in lines[start:end]:
        if not line.strip():
            continue
        match = TOC_ENTRY_PATTERN.match(line)
        if not match:
            return markdown
        depth = len(match.group("indent")) // 4
        if depth == 0:
            sources.append((match.group("title"), match.group("anchor"), []))
        elif match.group("anchor"):
            sources[-1][2].append(
                f"(depth: {depth}, title: {_typst_string(match.group('title'))}, "
                f"target: label({_typst_string(match.group('anchor'))}))"
            )
        else:
            sources[-1][2].append(
                f"(depth: {depth}, title: {_typst_string(match.group('label'))}, target: none)"
            )

    block = ["", "```{=typst}"]
    for title, anchor, entries in sources:
        block.append(
            f"#toc-source({_typst_string(title)}, label({_typst_string(anchor)}), ("
        )
        block.extend(f"  {entry}," for entry in entries)
        block.append("))")
    block.extend(["```", ""])
    return "\n".join([*lines[:start], *block, *lines[end:]]) + "\n"


def prepare_pdf_markdown(markdown: str, external_link_icon: str | None = None) -> str:
    """Apply PDF-oriented Markdown transforms for Material syntax."""
    transformed = normalize_pdf_tables(
        expand_tabs(expand_admonitions(typst_contents(markdown)))
    )
    if external_link_icon:
        transformed = mark_external_links(transformed, external_link_icon)
    return transformed
