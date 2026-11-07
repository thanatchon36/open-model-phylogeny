#!/usr/bin/env python3
"""Build the web reader docs/paper/ from paper/paper.tex (same text and numbers as the PDF).

pandoc renders the LaTeX source with paper/reader.html: masthead, abstract, a results strip, contents, numbered
sections, references and appendices. Macros come from paper/macros.tex, which make_macros.py generates from
results/results.json, so this script types no numbers. Sections, tables and figures are numbered here in document
order, the way LaTeX numbers them, and every cross-reference and citation becomes a link. paper.pdf and the figures
are copied next to the page; GitHub Pages serves docs/ at https://thanatchon36.github.io/open-model-phylogeny/.
The script stops on anything it cannot resolve. Requires pandoc on PATH.

Usage: python scripts/build_web_paper.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUT = ROOT / "docs" / "paper"

REPO_URL = "https://github.com/thanatchon36/open-model-phylogeny"
PAPER_URL = "https://thanatchon36.github.io/open-model-phylogeny/paper/"
DATA_URL = "https://huggingface.co/datasets/thanatchon36/open-model-phylogeny"
DOI = "10.5281/zenodo.24029159"
TITLE = "Phylogenetics of Open Models"
SUBTITLE = "Structure, Hybridisation, Tempo and Speciation in the Hugging Face Lineage Graph"
AUTHOR = "Thanatchon Chongmankhong"
DATE = "Working draft, 6 November 2026"


def braced(tex: str, start: int) -> tuple[str, int]:
    """The contents of the {...} group opening at tex[start], and the index just past its closing brace."""
    if tex[start] != "{":
        raise ValueError(f"expected a brace group at: {tex[start:start + 40]!r}")
    depth = 0
    for i in range(start, len(tex)):
        if tex[i] == "{" and tex[i - 1] != "\\":
            depth += 1
        elif tex[i] == "}" and tex[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return tex[start + 1 : i], i + 1
    raise ValueError(f"unbalanced group at: {tex[start:start + 40]!r}")


def read_macros() -> dict[str, str]:
    """name -> LaTeX value. \\xspace is dropped: the regex expansion below keeps the source's own spaces."""
    macros = {}
    for line in (PAPER / "macros.tex").read_text(encoding="utf-8").splitlines():
        if line.startswith(r"\newcommand{"):
            name, end = braced(line, len(r"\newcommand"))
            value, _ = braced(line, end)
            macros[name.lstrip("\\")] = value.replace(r"\xspace", "")
    if not macros:
        raise RuntimeError("no macros found in paper/macros.tex")
    return macros


def expand_macros(tex: str, macros: dict[str, str]) -> str:
    return re.sub(r"\\([A-Za-z]+)", lambda m: macros.get(m.group(1), m.group(0)), tex)


def plain(value: str) -> str:
    """A macro value as plain text, for the results strip."""
    text = value.replace("{,}", ",").replace(r"\%", "%")
    if "\\" in text or "$" in text:
        raise ValueError(f"macro value is not plain text: {value!r}")
    return text


def rewrite_group_command(tex: str, command: str, render) -> str:
    """Replace every \\command{...}, whose argument may hold nested braces, by render(argument)."""
    out, pos = [], 0
    while (i := tex.find(command + "{", pos)) != -1:
        arg, end = braced(tex, i + len(command))
        out += [tex[pos:i], render(arg)]
        pos = end
    return "".join(out) + tex[pos:]


def simplify(tex: str) -> str:
    """Remove page-layout commands and reduce print-only constructs to forms pandoc reads correctly."""
    tex = re.sub(r"\\RQ(\d)", r"\\textbf{RQ\1}", tex)
    tex = re.sub(r"\\resizebox\{\\columnwidth\}\{!\}\{(\\input\{[^}]+\})\}", r"\1", tex)
    tex = re.sub(r"\{\\footnotesize\s*(\\input\{[^}]+\})\}", r"\1", tex)
    tex = re.sub(r"\\input\{([^}]+)\}", lambda m: (PAPER / f"{m.group(1)}.tex").read_text(encoding="utf-8"), tex)
    # The ledger is a longtable with print column specs; the browser scrolls instead.
    tex = re.sub(r"\\begin\{longtable\}\{.*\}\n", "\\\\begin{tabular}{lrl}\n", tex)
    tex = tex.replace(r"\end{longtable}", r"\end{tabular}").replace("\\endhead\n", "")
    tex = re.sub(r"\\begin\{(figure|table)\*?\}(?:\[[^]]*\])?", r"\\begin{\1}", tex)
    tex = re.sub(r"\\end\{(figure|table)\*?\}", r"\\end{\1}", tex)
    for pattern in (r"\\centering(?:\\small)?", r"\\onecolumn", r"^\\small$", r"\\setlength\{\\itemsep\}\{[^}]*\}"):
        tex = re.sub(pattern, "", tex, flags=re.MULTILINE)
    return tex


def link_citations(tex: str) -> str:
    """Number the bibliography in source order, as natbib's numbers mode does, and link every citation to it."""
    match = re.search(r"\\begin\{thebibliography\}\{\d+\}(.*?)\\end\{thebibliography\}", tex, re.DOTALL)
    if not match:
        raise ValueError("no thebibliography environment")
    items = re.findall(r"\\bibitem\[([^]]*)\]\{([^}]+)\}(.*)", match.group(1))
    numbers = {key: i + 1 for i, (_, key, _) in enumerate(items)}
    names = {key: re.sub(r"\(\d{4}\)$", "", label) for label, key, _ in items}

    def cite_link(key: str) -> str:
        if key not in numbers:
            raise ValueError(f"undefined citation: {key}")
        return rf"\href{{#ref-{key}}}{{{numbers[key]}}}"

    def numeric(arg: str) -> str:
        keys = sorted((k.strip() for k in arg.split(",")), key=lambda k: numbers.get(k, 0))
        return "[" + ", ".join(cite_link(k) for k in keys) + "]"

    def named(arg: str) -> str:
        return f"{names[arg]} [{cite_link(arg)}]" if arg in names else numeric(arg)

    entries = "\n\n".join(f"REFENTRY-{key}-{numbers[key]}-END {text.strip()}" for _, key, text in items)
    tex = tex[: match.start()] + "\\section*{References}\\label{references}\n\n" + entries + "\n\n" + tex[match.end() :]
    tex = rewrite_group_command(tex, r"\citep", numeric)
    return rewrite_group_command(tex, r"\citet", named)


def number_document(tex: str) -> tuple[str, dict[str, str]]:
    """Number sections and floats in document order, then turn every \\ref into a link."""
    labels: dict[str, str] = {}

    # pandoc ignores \appendix, so appendix sections get a label here and their letter in finish_html().
    head, appendix = tex.split(r"\appendix", 1)
    letters = iter("ABCDEFGH")

    def appendix_section(m: re.Match) -> str:
        letter = next(letters)
        labels[f"app:{letter}"] = letter
        return f"{m.group(0)}\\label{{app:{letter}}}"

    appendix = re.sub(r"\\section\{[^}]*\}", appendix_section, appendix)

    section, subsection = 0, 0
    for m in re.finditer(r"\\(section|subsection)(\*?)\{|\\label\{(sec:[^}]+)\}", head):
        if m.group(1) == "section" and not m.group(2):
            section, subsection = section + 1, 0
        elif m.group(1) == "subsection" and not m.group(2):
            subsection += 1
        elif m.group(3):
            labels[m.group(3)] = f"{section}.{subsection}" if subsection else str(section)
    tex = head + appendix

    counts = {"table": 0, "figure": 0}

    def number_float(m: re.Match) -> str:
        kind, block = m.group(1), m.group(0)
        counts[kind] += 1
        label = re.search(r"\\label\{([^}]+)\}", block)
        if not label:
            raise ValueError(f"unlabelled {kind}: {block[:80]!r}")
        labels[label.group(1)] = str(counts[kind])
        block = block.replace(label.group(0), "")
        tag = rf"\hypertarget{{{label.group(1)}}}{{\textbf{{{kind.capitalize()} {counts[kind]}.}}}} "
        return block.replace(r"\caption{", r"\caption{" + tag, 1)

    tex = re.sub(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", number_float, tex, flags=re.DOTALL)

    def link(m: re.Match) -> str:
        if m.group(1) not in labels:
            raise ValueError(f"undefined reference: {m.group(1)}")
        return rf"\href{{#{m.group(1)}}}{{{labels[m.group(1)]}}}"

    return re.sub(r"\\ref\{([^}]+)\}", link, tex), labels


def pandoc(tex: str, *args: str) -> str:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found; install pandoc to build the web reader")
    return subprocess.run(
        ["pandoc", "--from=latex", "--to=html5", "--mathml", "--wrap=none", *args],
        input=tex, capture_output=True, text=True, check=True, cwd=str(PAPER),
    ).stdout


def finish_html(page: str, labels: dict[str, str]) -> str:
    """Figures, tables and heading numbers: the things pandoc leaves in print form."""
    # Run-in \paragraph headings are unnumbered in the PDF.
    page = re.sub(r'(<h4\b[^>]*?)\sdata-number="[^"]*"([^>]*>)<span class="header-section-number">[^<]*</span>\s*',
                  r"\1\2", page)
    for label, letter in labels.items():
        if not label.startswith("app:"):
            continue
        page, headings = re.subn(rf'(<h1\b[^>]*id="{label}"[^>]*><span class="header-section-number">)[^<]*(</span>)',
                                 rf"\g<1>{letter}\2", page)
        page, entries = re.subn(rf'(<a href="#{label}"[^>]*><span class="toc-section-number">)[^<]*(</span>)',
                                rf"\g<1>{letter}\2", page)
        if (headings, entries) != (1, 1):
            raise ValueError(f"appendix {label}: {headings} headings, {entries} contents entries")

    def figure(m: re.Match) -> str:
        tag = re.sub(r'\s(?:style|width|height|alt)="[^"]*"', "", m.group(1))
        tag = tag.replace('src="figs/', 'src="figures/')
        caption = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
        alt = html.escape(re.sub(r"^Figure \d+\.\s*", "", caption).strip(), quote=True)
        return m.group(0).replace(m.group(1), tag.replace("<img ", f'<img loading="lazy" alt="{alt}" ', 1), 1)

    page = re.sub(r"<figure>\s*(<img\b[^>]*>)\s*<figcaption[^>]*>(.*?)</figcaption>", figure, page, flags=re.DOTALL)
    # The caption sits above the table, outside its sideways scroll, so it wraps at the text width.
    page = re.sub(r"<table\b[^>]*>\s*<caption>(.*?)</caption>(.*?)</table>",
                  r'<div class="tbl"><p class="tcap">\1</p><div class="tscroll"><table>\2</table></div></div>',
                  page, flags=re.DOTALL)
    # A table without a caption (the numbers ledger) still scrolls on its own.
    page = re.sub(r"(?<!<div class=\"tscroll\">)<table\b[^>]*>(.*?)</table>",
                  r'<div class="tscroll"><table>\1</table></div>', page, flags=re.DOTALL)
    page = re.sub(r"<colgroup>.*?</colgroup>\s*", "", page, flags=re.DOTALL)
    # pandoc makes a block of a \\hypertarget that opens a paragraph, so reference anchors are placed here.
    page = re.sub(r"<p>REFENTRY-(.+?)-(\d+)-END\s*", r'<p id="ref-\1">[\2] ', page)
    return page


def results_strip(m: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """(label, style, finding, detail), with every number read from the generated macros."""
    v = {name: plain(value) for name, value in m.items() if "\\" not in value.replace(r"\%", "") and "$" not in value}
    return [
        ("Structure", "ref", f"The top 1% of roots hold {v['pctTopOnePctRoots']} of connected models",
         f"Gini {v['giniFamily']} on family size; {v['pctLeaves']} of derivatives never have offspring"),
        ("Hybridisation", "ref", f"{v['pctRelated']} of merged parent pairs are relatives",
         f"against {v['pctNullRelated']} under random re-pairing of parents"),
        ("Tempo", "ref", f"First fine-tune: {v['rtFinetuneEarly']} days down to {v['rtFinetuneLate']} days",
         "median for heavily reused bases, 2023 H2 releases against 2026 H1 releases"),
        ("Attention", "ref", f"The top 1% of derivatives receive {v['pctTopDownloads']} of their downloads",
         f"and the top 1% of uploaders produce {v['pctTopUploaders']} of derivatives"),
        ("Speciation", "ref", f"{v['pctSpeciation']} of parent-to-child links change task group",
         "led by fill-mask to text classification"),
        ("License drift", "null", "Not analysed yet",
         "the snapshot has no per-model license tags; this analysis of the original plan is pending"),
    ]


def main() -> None:
    macros = read_macros()
    source = (PAPER / "paper.tex").read_text(encoding="utf-8")
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", source, re.DOTALL).group(1)
    body = source[source.index(r"\section{Introduction}") : source.index(r"\end{document}")]

    tex, labels = number_document(link_citations(simplify(expand_macros(body, macros))))

    meta = {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "author": [AUTHOR],
        "date": DATE,
        "pagetitle": TITLE,
        "description": "Working draft: a phylogenetic analysis of the Hugging Face Hub, built from the lineage that "
                       "models declare.",
    }
    with tempfile.TemporaryDirectory() as tmp:
        meta_file = Path(tmp) / "meta.json"
        meta_file.write_text(json.dumps(meta), encoding="utf-8")
        page = pandoc(tex, "--standalone", "--template=reader.html", "--number-sections", "--toc", "--toc-depth=1",
                      f"--metadata-file={meta_file}")
    page = finish_html(page, labels)

    items = "\n".join(
        f'<li class="r r-{style}"><span class="r-id">{html.escape(label)}</span>'
        f'<span class="r-text">{html.escape(finding)}<small>{html.escape(detail)}</small></span></li>'
        for label, style, finding, detail in results_strip(macros)
    )
    actions = (
        '<li><a href="paper.pdf">Download PDF</a></li>'
        f'<li><a href="{REPO_URL}">Code and replication</a></li>'
        f'<li><a href="{DATA_URL}">Data (Hugging Face)</a></li>'
        f'<li><a href="https://doi.org/{DOI}">Zenodo archive</a></li>'
    )
    bib = (
        "@unpublished{chongmankhong2026phylogeny,\n"
        "  author = {Chongmankhong, Thanatchon},\n"
        f"  title  = {{{TITLE}: {SUBTITLE.replace('Hugging Face', '{Hugging Face}')}}},\n"
        "  note   = {Working draft and code repository},\n"
        "  year   = {2026},\n"
        f"  doi    = {{{DOI}}},\n"
        f"  url    = {{{PAPER_URL}}}\n"
        "}"
    )
    colophon = (
        "<p>Lineage data: Open Model Family Tree by h9-tec (CC BY 4.0), derived from the cfahlgren1/hub-stats dump of "
        "Hugging Face Hub metadata (Apache-2.0).</p>"
        "<p>Rendered from <code>paper/paper.tex</code> by <code>scripts/build_web_paper.py</code>. Every number comes "
        "from <code>results/results.json</code>. The PDF is authoritative.</p>"
    )
    for marker, value in (
        ("<!--ABSTRACT-->", pandoc(expand_macros(abstract, macros))),
        ("<!--ACTIONS-->", actions),
        ("<!--RESULTS-NOTE-->", "Headline numbers, read from the result files. Amber: results; grey: pending."),
        ("<!--RESULTS-->", items),
        ("<!--CITE-->", f"<h2>How to cite</h2><pre><code>{html.escape(bib)}</code></pre>"),
        ("<!--COLOPHON-->", colophon),
    ):
        if marker not in page:
            raise RuntimeError(f"reader.html lacks {marker}")
        page = page.replace(marker, value)

    # Thousands separators in macros are {,} for LaTeX; pandoc wraps the group in a span.
    page = page.replace("<span>,</span>", ",")

    leftovers = re.findall(r"\\[A-Za-z]+\{?", re.sub(r"<annotation.*?</annotation>|<code>.*?</code>", "", page, flags=re.DOTALL))
    if leftovers:
        raise RuntimeError(f"unresolved LaTeX in the page: {sorted(set(leftovers))}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    shutil.copyfile(PAPER / "paper.pdf", OUT / "paper.pdf")
    (OUT / "figures").mkdir(exist_ok=True)
    for name in sorted(set(re.findall(r'src="figures/([\w.-]+)"', page))):
        shutil.copyfile(PAPER / "figs" / name, OUT / "figures" / name)
    print(f"web reader -> {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
