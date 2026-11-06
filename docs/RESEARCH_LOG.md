# Research log

## Phase 0 - environment and data
- Sandbox: 1 CPU, 3.9 GB RAM; huggingface.co does not resolve, GitHub is reachable.
- Found a nightly full-Hub lineage snapshot on GitHub (h9-tec/model-family-tree, CC BY 4.0). Used it instead of a user-run collection script.
- The snapshot has no per-model license, tags, datasets or arXiv links. The only GitHub source with licenses (radar-huggingface-dataset) keeps open-licensed trending models only, which would bias any drift estimate.
- Decision: no synthetic data. RQ3/RQ4 (license drift) moved to future work; RQs re-scoped to structure, hybridisation, tempo, attention and speciation.

## Phase 1 - graph
- Dropped 1 duplicate node row; case-insensitive parent matching; unresolved parents kept as ghost nodes.
- Cycles broken (child older than parent first, then oldest node loses residual incoming edges).
- Primary parent: largest lineage, ties to the older parent. Backfilled creation date 2022-03-02 treated as left-censored.

## Phase 2-4 - analysis
- Power-law vs lognormal inconclusive; reported as heavy-tailed, not as a power law.
- Reaction-time trend re-tested on 2024+ cohorts to discount metadata adoption; trend holds except for merges.
- Robustness: first-listed primary parent, no quantised models, no top-1% uploaders, last 24 months.

## Phase 5 - figures
- F1 radial chronogram with a custom additive rasteriser; long tail dimmed and hybrid web softened after review.
- F2 coral: force-directed skeleton plus sunflower leaves; skeleton edges weighted up after review.
- F3 chord: tasks under 2.5% of the flow pooled to avoid label collisions.

## Phase 7 - paper
- LaTeX, two columns; all numbers via generated macros; [CITE] placeholders for related work that must be verified.

## Open items
- License drift: needs per-model license tags (run a collection script outside the sandbox, or allow huggingface.co).
- Fill [CITE] placeholders, author names and affiliation; check the target venue's template and page limit.
- Interactive explorer (Phase 6) not built in this round.

## Phase 8 - packaging (2026-11-06)
- Repository assembled for Claude Code (CLAUDE.md, Makefile, scripts/get_data.sh with SHA256SUMS, requirements.txt).
- Reproducibility check: re-running build.py and analyze.py from the raw snapshot reproduced results.json exactly (timing fields excluded).
- Research log kept here instead of a Claude Doc tab.

## Phase 9 - publication (2026-11-06)
- Research plan (`docs/MASTER_PROMPT.md`) translated to English; the Thai original stays in git history at `3d3dd1f`.
- All research data published on Hugging Face (`thanatchon36/open-model-phylogeny`, public, at the user's request): pinned raw snapshot, processed graph, layout, results. Raw hashes match `SHA256SUMS`. Re-running `make build layout` reproduced `results/build.json` apart from its timing field.
- `make data` now fetches from that dataset at a fixed revision, so a fresh clone can reproduce the paper; upstream `data-latest` is rebuilt nightly.
- Web reader added (`docs/paper/`, GitHub Pages from `main:/docs`), same format as the stablerun reader. It shows an author name, which `paper.tex` still leaves as a placeholder; pdflatex is not available locally, so the PDF was not rebuilt.
