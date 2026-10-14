# itk-docs

Assembles the Connected Services documentation (Building Trusted Digital
Services, Integration Toolkit, ADR, SDX, EFV, BC Data Catalogue) into one master
document, a PDF, and a GitHub Pages site. Published at
<https://bcgov.github.io/itk-docs/>.

Assembly is deterministic: source content is fetched, normalized, stitched
together with internal cross-links rewritten, and rendered. Nothing is rewritten
or edited. See [docs/poc-evaluation.md](docs/poc-evaluation.md) for background.

## Building locally

Requirements:

- [uv](https://docs.astral.sh/uv/) (installs the pinned Python 3.14 and dependencies)
- Google Chrome or Chromium (used to rasterize draw.io SVGs for the PDF; set
  `CHROME_PATH` if it isn't in a standard location)
- `git` and network access (sources are cloned from GitHub)

```bash
uv sync --locked
uv run python scripts/build.py
```

Pandoc and Typst are downloaded automatically into `.tools/`. Open `site/index.html`
to preview the result.

## What the build does

`scripts/build.py` runs these steps in order:

| Step                   | What it does                                                                                   |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| `install_pandoc.py`    | Downloads Pandoc into `.tools/`                                                                |
| `install_typst.py`     | Downloads Typst into `.tools/`                                                                 |
| `fetch_sources.py`     | Clones/copies each source in `sources.yaml` into `.work/`, writes `sources.lock.yaml`          |
| `normalize_sources.py` | Copies Markdown, converts Word docs to Markdown                                                |
| `assemble_master.py`   | Builds `dist/master.md` and `dist/validation-report.md`; rewrites links between sources        |
| `export_pdf.py`        | Renders `dist/master.pdf` with Pandoc + Typst                                                  |
| `build_site.py`        | Builds the MkDocs site into `site/` (strict mode: broken links fail the build)                 |

## Configuring sources

Sources are listed in [sources.yaml](sources.yaml). Each has a unique `id` and
`order` (the order they appear in the document).

| `type`        | Fields                                                                                                |
| ------------- | ----------------------------------------------------------------------------------------------------- |
| `git`         | `repository`, `ref`, `root`, `include` (globs), optional `navigation`, `assets`, `techdocs_component` |
| `docx`        | `location` (path to a Word file in `sources/`)                                                        |
| `placeholder` | optional `message` (default "Documentation coming soon."); renders a title and message only           |

- **`techdocs_component`** is the DevHub component name (the part after
  `/docs/default/component/`). It lets links between sources, including absolute
  developer.gov.bc.ca URLs, resolve to internal links instead of external ones.
- **`assets`** lists images (such as SVGs) a source's pages reference. A page
  that links to an image missing from this list fails the strict site build.

`sources.lock.yaml` is regenerated on every build and records the exact commits
used.

## Other files

- `templates/intro.md`: the intro text shown above the contents.
- `templates/pdf-codeblocks.typ`: Typst styling for the PDF (code blocks, links, tables).
- `mkdocs.yml`, `stylesheets/`: site configuration and styling.
- `docs/poc-evaluation.md`: the POC evaluation page.

## Checking the result

`dist/validation-report.md` (also on the site) lists links that couldn't be
resolved to a selected source file. Links to pages outside your `include` rules
show up here.

## Deployment

[`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs the same
build on every push to `main` and deploys `site/` to GitHub Pages. The build
outputs (`dist/`, `site/`, `.work/`) are regenerated in CI, so they don't need
to be committed.
