# CLAUDE.md — open-model-phylogeny

Research project: a phylogenetic analysis of the Hugging Face Hub, built from the lineage that
models declare (`base_model`: finetune / adapter / quantized / merge). Outputs: a reproducible
Python pipeline, publication-quality figures, and a LaTeX paper (`paper/paper.pdf`).

- Talk to the user in **Thai**. Write code, comments, commit messages and the paper in **English**.
- Original plan (Thai): `docs/MASTER_PROMPT.md`. What was actually done and why: `docs/RESEARCH_LOG.md`.

## Status (snapshot 2026-11-05)

Done in a claude.ai sandbox (no access to huggingface.co):
- Lineage DAG (`src/build.py`), analysis of five RQs (`src/analyze.py` -> `results/results.json`).
- Figures F1–F6 (`figures/`), paper draft with numbers ledger (`paper/`).

Not done:
- **License drift** — the core question of the original plan. The snapshot has no per-model license
  tags. Current RQs were re-scoped to: structure, hybridisation, tempo, attention, speciation.
- Interactive explorer; verified related-work citations; author names; venue template.

## Repository map

| Path | What |
| --- | --- |
| `src/common.py` | Super-family regexes, palettes, task groups, fonts |
| `src/build.py` | Raw parquet -> cleaned DAG: case-insensitive parents, ghosts, cycle breaking, primary tree, families |
| `src/analyze.py` | All statistics -> `results/results.json` + `results/tables/*.csv` |
| `src/layout.py` | Radial chronogram layout (angle = lineage, radius = creation date) |
| `src/fig_hero.py` | F1, custom additive rasteriser: `python fig_hero.py <px> <all\|collapsed>` |
| `src/fig_flows.py` | F3 speciation chord, F4 streamgraph |
| `src/fig_more.py` | F2 coral (Qwen2.5), F5 hybridisation web, F6 statistics panel |
| `src/make_macros.py` | `results.json` -> `paper/macros.tex`, tables, numbers ledger, `paper/figs/*.jpg` |
| `paper/paper.tex` | Paper source (all numbers are macros) |
| `scripts/get_data.sh` | Verify or fetch the pinned snapshot |

## Commands

```bash
make data      # verify data/raw against SHA256SUMS (fetches if missing)
make build     # ~20 s
make analyze   # ~90 s
make figures   # ~5 min; F1 at 5000 px peaks near 2.5 GB RAM (use 1600 for drafts)
make paper     # macros + pdflatex x2
make all       # build analyze figures paper
```

## Hard rules

1. Never fabricate data, numbers or citations. Mock data only inside tests, clearly labelled.
2. Every number in the paper comes from `results/results.json` through `src/make_macros.py`.
   Never type a number into `paper.tex`; add a macro (it then appears in the numbers ledger).
3. Related work stays as `\todocite{...}` until the reference is verified against the real source.
   The method references in the bibliography were written from memory: verify each one.
4. Keep the pinned snapshot. Upstream `data-latest` is rebuilt nightly, so a fresh download will not
   reproduce the paper. A refresh is a new study version: re-run everything, log it, bump the date.
5. Seeds are fixed (42). After any analysis change, re-run `make analyze` and diff `results.json`.
6. Ask the user before changing RQs, license rules, or publishing anything.
7. Ethics: public metadata only; anonymise individual uploaders in the paper (organisations' base
   models may be named); say "inconsistency", never "violation"; this is not legal advice.
8. Append decisions to `docs/RESEARCH_LOG.md` at the end of each phase.

## Data notes

- Source: `h9-tec/model-family-tree`, release `data-latest` (CC BY 4.0), derived from the
  `cfahlgren1/hub-stats` dump of `/api/models` (Apache-2.0). Attribute both in every output.
- `data/raw/` and `data/processed/` are git-ignored. Checksums: `data/raw/SHA256SUMS`.
- Creation date 2022-03-02 is a Hub backfill: treat as left-censored. Unresolved parents are ghost
  nodes. Cycle-breaking and primary-parent rules are documented in `src/build.py` and the paper.

## Next steps (priority order)

1. **License drift (original RQ3/RQ4)**, now possible with internet access:
   - Collect per-model tags (`license:*`, `dataset:*`, `arxiv:*`) and, for `license:other`,
     `license_name`/`license_link`. Prefer the `cfahlgren1/hub-stats` dataset at the revision
     closest to 2026-11-05 so tags match the lineage snapshot; otherwise use the Hub API with
     `HF_TOKEN` from the environment, backoff on HTTP 429, resumable. Save `data/raw/tags.parquet`.
   - Implement the taxonomy and obligation propagation exactly as specified in
     `docs/MASTER_PROMPT.md` (sections "License taxonomy…" and "การตรวจสอบความถูกต้อง (audit)"):
     classes P/C/R/V(f)/N/ND/U/O, topological propagation, introduced / inherited / healed,
     dataset tension, super-spreaders, exposure. Get the user's approval of the mapping table first.
   - Audit 300 stratified cases with README evidence; the user re-labels 50; report precision with
     Wilson CIs and Cohen's kappa; MIN_PRECISION = 0.8.
   - Add the results to the paper (new RQ, license chord, contagion small multiples, red overlay on F1).
2. Paper polish: verified references for every `\todocite`, author names, venue template and page
   limit (default target: MSR), AI-assistance disclosure per venue policy.
3. Interactive explorer: sigma.js + graphology, at most ~50k nodes, coordinates from
   `data/processed/layout_radial.parquet` (spec in the master prompt).
