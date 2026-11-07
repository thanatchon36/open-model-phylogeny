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
- Research plan (`docs/MASTER_PROMPT.md`) translated to English; the Thai original stays in git history at `c56d6b7`.
- All research data published on Hugging Face (`thanatchon36/open-model-phylogeny`, public, at the user's request): pinned raw snapshot, processed graph, layout, results. Raw hashes match `SHA256SUMS`. Re-running `make build layout` reproduced `results/build.json` apart from its timing field.
- `make data` now fetches from that dataset at a fixed revision, so a fresh clone can reproduce the paper; upstream `data-latest` is rebuilt nightly.
- Web reader added (`docs/paper/`, GitHub Pages from `main:/docs`), same format as the stablerun reader.

## Phase 10 - paper review (2026-11-06)
- Author set to Thanatchon Chongmankhong, name only, at the user's request. Appendix "References to find" removed.
- All `\todocite` placeholders replaced. New references were checked against Crossref, arXiv or the source: Hugging Face docs, Jiang 2023, Stalnaker 2026, Horwitz 2025, Laufer 2025, Longpre 2024, Jewitt 2025. Abstracts were read; for Laufer, the sections on scope and related work were also read in the full text. Longpre was checked by title and bibliographic record only.
- Method references written from memory were checked and found correct; pages were added to Seabold 2010. Csardi 2006 is confirmed by igraph's own citation file because Crossref does not index it.
- Claims corrected because the data did not support them:
  - "Merges overwhelmingly combine relatives" and "hybridises mostly within families": most parent pairs are outcrosses and 51.1% cross family keys.
  - "signature of automated, evolutionary merging pipelines": every deep model of the top account is a quantisation. New keys added to `results.json`, F5 annotation changed.
  - "increasingly automated": not measured, and deep-merge births fell in 2026.
  - "propagation code in place": only root and depth propagation exists, not license obligations.
  - "typically tutorial defaults": not measured; removed.
  - "faster every half-year": not monotone for every relation.
- Text 23.2% and robustness table 23.3%: both correct, with different family filters; the table caption now says so.
- `make analyze` re-run on Python 3.13 (macOS arm64): values differ only by floating-point noise, published macros unchanged apart from the 4 new ones.
- PDF built with Tectonic, because pdflatex is not installed locally. F5 regenerated with Inter 4.1.
- Related work to note: Laufer et al. already apply an evolutionary lens to Hub family trees and report license drift along fine-tuning edges, and Jewitt et al. study license drift from models to software. Any license-drift RQ needs to be scoped against them.

## Phase 11 - first release (2026-11-07)
- Code license set to MIT and commit author emails rewritten to the GitHub noreply address, both at the user's request. File contents were unchanged by the rewrite; `main` was force-pushed.
- Release v0.1.0 archived on Zenodo: version DOI `10.5281/zenodo.24029160`, concept DOI `10.5281/zenodo.24029159`. The DOI was added to the documents after the release, so the v0.1.0 archive itself does not contain it.

## Phase 12 - arXiv format (2026-11-07)
- Paper moved to an arXiv-style preprint layout at the user's request, matching stablerun: single column, 11pt, running head, keywords. Text and numbers unchanged.
- `paper/make_arxiv.sh` builds the upload bundle. It is compile-checked with Tectonic (XeTeX-based); pdfLaTeX itself is not installed here, so arXiv's own compile is the final check.
- F6 panel (c) retitled to match the corrected text ("faster every half-year" is not monotone for every relation).

## Phase 13 - LinkedIn post and poster (2026-11-07)
- `docs/linkedin_post.md` (English, Thai and short versions, first-comment links, alt text) and `scripts/make_linkedin_poster.py` (4:5 poster from the F1 render and `results.json`, with fit checks that fail the build on overflowing text). Every number in the post was checked against the PDF text.
- The poster cuts the disc out of the F1 render and removes the figure's own title and legend by position and colour, so F1 did not have to be re-rendered.
