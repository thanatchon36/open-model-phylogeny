#!/usr/bin/env python3
"""Phase 1 - build the lineage DAG of Hugging Face models.

Input : data/raw/nodes.parquet, data/raw/edges.parquet  (Open Model Family Tree,
        h9-tec/model-family-tree, release `data-latest`, CC BY 4.0; derived from the
        cfahlgren1/hub-stats dump of the Hub /api/models, Apache-2.0)
        data/raw/mft/.../dist/parents.json            (family keys of every parent)
Output: data/processed/nodes_conn.parquet, edges_conn.parquet, results/build.json
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, RES = ROOT / "data/raw", ROOT / "data/processed", ROOT / "results"
PROC.mkdir(parents=True, exist_ok=True)
RES.mkdir(parents=True, exist_ok=True)
REL_NAMES = ["finetune", "adapter", "quantized", "merge", "unknown"]


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def kahn(n, par, chi):
    """Topological order of a graph given parent->child edge arrays. Returns order, processed mask."""
    indeg = np.bincount(chi, minlength=n).astype(np.int64)
    srt = np.argsort(par, kind="stable")
    kids = chi[srt]
    ptr = np.concatenate([[0], np.cumsum(np.bincount(par, minlength=n))])
    stack = list(np.flatnonzero(indeg == 0))
    order = []
    indeg_l = indeg.tolist()
    kids_l, ptr_l = kids.tolist(), ptr.tolist()
    while stack:
        v = stack.pop()
        order.append(v)
        for k in kids_l[ptr_l[v]:ptr_l[v + 1]]:
            indeg_l[k] -= 1
            if indeg_l[k] == 0:
                stack.append(k)
    done = np.zeros(n, bool)
    done[order] = True
    return np.array(order, dtype=np.int64), done


def main():
    t0 = time.time()
    out = {}
    # ------------------------------------------------------------------ load
    nodes = pq.read_table(RAW / "nodes.parquet", columns=[
        "id", "author", "created", "downloads", "downloads_all", "likes", "pipeline", "library"]).to_pandas()
    edges = pq.read_table(RAW / "edges.parquet").to_pandas()
    log("loaded", len(nodes), "nodes,", len(edges), "edges")
    out["duplicate_node_rows_dropped"] = int(nodes["id"].duplicated().sum())
    nodes = nodes.drop_duplicates("id", keep="first").reset_index(drop=True)
    out["n_models_hub"] = int(len(nodes))
    out["n_edges_raw"] = int(len(edges))
    assert nodes["id"].is_unique
    out["edges_by_relation_raw"] = {k: int(v) for k, v in edges["relation"].value_counts().items()}

    # backfilled creation dates (the Hub assigns one timestamp to all pre-2022-03 repos)
    cday = nodes["created"].dt.floor("D")
    top_day = cday.value_counts().head(1)
    out["backfill_date"] = str(top_day.index[0].date())
    out["backfill_date_n"] = int(top_day.iloc[0])

    # ------------------------------------------------------------------ resolve ids
    idx = pd.Index(nodes["id"])
    ci = idx.get_indexer(edges["child"])
    pi = idx.get_indexer(edges["parent"])
    out["edges_child_unresolved"] = int((ci < 0).sum())
    miss = pi < 0
    lower = nodes["id"].str.lower()
    lmap = pd.Series(np.arange(len(nodes)), index=lower.values)
    lmap = lmap[~lmap.index.duplicated(keep=False)]
    resc = edges.loc[miss, "parent"].str.lower().map(lmap)
    ok = resc.notna().values
    pi[np.flatnonzero(miss)[ok]] = resc.values[ok].astype(np.int64)
    out["parents_rescued_case_insensitive"] = int(ok.sum())
    miss = pi < 0
    ghosts = pd.Index(edges.loc[miss, "parent"].unique())
    out["ghost_parents"] = int(len(ghosts))
    pi[miss] = len(nodes) + ghosts.get_indexer(edges.loc[miss, "parent"])
    keep = ci >= 0
    ci, pi, rel_raw = ci[keep], pi[keep], edges["relation"].values[keep]
    # drop duplicate (child,parent) pairs after case rescue and self loops
    pair = pd.DataFrame({"c": ci, "p": pi, "r": rel_raw})
    pair = pair[pair.c != pair.p].drop_duplicates(["c", "p"], keep="first").reset_index(drop=True)
    log("resolved; ghosts:", len(ghosts))

    # ------------------------------------------------------------------ connected subgraph
    conn = np.unique(np.concatenate([pair.c.values, pair.p.values]))
    M = len(conn)
    remap = np.full(len(nodes) + len(ghosts), -1, np.int64)
    remap[conn] = np.arange(M)
    c = remap[pair.c.values]
    p = remap[pair.p.values]
    rel = pd.Categorical(pair.r.values, categories=REL_NAMES).codes.astype(np.int8)
    is_ghost = conn >= len(nodes)
    real = conn[~is_ghost]
    nd = pd.DataFrame({"id": np.empty(M, dtype=object)})
    nd.loc[~is_ghost, "id"] = nodes["id"].values[real]
    nd.loc[is_ghost, "id"] = ghosts.values[conn[is_ghost] - len(nodes)]
    for col in ["author", "pipeline", "library"]:
        v = np.full(M, None, dtype=object)
        v[~is_ghost] = nodes[col].values[real]
        nd[col] = v
    created = np.full(M, np.datetime64("NaT"), dtype="datetime64[us]")
    created[~is_ghost] = nodes["created"].values[real].astype("datetime64[us]")
    nd["created"] = created
    for col in ["downloads", "downloads_all", "likes"]:
        v = np.zeros(M, np.int64)
        v[~is_ghost] = nodes[col].values[real]
        nd[col] = v
    nd["ghost"] = is_ghost
    nd.loc[is_ghost, "author"] = nd.loc[is_ghost, "id"].str.split("/").str[0]
    del nodes
    out["n_connected"] = int(M)
    out["n_edges"] = int(len(c))
    log("connected nodes:", M, "edges:", len(c))

    # ------------------------------------------------------------------ cycles
    order, done = kahn(M, p, c)
    rem = ~done
    out["cycle_nodes_initial"] = int(rem.sum())
    keep_e = np.ones(len(c), bool)
    days = nd["created"].values.astype("datetime64[D]").astype("float64")
    it = 0
    while rem.any():
        it += 1
        inside = rem[p] & rem[c] & keep_e
        # rule 1: drop edges whose child is older than its parent
        older = inside & (days[c] < days[p])
        if older.any():
            keep_e &= ~older
        else:
            # rule 2: oldest node in the residual graph loses its incoming residual edges
            cand = np.flatnonzero(rem)
            v = cand[np.nanargmin(np.where(np.isnan(days[cand]), np.inf, days[cand]))]
            keep_e &= ~(inside & (c == v))
        sub = np.flatnonzero(keep_e & rem[p] & rem[c])
        sub_nodes = np.flatnonzero(rem)
        loc = np.full(M, -1, np.int64)
        loc[sub_nodes] = np.arange(len(sub_nodes))
        _, d2 = kahn(len(sub_nodes), loc[p[sub]], loc[c[sub]])
        rem2 = np.zeros(M, bool)
        rem2[sub_nodes[~d2]] = True
        rem = rem2
    out["cycle_edges_removed"] = int((~keep_e).sum())
    c, p, rel = c[keep_e], p[keep_e], rel[keep_e]
    order, done = kahn(M, p, c)
    assert done.all()
    log("cycles broken in", it, "iterations; edges removed:", out["cycle_edges_removed"])

    # ------------------------------------------------------------------ parents per child
    E = len(c)
    n_par = np.bincount(c, minlength=M)
    n_kid = np.bincount(p, minlength=M)
    srt_c = np.argsort(c, kind="stable")
    pptr = np.concatenate([[0], np.cumsum(n_par)])
    plist = p[srt_c]
    first_parent = np.full(M, -1, np.int64)
    has = n_par > 0
    first_parent[has] = plist[pptr[:-1][has]]
    order_l = order.tolist()

    def propagate(pp):
        root = np.arange(M)
        depth = np.zeros(M, np.int32)
        pp_l, root_l, depth_l = pp.tolist(), root.tolist(), depth.tolist()
        for v in order_l:
            q = pp_l[v]
            if q >= 0:
                root_l[v] = root_l[q]
                depth_l[v] = depth_l[q] + 1
        return np.array(root_l), np.array(depth_l, np.int32)

    root0, _ = propagate(first_parent)
    fam0 = np.bincount(root0, minlength=M)
    # primary parent: parent whose (provisional) family is largest; ties -> older parent
    primary = first_parent.copy()
    multi = np.flatnonzero(n_par >= 2)
    for v in multi:
        cand = plist[pptr[v]:pptr[v + 1]]
        fs = fam0[root0[cand]]
        dd = np.where(np.isnan(days[cand]), np.inf, days[cand])
        best = np.lexsort((dd, -fs))[0]
        primary[v] = cand[best]
    root, depth = propagate(primary)
    out["primary_changed_vs_first_listed"] = int((primary != first_parent).sum())

    # longest-path depth and hybrid depth over the full DAG (parents before children)
    ldepth = np.zeros(M, np.int32)
    hyb = np.zeros(M, np.int32)
    ld_l, hy_l = ldepth.tolist(), hyb.tolist()
    pl_l, pp_l, np_l = plist.tolist(), pptr.tolist(), n_par.tolist()
    for v in order_l:
        k = np_l[v]
        if k:
            ps = pl_l[pp_l[v]:pp_l[v + 1]]
            ld_l[v] = max(ld_l[q] for q in ps) + 1
            hy_l[v] = max(hy_l[q] for q in ps) + (1 if k >= 2 else 0)
    ldepth, hyb = np.array(ld_l, np.int32), np.array(hy_l, np.int32)

    # primary subtree sizes (each node counted once, inside its primary family)
    sub = np.ones(M, np.int64)
    sub_l = sub.tolist()
    prim_l = primary.tolist()
    for v in reversed(order_l):
        q = prim_l[v]
        if q >= 0:
            sub_l[q] += sub_l[v]
    sub = np.array(sub_l, np.int64)

    # relation of each child (relation on its primary edge)
    prim_edge = np.full(M, -1, np.int8)
    is_prim = np.zeros(E, bool)
    key = c.astype(np.int64) * (M + 1) + p
    pk = np.flatnonzero(primary >= 0)
    pos = pd.Index(key).get_indexer(pk.astype(np.int64) * (M + 1) + primary[pk])
    assert (pos >= 0).all()
    is_prim[pos] = True
    prim_edge[pk] = rel[pos]

    # ------------------------------------------------------------------ family keys
    pjs = sorted(RAW.glob("mft/*/dist/parents.json"))
    if not pjs:
        import zipfile
        zipfile.ZipFile(RAW / "mft.zip").extractall(RAW / "mft")
        pjs = sorted(RAW.glob("mft/*/dist/parents.json"))
    pj = json.loads(pjs[0].read_text())
    cols = pj["columns"]
    fam_map = {r[cols.index("id")]: r[cols.index("family")] for r in pj["rows"]}
    tot_map = {r[cols.index("id")]: r[cols.index("total")] for r in pj["rows"]}
    ids = nd["id"].values
    root_ids = ids[root]
    fam_key = pd.Series(root_ids).map(fam_map).fillna("other").values
    out["roots"] = int(((n_par == 0) & (n_kid > 0)).sum())
    out["roots_without_family_key"] = int(pd.Series(ids[(n_par == 0) & (n_kid > 0)]).map(fam_map).isna().sum())

    nd["n_par"], nd["n_kid"] = n_par, n_kid
    nd["primary"], nd["root"], nd["depth"], nd["ldepth"], nd["hyb"] = primary, root, depth, ldepth, hyb
    nd["sub"], nd["rel"], nd["family"] = sub, prim_edge, fam_key
    nd["fam_size"] = np.bincount(root, minlength=M)[root]
    nd["upstream_total"] = pd.Series(ids).map(tot_map).fillna(-1).astype(np.int64).values
    nd["topo"] = np.empty(M, np.int64)
    nd.loc[order, "topo"] = np.arange(M)
    ed = pd.DataFrame({"p": p, "c": c, "rel": rel, "primary": is_prim})

    nd.to_parquet(PROC / "nodes_conn.parquet", index=False)
    ed.to_parquet(PROC / "edges_conn.parquet", index=False)

    out["n_multi_parent"] = int((n_par >= 2).sum())
    out["n_children"] = int((n_par > 0).sum())
    out["n_parents"] = int((n_kid > 0).sum())
    out["n_leaves"] = int(((n_kid == 0) & (n_par > 0)).sum())
    out["edges_by_relation"] = {REL_NAMES[k]: int(v) for k, v in zip(*np.unique(rel, return_counts=True))}
    out["max_depth_primary"] = int(depth.max())
    out["max_depth_longest"] = int(ldepth.max())
    out["max_hybrid_depth"] = int(hyb.max())
    out["build_seconds"] = round(time.time() - t0, 1)
    (RES / "build.json").write_text(json.dumps(out, indent=2))
    log("done", json.dumps(out))


if __name__ == "__main__":
    main()
