#!/usr/bin/env python3
"""Phases 2-4 - all statistics for RQ1-RQ5 (adapted), robustness and bootstrap CIs.

Writes results/results.json (single source of every number in the paper) and
results/tables/*.csv (inputs of the figures).
"""
import json
import re
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data/processed", ROOT / "results"
TAB = RES / "tables"
TAB.mkdir(parents=True, exist_ok=True)
SEED = 42
RNG = np.random.default_rng(SEED)
SNAP = pd.Timestamp("2026-11-05")
REL = ["finetune", "adapter", "quantized", "merge", "unknown"]

SUPER = [  # (super-family, regex over family key) - order matters
    ("Qwen", r"^qwen"), ("Llama", r"^(llama|codellama)"), ("Gemma", r"^gemma"),
    ("Mistral", r"^(mistral|mixtral|ministral|magistral|devstral|codestral|pixtral)"),
    ("FLUX", r"^flux"), ("Stable Diffusion", r"^(stable-diffusion|sdxl|sd\d|sd$)"),
    ("BERT family", r"^(bert|distilbert|roberta|xlm-roberta|deberta|modernbert|electra|albert|camembert|multilingual-e5|e5)"),
    ("Whisper", r"^whisper"), ("SmolLM", r"^smol"), ("DeepSeek", r"^deepseek"), ("Phi", r"^phi"),
    ("T5", r"^(t5|flan-t5|mt5|byt5)"),
]
TASK = {  # pipeline tag -> task group
    "Text generation": ["text-generation", "text2text-generation"],
    "Vision-language": ["image-text-to-text", "image-to-text", "visual-question-answering", "any-to-any",
                        "video-text-to-text", "document-question-answering", "audio-text-to-text"],
    "Text classification": ["text-classification", "zero-shot-classification"],
    "Token classification": ["token-classification"],
    "Embeddings & ranking": ["sentence-similarity", "feature-extraction", "text-ranking"],
    "Fill-mask": ["fill-mask"],
    "Question answering": ["question-answering", "table-question-answering"],
    "Translation & summarization": ["translation", "summarization"],
    "Speech & audio": ["automatic-speech-recognition", "text-to-speech", "audio-classification", "text-to-audio",
                       "audio-to-audio", "voice-activity-detection"],
    "Image & video generation": ["text-to-image", "image-to-image", "text-to-video", "image-to-video",
                                 "unconditional-image-generation", "image-to-3d", "text-to-3d"],
    "Vision": ["image-classification", "object-detection", "image-segmentation", "zero-shot-image-classification",
               "image-feature-extraction", "depth-estimation", "video-classification", "mask-generation",
               "zero-shot-object-detection", "keypoint-detection"],
    "Robotics & RL": ["robotics", "reinforcement-learning"],
}


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def q(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")


def cluster_boot(num, den, clusters, reps=500):
    """95% CI of sum(num)/sum(den) resampling clusters with replacement."""
    df = pd.DataFrame({"n": num, "d": den, "g": clusters}).groupby("g")[["n", "d"]].sum()
    n, d = df.n.values, df.d.values
    k = len(n)
    w = RNG.multinomial(k, np.full(k, 1 / k), size=reps)
    est = (w @ n) / (w @ d)
    return [float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))]


def main():
    t0 = time.time()
    R = {"build": json.loads((RES / "build.json").read_text())}
    nd = pd.read_parquet(PROC / "nodes_conn.parquet")
    ed = pd.read_parquet(PROC / "edges_conn.parquet")
    M = len(nd)
    days = ((nd["created"] - pd.Timestamp("1970-01-01")).dt.total_seconds() / 86400).values
    nd["day"] = days
    bf_day = (pd.Timestamp(R["build"]["backfill_date"]) - pd.Timestamp("1970-01-01")).days
    backfill = np.floor(days) == bf_day
    snap_day = (SNAP - pd.Timestamp("1970-01-01")).days
    fam = nd["family"].values
    sup = np.full(M, "Other", dtype=object)
    fam_s = pd.Series(fam)
    for name, rx in reversed(SUPER):
        sup[fam_s.str.contains(rx, regex=True).values] = name
    nd["super"] = sup
    ghost = nd["ghost"].values
    n_par, n_kid = nd["n_par"].values, nd["n_kid"].values
    is_root = (n_par == 0) & (n_kid > 0)
    is_child = n_par > 0
    rel = nd["rel"].values
    p, c, erel = ed["p"].values, ed["c"].values, ed["rel"].values

    # ---------------------------------------------------------------- overview
    O = {}
    O["n_models_hub"] = R["build"]["n_models_hub"]
    O["n_connected"] = M
    O["share_connected"] = M / O["n_models_hub"]
    O["n_children"] = int(is_child.sum())
    O["share_declare_parent"] = O["n_children"] / O["n_models_hub"]
    O["n_edges"] = int(len(ed))
    O["n_roots"] = int(is_root.sum())
    O["n_ghost"] = int(ghost.sum())
    O["n_families"] = int(pd.Series(fam[is_root]).nunique())
    O["n_authors_connected"] = int(nd["author"].nunique())
    O["children_by_relation"] = {REL[k]: int(v) for k, v in zip(*np.unique(rel[is_child], return_counts=True))}
    O["edges_by_relation"] = {REL[k]: int(v) for k, v in zip(*np.unique(erel, return_counts=True))}
    O["share_children_by_relation"] = {k: v / O["n_children"] for k, v in O["children_by_relation"].items()}
    O["backfill_in_connected"] = int(backfill.sum())
    O["first_child_date"] = str(nd.loc[is_child & ~backfill, "created"].min().date())
    R["overview"] = O
    log("overview", O["n_connected"])

    # ---------------------------------------------------------------- RQ1 structure
    S = {}
    rsz = nd["sub"].values[is_root]  # primary family size per root (incl. root)
    S["root_family_size_median"] = float(np.median(rsz))
    S["root_family_size_mean"] = float(rsz.mean())
    S["root_family_size_max"] = int(rsz.max())
    S["share_roots_size_le_3"] = float((rsz <= 3).mean())
    srt = np.sort(rsz)[::-1]
    S["top10_roots_share_of_connected"] = float(srt[:10].sum() / M)
    k1 = max(1, int(round(0.01 * len(srt))))
    S["top1pct_roots_n"] = k1
    S["top1pct_roots_share_of_connected"] = float(srt[:k1].sum() / M)
    S["gini_root_family_size"] = gini(rsz)
    fk = pd.Series(fam).value_counts()
    S["n_family_keys"] = int(len(fk))
    S["top10_family_keys"] = {k: int(v) for k, v in fk.head(10).items()}
    S["top10_family_keys_share"] = float(fk.head(10).sum() / M)
    sups = pd.Series(sup).value_counts()
    S["super_family_sizes"] = {k: int(v) for k, v in sups.items()}
    import powerlaw
    fit = powerlaw.Fit(rsz, discrete=True, verbose=False)
    Rln, pln = fit.distribution_compare("power_law", "lognormal", normalized_ratio=True)
    Rex, pex = fit.distribution_compare("power_law", "exponential", normalized_ratio=True)
    S["powerlaw_alpha"] = float(fit.power_law.alpha)
    S["powerlaw_xmin"] = float(fit.power_law.xmin)
    S["powerlaw_n_tail"] = int((rsz >= fit.power_law.xmin).sum())
    S["pl_vs_lognormal_R"], S["pl_vs_lognormal_p"] = float(Rln), float(pln)
    S["pl_vs_exponential_R"], S["pl_vs_exponential_p"] = float(Rex), float(pex)
    S["lognormal_mu"], S["lognormal_sigma"] = float(fit.lognormal.mu), float(fit.lognormal.sigma)
    dep = nd["depth"].values[is_child]
    S["depth_median"] = float(np.median(dep))
    S["depth_share_1"] = float((dep == 1).mean())
    S["depth_share_ge3"] = float((dep >= 3).mean())
    S["depth_p99"] = q(dep, 99)
    S["depth_max"] = int(dep.max())
    S["ldepth_max"] = int(nd["ldepth"].max())
    kids = n_kid[n_kid > 0]
    S["outdeg_median"] = float(np.median(kids))
    S["outdeg_p99"] = q(kids, 99)
    S["outdeg_max"] = int(kids.max())
    S["share_children_leaves"] = float(((n_kid == 0) & is_child).sum() / is_child.sum())
    comp = {}
    for g, lab in [(1, "1"), (2, "2"), (3, "3"), (4, "4+")]:
        m = is_child & ((nd["depth"].values == g) if g < 4 else (nd["depth"].values >= 4))
        vc = pd.Series(rel[m]).value_counts(normalize=True)
        comp[lab] = {REL[k]: float(v) for k, v in vc.items()}
        comp[lab]["n"] = int(m.sum())
    S["relation_by_generation"] = comp
    # leaves by relation: quantized as terminal tips
    S["leaf_share_by_relation"] = {REL[r]: float(((n_kid == 0) & is_child & (rel == r)).sum() / max(1, (is_child & (rel == r)).sum())) for r in range(4)}
    gr = is_root & ghost
    S["ghost_roots"] = int(gr.sum())
    S["nodes_under_ghost_roots"] = int(ghost[nd["root"].values].sum() - ghost.sum() + gr.sum())
    S["share_nodes_under_ghost_roots"] = S["nodes_under_ghost_roots"] / M
    R["rq1"] = S
    pd.DataFrame({"size": rsz}).to_csv(TAB / "root_family_sizes.csv", index=False)
    log("RQ1 done; alpha", round(S["powerlaw_alpha"], 2), "R_ln", round(Rln, 2))

    # ---------------------------------------------------------------- RQ2 hybridization
    H = {}
    srt_c = np.argsort(c, kind="stable")
    pptr = np.concatenate([[0], np.cumsum(np.bincount(c, minlength=M))])
    plist = p[srt_c]
    hyb_nodes = np.flatnonzero(n_par >= 2)
    H["n_hybrids"] = int(len(hyb_nodes))
    H["n_merge_labelled"] = int((rel == 3).sum())
    H["share_merge_labelled_multi_parent"] = float(((rel == 3) & (n_par >= 2)).sum() / max(1, (rel == 3).sum()))
    npar_h = n_par[hyb_nodes]
    H["parents_per_hybrid"] = {str(k): int(v) for k, v in pd.Series(np.minimum(npar_h, 6)).value_counts().sort_index().items()}
    H["parents_per_hybrid_max"] = int(npar_h.max())
    # ancestor sets (memoised, DAG)
    plist_l, pptr_l = plist.tolist(), pptr.tolist()
    memo = {}

    def anc(v):
        if v in memo:
            return memo[v]
        stack, seen = [v], set()
        while stack:
            u = stack.pop()
            for w in plist_l[pptr_l[u]:pptr_l[u + 1]]:
                if w not in seen:
                    if w in memo:
                        seen |= memo[w]
                        seen.add(w)
                    else:
                        seen.add(w)
                        stack.append(w)
        memo[v] = frozenset(seen)
        return memo[v]

    par_sets = [plist[pptr[v]:pptr[v + 1]] for v in hyb_nodes]
    direct = {}

    def kin(a, b):
        A, B = anc(a), anc(b)
        if a in B or b in A:
            return "backcross"
        pa = set(plist_l[pptr_l[a]:pptr_l[a + 1]])
        pb = set(plist_l[pptr_l[b]:pptr_l[b + 1]])
        if pa & pb:
            return "sibling"
        if (A | {a}) & (B | {b}):
            return "cousin"
        return "outcross"

    pairs, kinds = [], []
    for ps in par_sets:
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                pairs.append((ps[i], ps[j]))
    for a, b in pairs:
        kinds.append(kin(a, b))
    kv = pd.Series(kinds).value_counts()
    H["n_parent_pairs"] = int(len(pairs))
    H["kinship_share"] = {k: float(kv.get(k, 0) / len(pairs)) for k in ["backcross", "sibling", "cousin", "outcross"]}
    H["related_share"] = 1 - H["kinship_share"]["outcross"]
    pf = fam
    cross_fam = np.array([pf[a] != pf[b] for a, b in pairs])
    cross_sup = np.array([sup[a] != sup[b] for a, b in pairs])
    H["cross_family_pair_share"] = float(cross_fam.mean())
    H["cross_super_family_pair_share"] = float(cross_sup.mean())
    # permutation null: shuffle parents across hybrids, keep parent multiset and per-hybrid counts
    allp = np.concatenate(par_sets)
    sizes = np.array([len(s) for s in par_sets])
    cuts = np.cumsum(sizes)[:-1]
    null_rel, null_cross = [], []
    for _ in range(100):
        sh = RNG.permutation(allp)
        groups = np.split(sh, cuts)
        rel_n, cr_n, tot = 0, 0, 0
        for ps in groups:
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    a, b = ps[i], ps[j]
                    if a == b:
                        continue
                    tot += 1
                    A, B = anc(a), anc(b)
                    if (A | {a}) & (B | {b}):
                        rel_n += 1
                    if pf[a] != pf[b]:
                        cr_n += 1
        null_rel.append(rel_n / tot)
        null_cross.append(cr_n / tot)
    H["null_related_share_mean"] = float(np.mean(null_rel))
    H["null_related_share_ci"] = [q(null_rel, 2.5), q(null_rel, 97.5)]
    H["null_cross_family_share_mean"] = float(np.mean(null_cross))
    H["assortativity_ratio_related"] = H["related_share"] / H["null_related_share_mean"]
    H["perm_p_related"] = float((np.sum(np.array(null_rel) >= H["related_share"]) + 1) / 101)
    hd = nd["hyb"].values
    H["hybrid_depth_median_hybrids"] = float(np.median(hd[hyb_nodes]))
    H["hybrid_depth_max"] = int(hd.max())
    deep = hd >= 10
    H["n_nodes_hybrid_depth_ge10"] = int(deep.sum())
    H["authors_hybrid_depth_ge10"] = int(nd.loc[deep, "author"].nunique())
    top_author_share = nd.loc[deep, "author"].value_counts(normalize=True)
    H["top_author_share_hybrid_depth_ge10"] = float(top_author_share.iloc[0]) if len(top_author_share) else 0.0
    H["anc_size_max"] = int(max(len(anc(v)) for v in hyb_nodes[np.argsort(-hd[hyb_nodes])[:50]]))
    # super-family hybridisation matrix (for the hybrid web figure)
    pd.DataFrame({"a": [sup[a] for a, b in pairs], "b": [sup[b] for a, b in pairs],
                  "fa": [pf[a] for a, b in pairs], "fb": [pf[b] for a, b in pairs], "kind": kinds}).to_csv(
        TAB / "hybrid_pairs.csv", index=False)
    pd.DataFrame({"hyb": hd[hd > 0]}).to_csv(TAB / "hybrid_depth.csv", index=False)
    hcl = np.array([fam[v] for v in hyb_nodes])
    H["outcross_ci"] = cluster_boot(np.array([k == "outcross" for k in kinds], float), np.ones(len(kinds)),
                                    np.array([pf[a] for a, b in pairs]))
    R["rq2"] = H
    log("RQ2 done; related", round(H["related_share"], 3), "null", round(H["null_related_share_mean"], 3))

    # ---------------------------------------------------------------- RQ3 tempo
    T = {}
    lag = days[c] - days[p]
    valid = (~ghost[p]) & (~backfill[p]) & (~backfill[c]) & np.isfinite(lag)
    T["edges_valid_for_lag"] = int(valid.sum())
    T["share_negative_lag"] = float((lag[valid] < 0).mean())
    ok = valid & (lag >= 0)
    for r in range(4):
        m = ok & (erel == r)
        x = lag[m]
        T[f"lag_{REL[r]}"] = {"n": int(m.sum()), "median_days": q(x, 50), "p25": q(x, 25), "p75": q(x, 75),
                              "share_within_1d": float((x <= 1).mean()), "share_within_7d": float((x <= 7).mean()),
                              "share_within_30d": float((x <= 30).mean())}
    ecdf = {}
    grid = np.unique(np.concatenate([np.logspace(-2, 3.6, 200)]))
    for r in range(4):
        x = np.sort(lag[ok & (erel == r)])
        ecdf[REL[r]] = np.searchsorted(x, grid, side="right") / len(x)
    pd.DataFrame({"days": grid, **ecdf}).to_csv(TAB / "lag_ecdf.csv", index=False)
    # reaction time of major bases
    major = (n_kid >= 100) & (~ghost) & (~backfill) & (days >= (pd.Timestamp("2023-01-01") - pd.Timestamp("1970-01-01")).days) & (days <= snap_day - 180)
    T["n_major_bases"] = int(major.sum())
    rows = []
    mb = np.flatnonzero(major)
    sel = np.isin(p, mb) & ok
    df = pd.DataFrame({"p": p[sel], "rel": erel[sel], "lag": lag[sel]})
    first = df.groupby(["p", "rel"])["lag"].min().unstack()
    first.columns = [REL[k] for k in first.columns]
    half = pd.Series(nd["created"].values[first.index]).dt.year.astype(str).values + np.where(
        pd.Series(nd["created"].values[first.index]).dt.month.values <= 6, "H1", "H2")
    first["release"] = half
    first.to_csv(TAB / "reaction_times.csv")
    rt = first.groupby("release").median(numeric_only=True)
    cnt = first.groupby("release").size()
    T["reaction_median_days_by_half"] = {h: {k: (None if pd.isna(v) else float(v)) for k, v in rt.loc[h].items()} | {"n": int(cnt[h])} for h in rt.index}
    from scipy.stats import spearmanr
    ry = pd.Series(nd["created"].values[first.index]).dt.year.values + (pd.Series(nd["created"].values[first.index]).dt.dayofyear.values / 366)
    for r in ["quantized", "finetune", "adapter", "merge"]:
        if r in first:
            m = first[r].notna().values
            rho, pv = spearmanr(ry[m], first[r].values[m])
            T[f"reaction_trend_{r}"] = {"spearman_rho": float(rho), "p": float(pv), "n": int(m.sum()),
                                       "median_days": float(np.median(first[r].values[m]))}
    since24 = ry >= 2024
    for r in ["quantized", "finetune", "adapter", "merge"]:
        if r in first:
            m = first[r].notna().values & since24
            rho, pv = spearmanr(ry[m], first[r].values[m])
            T[f"reaction_trend_{r}_since2024"] = {"spearman_rho": float(rho), "p": float(pv), "n": int(m.sum()),
                                                 "median_days": float(np.median(first[r].values[m]))}
    # attention decay within the first year
    old = (n_kid >= 100) & (~ghost) & (~backfill) & (days >= (pd.Timestamp("2023-01-01") - pd.Timestamp("1970-01-01")).days) & (days <= snap_day - 365)
    selo = np.isin(p, np.flatnonzero(old)) & ok & (lag <= 365)
    d2 = pd.DataFrame({"p": p[selo], "lag": lag[selo]})
    g = d2.groupby("p")["lag"]
    T["n_bases_decay"] = int(g.ngroups)
    T["decay_share_first30d_median"] = float(g.apply(lambda s: (s <= 30).mean()).median())
    T["decay_halflife_days_median"] = float(g.median().median())
    # monthly births by super-family (non-root children) for the streamgraph
    m = is_child & ~backfill & (nd["created"] >= "2021-01-01") & (nd["created"] < "2026-11-01")
    mon = nd.loc[m, ["created", "super"]].assign(month=lambda d: d.created.dt.to_period("M").astype(str))
    births = mon.groupby(["month", "super"]).size().unstack(fill_value=0)
    births.to_csv(TAB / "monthly_births.csv")
    T["births_peak_month"] = str(births.sum(1).idxmax())
    T["births_peak_count"] = int(births.sum(1).max())
    yr = mon.groupby(mon.created.dt.year).size()
    T["births_by_year"] = {str(k): int(v) for k, v in yr.items()}
    au_ch = nd.loc[is_child, "author"].value_counts()
    T["n_uploaders_children"] = int(len(au_ch))
    T["share_children_top10_uploaders"] = float(au_ch.head(10).sum() / au_ch.sum())
    T["share_children_top100_uploaders"] = float(au_ch.head(100).sum() / au_ch.sum())
    T["gini_children_per_uploader"] = gini(au_ch.values)
    pk = mon[mon.month == T["births_peak_month"]]
    pka = nd.loc[pk.index, "author"].value_counts(normalize=True)
    T["peak_month_top_uploader_share"] = float(pka.iloc[0])
    T["peak_month_top_super"] = str(pk["super"].value_counts().index[0])
    R["rq3"] = T
    log("RQ3 done")

    # ---------------------------------------------------------------- RQ4 attention
    A = {}
    dl_all, dl30 = nd["downloads_all"].values, nd["downloads"].values
    ch = is_child & ~ghost
    A["share_children_zero_downloads_all"] = float((dl_all[ch] == 0).mean())
    A["share_children_dormant_30d"] = float((dl30[ch] == 0).mean())
    A["dormant_ci"] = cluster_boot((dl30[ch] == 0).astype(float), np.ones(ch.sum()), fam[ch])
    A["dormant_by_relation"] = {REL[r]: float((dl30[ch & (rel == r)] == 0).mean()) for r in range(4)}
    A["median_downloads_all_by_relation"] = {REL[r]: float(np.median(dl_all[ch & (rel == r)])) for r in range(4)}
    A["children_downloads_all_total"] = int(dl_all[ch].sum())
    top = np.sort(dl_all[ch])[::-1]
    A["share_child_downloads_top1pct"] = float(top[:max(1, len(top) // 100)].sum() / top.sum())
    A["gini_child_downloads_all"] = gini(dl_all[ch])
    root_ids = nd["root"].values
    big = is_root & (~ghost) & (nd["sub"].values >= 51)
    bdf = pd.DataFrame({"root": root_ids[ch], "dl": dl_all[ch]}).groupby("root")["dl"].agg(["sum", "max"])
    bdf = bdf[bdf.index.isin(np.flatnonzero(big))]
    rdl = dl_all[bdf.index.values]
    A["n_big_families"] = int(len(bdf))
    A["family_download_share_descendants_median"] = float(np.median(bdf["sum"].values / np.maximum(1, bdf["sum"].values + rdl)))
    A["share_families_child_outgrows_root"] = float((bdf["max"].values > rdl).mean())
    from scipy.stats import spearmanr
    pm = (n_kid >= 10) & ~ghost
    rho, pv = spearmanr(n_kid[pm], dl_all[pm])
    A["spearman_children_vs_downloads"] = {"rho": float(rho), "p": float(pv), "n": int(pm.sum())}
    bm = (n_kid >= 100) & ~ghost
    kid_rel = pd.DataFrame({"p": p, "r": erel}).query("p in @np.flatnonzero(@bm)").groupby("p")["r"].apply(lambda s: (s == 1).mean())
    A["n_bases_ge100"] = int(bm.sum())
    A["share_bases_adapter_dominated"] = float((kid_rel >= 0.9).mean())
    # logistic regression: P(active in last 30 days)
    import statsmodels.api as sm
    auth_n = nd.groupby("author")["id"].transform("size").values
    age = np.maximum(1.0, snap_day - days)
    dfm = pd.DataFrame({
        "active": (dl30 > 0).astype(float),
        "rel": pd.Categorical([REL[r] if r >= 0 else "none" for r in rel], categories=["finetune", "adapter", "quantized", "merge"]),
        "gen": np.minimum(nd["depth"].values, 3), "hybrid": (n_par >= 2).astype(float),
        "log_author": np.log10(auth_n), "log_age": np.log10(age),
        "super": nd["super"].values, "fam": fam})[ch & (rel <= 3) & ~backfill]
    X = pd.get_dummies(dfm[["rel"]], drop_first=True, dtype=float)
    X["gen2"] = (dfm.gen == 2).astype(float)
    X["gen3p"] = (dfm.gen >= 3).astype(float)
    X["hybrid"] = dfm.hybrid
    X["log_author"] = dfm.log_author
    X["log_age"] = dfm.log_age
    X = pd.concat([X, pd.get_dummies(dfm["super"], prefix="sf", dtype=float).drop(columns=["sf_Other"])], axis=1)
    X = sm.add_constant(X)
    groups = pd.factorize(dfm.fam)[0]
    res = sm.Logit(dfm.active.values, X.values).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups})
    coef = pd.DataFrame({"name": X.columns, "beta": res.params, "se": res.bse, "p": res.pvalues})
    coef["or"] = np.exp(coef.beta)
    coef["or_lo"] = np.exp(coef.beta - 1.96 * coef.se)
    coef["or_hi"] = np.exp(coef.beta + 1.96 * coef.se)
    coef.to_csv(TAB / "logit_active.csv", index=False)
    A["logit_n"] = int(len(dfm))
    A["logit_pseudo_r2"] = float(res.prsquared)
    A["logit_or"] = {r.name: {"or": float(r["or"]), "lo": float(r.or_lo), "hi": float(r.or_hi), "p": float(r.p)} for _, r in coef.set_index("name").iterrows()}
    R["rq4"] = A
    log("RQ4 done; dormant", round(A["share_children_dormant_30d"], 3))

    # ---------------------------------------------------------------- RQ5 speciation
    Sp = {}
    tmap = {t: g for g, ts in TASK.items() for t in ts}
    pipe = nd["pipeline"].values
    tg = np.array([tmap.get(x, "Other") if isinstance(x, str) else None for x in pipe], dtype=object)
    known = np.array([x is not None for x in tg])
    kk = known[p] & known[c]
    Sp["edges_with_both_tasks"] = int(kk.sum())
    diff = np.array([tg[a] != tg[b] for a, b in zip(p[kk], c[kk])])
    Sp["speciation_rate"] = float(diff.mean())
    Sp["speciation_ci"] = cluster_boot(diff.astype(float), np.ones(len(diff)), fam[c[kk]])
    Sp["speciation_by_relation"] = {REL[r]: float(diff[erel[kk] == r].mean()) for r in range(4) if (erel[kk] == r).any()}
    pdiff = np.array([pipe[a] != pipe[b] for a, b in zip(p[kk], c[kk])])
    Sp["pipeline_change_rate"] = float(pdiff.mean())
    tr = pd.DataFrame({"src": tg[p[kk]], "dst": tg[c[kk]], "rel": erel[kk]})
    tr.groupby(["src", "dst"]).size().rename("n").reset_index().to_csv(TAB / "task_transitions.csv", index=False)
    pt = pd.DataFrame({"src": pipe[p[kk]], "dst": pipe[c[kk]]})
    top_pt = pt[pt.src != pt.dst].value_counts().head(10)
    Sp["top_pipeline_transitions"] = [{"src": a, "dst": b, "n": int(n)} for (a, b), n in top_pt.items()]
    Sp["top_transition_share_of_changes"] = float(top_pt.iloc[0] / pdiff.sum())
    by_src = tr.assign(d=tr.src != tr.dst).groupby("src")["d"].agg(["mean", "size"])
    Sp["speciation_by_source_task"] = {k: {"rate": float(r["mean"]), "n": int(r["size"])} for k, r in by_src.iterrows() if r["size"] >= 1000}
    lib = nd["library"].values
    qm = (erel == 2) & np.array([isinstance(x, str) for x in lib[p]]) & np.array([isinstance(x, str) for x in lib[c]])
    lt = pd.DataFrame({"src": lib[p[qm]], "dst": lib[c[qm]]})
    Sp["quantized_edges_with_library"] = int(qm.sum())
    Sp["quantized_library_change_rate"] = float((lt.src != lt.dst).mean())
    Sp["top_quantized_library_transitions"] = [{"src": a, "dst": b, "n": int(n)} for (a, b), n in lt[lt.src != lt.dst].value_counts().head(6).items()]
    R["rq5"] = Sp
    log("RQ5 done; speciation", round(Sp["speciation_rate"], 3))

    # ---------------------------------------------------------------- robustness
    Rb = {}

    fp = np.full(M, -1)
    has = n_par > 0
    fp[has] = plist[pptr[:-1][has]]
    root_first = np.arange(M)
    rl, fl = root_first.tolist(), fp.tolist()
    for v in np.argsort(nd["topo"].values).tolist():
        if fl[v] >= 0:
            rl[v] = rl[fl[v]]
    root_first = np.array(rl)
    root_main = nd["root"].values

    def headline(mask_nodes, mask_edges, root_arr=None):
        root_arr = root_main if root_arr is None else root_arr
        out = {}
        cnt = np.bincount(root_arr[mask_nodes | is_root], minlength=M)
        sz = cnt[is_root]
        sz = sz[sz >= 2]
        out["gini_family_size"] = gini(sz)
        out["top10_share"] = float(np.sort(sz)[::-1][:10].sum() / sz.sum())
        me = mask_edges & kk_full
        dd = np.array([tg[a] != tg[b] for a, b in zip(p[me], c[me])])
        out["speciation_rate"] = float(dd.mean()) if len(dd) else float("nan")
        mf = ok & (erel == 0) & mask_edges
        out["median_lag_finetune"] = q(lag[mf], 50)
        chm = ch & mask_nodes
        out["dormant_share"] = float((dl30[chm] == 0).mean())
        return out

    kk_full = known[p] & known[c]
    alln, alle = np.ones(M, bool), np.ones(len(ed), bool)
    Rb["main"] = headline(alln, alle)
    Rb["first_listed_primary"] = headline(alln, alle, root_arr=root_first)
    nq = rel != 2
    Rb["no_quantized"] = headline(nq | ~is_child, erel != 2)
    au = nd["author"].value_counts()
    topa = set(au.index[:max(1, len(au) // 100)])
    nb = ~nd["author"].isin(topa).values
    Rb["no_top1pct_uploaders"] = headline(nb | is_root, nb[c])
    recent = days >= snap_day - 730
    Rb["last_24_months"] = headline(recent | is_root, recent[c])
    Rb["top1pct_uploaders_n"] = len(topa)
    Rb["top1pct_uploaders_share_children"] = float((~nb & is_child).sum() / is_child.sum())
    R["robustness"] = Rb
    R["meta"] = {"snapshot": "2026-11-05", "seed": SEED, "seconds": round(time.time() - t0, 1),
                 "source": "h9-tec/model-family-tree release data-latest (CC BY 4.0), from cfahlgren1/hub-stats (Apache-2.0)"}
    (RES / "results.json").write_text(json.dumps(R, indent=2, default=float))
    log("all done in", R["meta"]["seconds"], "s")


if __name__ == "__main__":
    main()
