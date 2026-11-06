# open-model-phylogeny

**The Tree of Open Models**: a phylogenetic atlas of the Hugging Face Hub. It covers 965,292 models that declare a parent or have a child, linked by 952,646 lineage edges (fine-tunes, adapters, quantisations and merges), from a snapshot taken on 2026-11-05.

![The Tree of Open Models: radius is creation date, angle is lineage](assets/hero_preview.jpg)

## Findings (working draft)

- **Concentration.** The top 1% of roots hold 74.8% of connected models (Gini 0.88). 95.1% of derivatives never have offspring.
- **Hybridisation.** 39.0% of merged parent pairs are relatives, against 2.1% under random re-pairing.
- **Tempo.** For heavily reused bases, the median time to the first fine-tune fell from 35.1 days (2023 H2 releases) to 2.8 days (2026 H1).
- **Attention.** The top 1% of uploaders produce 52.5% of derivatives, and the top 1% of derivatives receive 95.9% of their downloads.
- **Speciation.** 18.7% of parent-to-child links change task group, led by fill-mask to text classification.

Paper draft: [`paper/paper.pdf`](paper/paper.pdf). Every number in it is generated from `results/results.json` and listed in its numbers ledger.

| Coral (Qwen2.5) | Speciation | Hybridisation |
| --- | --- | --- |
| ![](paper/figs/f2.jpg) | ![](paper/figs/f3.jpg) | ![](paper/figs/f5.jpg) |

![Cambrian explosion](paper/figs/f4.jpg)

## Quick start

```bash
pip install -r requirements.txt   # Python 3.12, plus pdflatex for the paper
make data                         # verify the pinned snapshot (fetches the latest one if files are missing)
make all                          # build -> analyze -> figures -> paper (about 10 min, ~2.5 GB RAM peak)
```

The raw snapshot is not committed (`data/raw` is git-ignored). Its checksums are in `data/raw/SHA256SUMS`; keep the files from the original archive, or attach them to a GitHub release, to reproduce the paper exactly.

## Repository

- `src/`: pipeline (`build`, `analyze`, `layout`), figure scripts and `make_macros.py`.
- `results/`: `results.json` (single source of truth) and the tables behind the figures.
- `paper/`: LaTeX source, generated macros and tables, figures used by the paper.
- `docs/`: original research plan (`MASTER_PROMPT.md`, Thai) and `RESEARCH_LOG.md`.
- `CLAUDE.md`: instructions and next steps for Claude Code.

## Status and next steps

The license-drift analysis of the original plan is pending: the snapshot has no per-model license tags. See `CLAUDE.md` for the plan, followed by citation checks and an interactive explorer.

## Data and licenses

Lineage data: [Open Model Family Tree](https://github.com/h9-tec/model-family-tree) by h9-tec, CC BY 4.0, derived from the `cfahlgren1/hub-stats` dump of Hugging Face Hub metadata (Apache-2.0). Code license: to be chosen by the author.
