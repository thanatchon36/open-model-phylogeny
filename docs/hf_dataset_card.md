---
pretty_name: "Phylogenetics of Open Models: Hugging Face lineage graph"
license: cc-by-4.0
language: [en]
tags: [hugging-face, model-lineage, phylogenetics, graph, software-ecosystems, metadata, ml-supply-chain]
size_categories: [1M<n<10M]
configs:
  - config_name: nodes
    data_files: data/processed/nodes_conn.parquet
    default: true
  - config_name: edges
    data_files: data/processed/edges_conn.parquet
  - config_name: layout_radial
    data_files: data/processed/layout_radial.parquet
  - config_name: raw_nodes
    data_files: data/raw/nodes.parquet
  - config_name: raw_edges
    data_files: data/raw/edges.parquet
---

# Phylogenetics of Open Models: Hugging Face lineage graph

All data behind the working draft *Phylogenetics of Open Models: Structure, Hybridisation, Tempo and Speciation in the
Hugging Face Lineage Graph* (Thanatchon Chongmankhong, November 2026): the pinned raw snapshot of 2026-11-05, the
cleaned lineage graph, the radial layout and every result table.

- **Paper (web):** https://thanatchon36.github.io/open-model-phylogeny/paper/
- **Paper (PDF):** https://github.com/thanatchon36/open-model-phylogeny/raw/main/paper/paper.pdf
- **Code:** https://github.com/thanatchon36/open-model-phylogeny (`make data && make all` regenerates everything here
  from `data/raw`)

The upstream release `data-latest` is rebuilt nightly, so this copy is the way to reproduce the paper exactly. This is
a working draft: the license-drift analysis of the original plan is not done, because the snapshot has no per-model
license tags.

## Files

| Path | Rows | What |
|---|---|---|
| `data/raw/nodes.parquet` | 3,213,044 | One row per Hub model, including one duplicate row that the build drops |
| `data/raw/edges.parquet` | 952,659 | Declared child-to-parent links with their relation |
| `data/raw/mft.zip` | | Source archive of the Open Model Family Tree repository; `dist/parents.json` supplies the family keys |
| `data/raw/SHA256SUMS` | | Checksums of the three files above |
| `data/processed/nodes_conn.parquet` | 965,292 | Models that declare a parent or have a child, with graph measures |
| `data/processed/edges_conn.parquet` | 952,646 | Cleaned edges, after the cycle-breaking rules |
| `data/processed/layout_radial.parquet` | 965,292 | Radial chronogram coordinates, row-aligned with `nodes_conn` |
| `data/processed/wedges.csv` | | Angle range of each super-family in the layout |
| `results/results.json`, `results/build.json` | | Every statistic in the paper, and the cleaning counts |
| `results/tables/*.csv` | | The tables behind the figures |

The processed files were regenerated from the raw snapshot with `make build layout`. Doing so reproduced the committed
`results/build.json` apart from its timing field.

## Main columns

`nodes_conn`: `id`, `author`, `pipeline`, `library`, `created`, `downloads` (last 30 days), `downloads_all`, `likes`,
`ghost` (a parent that no longer resolves to a public model), `n_par`, `n_kid`, `primary` (row index of the primary
parent), `root` (row index of the root), `depth` (generation in the primary tree), `ldepth` (longest path through
merges), `hyb` (hybrid depth), `sub` (primary subtree size), `rel` (relation code), `family` (upstream family key),
`fam_size`, `upstream_total`, `topo` (topological order).

`edges_conn`: `p` and `c` (row indices of parent and child in `nodes_conn`), `rel` (relation code), `primary` (whether
this is the child's primary-parent edge).

Relation codes in `rel`: 0 finetune, 1 adapter, 2 quantized, 3 merge, 4 unknown, and -1 in `nodes_conn` for a model with
no primary parent. In `nodes_conn`, `primary` is also -1 for such a model.

`raw_nodes`: `id`, `author`, `created`, `modified`, `downloads`, `downloads_all`, `likes`, `pipeline`, `library`,
`trending`. `raw_edges`: `child`, `parent`, `relation`.

## Caveats

- Lineage is declared, not observed, so all counts are lower bounds, and relation labels may be inferred or wrong.
- Creation time is not release time. The creation date 2022-03-02 is a Hub backfill and is treated as left-censored.
- Unresolved parents are kept as ghost nodes. Family keys rely on a naming heuristic.
- Download counts follow the Hub's counting conventions and include automated traffic.

## Ethics

Only public Hub metadata is used. The `author` column holds public account names exactly as the Hub and the upstream
release publish them; the paper reports individual accounts anonymously, and we ask that users of this data do the same.
Nothing here is a judgement about any model or uploader, and nothing here is legal advice.

## Attribution and licenses

Lineage data: [Open Model Family Tree](https://github.com/h9-tec/model-family-tree) by h9-tec, CC BY 4.0, derived from
the [`cfahlgren1/hub-stats`](https://huggingface.co/datasets/cfahlgren1/hub-stats) dump of the Hub's `/api/models`
(Apache-2.0). The derived files here are shared under CC BY 4.0. The source code inside `data/raw/mft.zip` keeps its
upstream MIT license, included in the archive.

## Citation

```bibtex
@unpublished{chongmankhong2026phylogeny,
  author = {Chongmankhong, Thanatchon},
  title  = {Phylogenetics of Open Models: Structure, Hybridisation, Tempo and Speciation in the {Hugging Face} Lineage Graph},
  note   = {Working draft and code repository},
  year   = {2026},
  url    = {https://github.com/thanatchon36/open-model-phylogeny}
}
```
