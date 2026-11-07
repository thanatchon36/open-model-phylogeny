#!/usr/bin/env python3
"""F2 coral (one family: force-directed skeleton + sunflower leaves), F5 hybridisation web,
F6 statistics panel (light theme, for print)."""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from scipy.ndimage import gaussian_filter

from common import BG, FIG, INK, MUTED, PALETTE, PROC, REL_COLORS, RES, RING_ORDER, font_setup, hex2rgb, super_of

font_setup()
TAB = RES / "tables"
R = json.loads((RES / "results.json").read_text())
FOCUS = "qwen2.5"
GOLD = np.pi * (3 - np.sqrt(5))
REL4 = ["finetune", "adapter", "quantized", "merge"]


class Raster:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.acc = np.zeros((3, H * W), np.float32)

    def splat(self, px, py, w, rgb):
        ix, iy = np.round(px).astype(np.int64), np.round(py).astype(np.int64)
        ok = (ix >= 0) & (ix < self.W) & (iy >= 0) & (iy < self.H)
        idx = iy[ok] * self.W + ix[ok]
        for ch in range(3):
            self.acc[ch] += np.bincount(idx, weights=w[ok] * rgb[ok, ch], minlength=self.W * self.H).astype(np.float32)

    def segments(self, A, B, w, rgb, spacing=0.8, max_pts=2_500_000):
        L = np.hypot(*(B - A).T)
        n = np.clip(np.ceil(L / spacing).astype(np.int64), 2, 5000)
        cs = np.cumsum(n)
        st = np.concatenate([[0], cs[:-1]])
        i, E = 0, len(n)
        while i < E:
            j = max(i + 1, int(np.searchsorted(cs, st[i] + max_pts, side="right")))
            nn = n[i:j]
            e = np.repeat(np.arange(i, j), nn)
            off = np.arange(nn.sum()) - np.repeat(np.cumsum(nn) - nn, nn)
            t = off / (np.repeat(nn, nn) - 1)
            self.splat(A[e, 0] + t * (B[e, 0] - A[e, 0]), A[e, 1] + t * (B[e, 1] - A[e, 1]), (L / n)[e] * w[e], rgb[e])
            i = j

    def img(self):
        return self.acc.reshape(3, self.H, self.W)


def tone(a, k):
    return 1 - np.exp(-np.float32(k) * a)


def compose(base, layers):
    out = base
    for L, wgt in layers:
        out = 1 - (1 - out) * (1 - np.clip(L * np.float32(wgt), 0, 1))
    return np.clip(out, 0, 1)


# --------------------------------------------------------------------------------- F2 coral
def coral(W=3000):
    import igraph as ig
    from scipy.spatial import cKDTree
    nd = pd.read_parquet(PROC / "nodes_conn.parquet", columns=["id", "family", "primary", "sub", "rel", "downloads_all", "ghost", "created"])
    ed = pd.read_parquet(PROC / "edges_conn.parquet")
    sel = np.flatnonzero(nd["family"].values == FOCUS)
    n = len(sel)
    loc = np.full(len(nd), -1, np.int64)
    loc[sel] = np.arange(n)
    m = (loc[ed["p"].values] >= 0) & (loc[ed["c"].values] >= 0)
    ep, ec = loc[ed["p"].values[m]], loc[ed["c"].values[m]]
    eprim, erel = ed["primary"].values[m], ed["rel"].values[m]
    prim = nd["primary"].values[sel]
    pl = np.where(prim >= 0, loc[np.maximum(prim, 0)], -1)
    kids_in = np.bincount(ep[eprim], minlength=n)
    skel = np.union1d(np.flatnonzero(kids_in > 0), np.flatnonzero(pl < 0))
    sl = np.full(n, -1)
    sl[skel] = np.arange(len(skel))
    se = (sl[ep] >= 0) & (sl[ec] >= 0)
    hub = len(skel)
    edges = list(zip(sl[ep[se]].tolist(), sl[ec[se]].tolist())) + [(hub, int(sl[r])) for r in np.flatnonzero(pl < 0)]
    g = ig.Graph(n=len(skel) + 1, edges=edges)
    g.simplify()
    rs = np.random.RandomState(42)
    init = rs.uniform(-1, 1, (len(skel) + 1, 2)).tolist()
    lay = np.array(g.layout_fruchterman_reingold(niter=1500, seed=init, grid="auto").coords)
    P = np.zeros((n, 2))
    P[skel] = lay[:len(skel)]
    tree = cKDTree(P[skel])
    d, _ = tree.query(P[skel], k=2)
    ext = np.ptp(P[skel], axis=0).max()
    s0 = np.median(d[:, 1]) * 0.16
    leaves = np.setdiff1d(np.arange(n), skel)
    day = ((nd["created"].values[sel] - np.datetime64("2022-01-01")) / np.timedelta64(1, "D")).astype(float)
    df = pd.DataFrame({"v": leaves, "p": pl[leaves], "rel": nd["rel"].values[sel][leaves], "t": np.nan_to_num(day[leaves])})
    df = df[df.p >= 0].sort_values(["p", "rel", "t"])
    df["k"] = df.groupby("p").cumcount()
    df["K"] = df.groupby("p")["v"].transform("size")
    Rcl = np.minimum(s0 * np.sqrt(df.K.values), 0.075 * ext)
    rr = Rcl * np.sqrt((df.k.values + 0.5) / df.K.values)
    ang = df.k.values * GOLD
    P[df.v.values] = P[df.p.values] + np.c_[rr * np.cos(ang), rr * np.sin(ang)]
    lo, hi = P.min(0), P.max(0)
    sc = 0.86 * W / (hi - lo).max()
    px = (P - (lo + hi) / 2) * sc + np.array([W / 2, W * 0.53])
    relc = np.stack([hex2rgb(REL_COLORS[r]) for r in REL4 + ["unknown"]])
    ras = Raster(W, W)
    A, B = px[ep], px[ec]
    to_skel = sl[ec] >= 0
    w_e = np.where(to_skel, 3.2, np.where(erel == 2, 0.22, 0.35))
    w_e = np.where(eprim, w_e, 0.9)
    rgb_e = relc[np.clip(erel, 0, 4)].copy()
    rgb_e[~eprim] = np.array([1.0, 0.85, 0.92])
    ras.segments(A, B, w_e, rgb_e)
    L = ras.img()
    ref = np.percentile(L[L > 0], 99.7)
    dots = Raster(W, W)
    dl = np.log10(1 + nd["downloads_all"].values[sel])
    rel_n = np.clip(nd["rel"].values[sel], 0, 4)
    rgb_n = np.clip(relc[rel_n] * 0.55 + 0.45, 0, 1)
    rgb_n[pl < 0] = np.array([1.0, 0.97, 0.85])
    dots.splat(px[:, 0], px[:, 1], 0.25 + 0.3 * dl, rgb_n)
    D = dots.img()
    dref = np.percentile(D[D > 0], 99.5)
    star = Raster(W, W)
    big = np.argsort(-nd["sub"].values[sel])[:40]
    star.splat(px[big, 0], px[big, 1], np.log10(nd["sub"].values[sel][big] + 1) ** 2, np.ones((len(big), 3)) * np.array([1.0, 0.95, 0.85]))
    S_ = star.img()
    s = W / 1600
    base = np.empty((3, W, W), np.float32)
    yy, xx = np.mgrid[0:W, 0:W]
    neb = np.exp(-(((xx - W / 2) ** 2 + (yy - W * 0.53) ** 2) / (0.45 * W) ** 2)).astype(np.float32)
    for ch, (b, nb) in enumerate(zip(hex2rgb(BG), [0.04, 0.05, 0.10])):
        base[ch] = b + nb * neb
    out = compose(base, [(tone(gaussian_filter(L, (0, 6 * s, 6 * s)), 1.4 / ref), 0.6), (tone(L, 2.4 / ref), 1.0),
                         (tone(D, 1.0 / dref), 0.8),
                         (tone(gaussian_filter(S_, (0, 12 * s, 12 * s)), 30.0 / S_.max() * s ** 2 * 6), 0.8),
                         (tone(gaussian_filter(S_, (0, 2 * s, 2 * s)), 3.0 / S_.max() * s ** 2 * 6), 1.0)])
    img = (out.transpose(1, 2, 0) * 255).astype(np.uint8)
    fig = plt.figure(figsize=(W / 100, W / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img)
    ax.axis("off")
    f = W / 1600
    ids = nd["id"].values[sel]
    placed = []
    for v in np.argsort(-nd["sub"].values[sel])[:40]:
        x, y = px[v]
        if any(np.hypot(x - a, y - b) < 90 * f for a, b in placed) or nd["ghost"].values[sel][v]:
            continue
        placed.append((x, y))
        ax.text(x + 9 * f, y - 7 * f, ids[v].split("/")[-1], color="#FFF7E6", fontsize=7.5 * f, ha="left", va="bottom", alpha=0.95)
        if len(placed) >= 12:
            break
    cnt = pd.Series(nd["rel"].values[sel][pl >= 0]).map(dict(enumerate(REL4 + ["unknown"]))).value_counts()
    ax.text(48 * f, 60 * f, "A family as a coral: Qwen2.5", color=INK, fontsize=28 * f, fontweight="bold", va="top")
    ax.text(50 * f, 108 * f, f"{n:,} models whose lineage traces back to a Qwen2.5 base · {int(m.sum()):,} parent→child links inside the family",
            color="#C9D2E3", fontsize=10.5 * f, va="top")
    ax.text(50 * f, 130 * f, "Force-directed skeleton of every model that has children; each base's childless offspring bloom around it as a sunflower disc",
            color=MUTED, fontsize=9 * f, va="top")
    lx, ly = 50 * f, W - 120 * f
    for i, r in enumerate(REL4):
        ax.plot([lx, lx + 34 * f], [ly + i * 24 * f] * 2, color=REL_COLORS[r], lw=2.6 * f)
        ax.text(lx + 44 * f, ly + i * 24 * f, f"{r}  ({cnt.get(r, 0):,})", color="#C9D2E3", fontsize=9 * f, va="center")
    ax.text(W - 48 * f, W - 40 * f, "Data: Open Model Family Tree (h9-tec), CC BY 4.0 · snapshot 2026-11-05",
            color="#6F7A8E", fontsize=7.4 * f, ha="right", va="bottom")
    fig.savefig(FIG / "F2_coral_qwen25.png", dpi=100, facecolor=BG)
    plt.close(fig)
    print("F2 done", n, "nodes,", len(skel), "skeleton")


# --------------------------------------------------------------------------------- F5 hybrid web
def hybrid_web():
    hp = pd.read_csv(TAB / "hybrid_pairs.csv")
    part = pd.concat([hp.fa, hp.fb]).value_counts()
    top = list(part.head(36).index)
    sup = dict(zip(top, super_of(top)))
    order = sorted(top, key=lambda k: (RING_ORDER.index(sup[k]), -part[k]))
    gap = 0.07
    supers = []
    for k in order:
        if not supers or supers[-1] != sup[k]:
            supers.append(sup[k])
    total = 2 * np.pi - gap * len(supers)
    step = total / len(order)
    ang, a, prev = {}, np.pi / 2, None
    for k in order:
        if prev is not None and sup[k] != prev:
            a -= gap
        ang[k] = a
        a -= step
        prev = sup[k]
    pos = {k: np.array([np.cos(ang[k]), np.sin(ang[k])]) for k in order}
    hub = {}
    for s in supers:
        mm = np.mean([ang[k] for k in order if sup[k] == s])
        hub[s] = 0.42 * np.array([np.cos(mm), np.sin(mm)])
    cross = hp[(hp.fa != hp.fb) & hp.fa.isin(top) & hp.fb.isin(top)]
    agg = cross.assign(x=np.where(cross.fa < cross.fb, cross.fa, cross.fb), y=np.where(cross.fa < cross.fb, cross.fb, cross.fa)).groupby(["x", "y"]).size().sort_values()
    selfm = hp[hp.fa == hp.fb].fa.value_counts()
    fig = plt.figure(figsize=(16, 11), dpi=200)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0.0, 0.0, 0.66, 0.92])
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")
    mx = agg.max()
    t = np.linspace(0, 1, 70)[:, None]
    for (x, y), c in agg.items():
        P0, P3 = pos[x], pos[y]
        P1, P2 = hub[sup[x]], hub[sup[y]]
        B = (1 - t) ** 3 * P0 + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t ** 2 * P2 + t ** 3 * P3
        seg = np.stack([B[:-1], B[1:]], axis=1)
        ca, cb = hex2rgb(PALETTE[sup[x]]), hex2rgb(PALETTE[sup[y]])
        cols = (1 - t[:-1]) * ca + t[:-1] * cb
        fr = (c / mx) ** 0.5
        rgba = np.c_[cols, np.full(len(cols), 0.12 + 0.70 * fr)]
        ax.add_collection(LineCollection(seg, colors=rgba, linewidths=0.4 + 5.0 * fr, capstyle="round"))
    for k in order:
        x, y = pos[k]
        sz = 30 + 900 * (part[k] / part.max())
        ax.scatter([x], [y], s=sz * 2.6, color=PALETTE[sup[k]], alpha=0.18, edgecolors="none", zorder=3)
        ax.scatter([x], [y], s=sz, color=PALETTE[sup[k]], alpha=0.95, edgecolors="white", linewidths=0.4, zorder=4)
        rot = np.rad2deg(ang[k])
        ha = "left"
        if np.cos(ang[k]) < 0:
            rot += 180
            ha = "right"
        ax.text(1.09 * x, 1.09 * y, k, color="#E3E9F3", fontsize=9.5, rotation=rot, rotation_mode="anchor", ha=ha, va="center")
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.38, 1.38)
    H = R["rq2"]
    fig.text(0.02, 0.975, f"Model merging is assortative: parents are relatives {H['assortativity_ratio_related']:.0f}× more often than chance",
             color=INK, fontsize=19, fontweight="bold", va="top")
    fig.text(0.02, 0.93, f"Web of the {len(order)} families most involved in merges; curves join the families of two parents of the same merged model, "
                         f"bundled through their lineage hubs.\nNode size = merge participation; colour = lineage. "
                         f"{H['n_hybrids']:,} merged models, {H['n_parent_pairs']:,} parent pairs.", color=MUTED, fontsize=11, va="top")
    bx = fig.add_axes([0.70, 0.30, 0.27, 0.40])
    bx.set_facecolor(BG)
    ks = H["kinship_share"]
    obs = [ks["backcross"], ks["sibling"], ks["cousin"], ks["outcross"]]
    nul = [H["null_related_share_mean"], 0, 0, 1 - H["null_related_share_mean"]]
    cols = ["#FF5C8A", "#FF9F6B", "#FFD166", "#5B6B85"]
    labs = ["backcross", "sibling", "cousin", "unrelated (outcross)"]
    for row, vals in enumerate([obs, nul]):
        left = 0
        for v, cc in zip(vals, cols):
            bx.barh(1 - row, v, left=left, color=cc, height=0.55, edgecolor=BG, linewidth=1.2)
            left += v
    bx.set_yticks([1, 0])
    bx.set_yticklabels(["Observed\nmerges", "Random\npairing"], color="#E3E9F3", fontsize=11)
    bx.set_xlim(0, 1)
    bx.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    bx.tick_params(colors="#9AA4B2", labelsize=9.5)
    for sp in bx.spines.values():
        sp.set_visible(False)
    bx.text(0, 1.45, f"Related parents: {H['related_share']:.1%} observed vs {H['null_related_share_mean']:.1%} under\n"
                     f"100 random re-pairings (permutation p ≤ {H['perm_p_related']:.2f})", color="#E3E9F3", fontsize=11, va="bottom")
    hs = [plt.Rectangle((0, 0), 1, 1, color=c) for c in cols]
    bx.legend(hs, labs, loc="upper left", bbox_to_anchor=(0.0, -0.18), frameon=False, labelcolor="#C9D2E3", fontsize=10, ncol=2)
    bx.text(0, -0.95, f"Deepest merge chain: {H['hybrid_depth_max']} successive merges;\n{H['n_nodes_hybrid_depth_ge10']:,} models sit ≥10 merges deep, "
                      f"{H['top_author_share_hybrid_depth_ge10']:.0%} of them\nquantised builds from a single account.", color=MUTED, fontsize=10, va="top")
    fig.savefig(FIG / "F5_hybridisation_web.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("F5 done")


# --------------------------------------------------------------------------------- F6 statistics (print)
def stats_panel():
    LC = {"finetune": "#0A8F96", "adapter": "#7B5CD6", "quantized": "#D98E04", "merge": "#D1495B"}
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
                         "axes.titlesize": 11.5, "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9})
    fig, axs = plt.subplots(2, 2, figsize=(12, 8.6), dpi=220)
    # (a) CCDF of family sizes
    ax = axs[0, 0]
    sz = np.sort(pd.read_csv(TAB / "root_family_sizes.csv")["size"].values)
    u, cnt = np.unique(sz, return_counts=True)
    ccdf = 1 - np.concatenate([[0], np.cumsum(cnt)[:-1]]) / len(sz)
    ax.loglog(u, ccdf, "o", ms=2.6, color="#3B4A6B", alpha=0.75, label="empirical")
    S = R["rq1"]
    xm, al = S["powerlaw_xmin"], S["powerlaw_alpha"]
    c0 = ccdf[np.searchsorted(u, xm)]
    xx = np.logspace(np.log10(xm), np.log10(u.max()), 50)
    ax.loglog(xx, c0 * (xx / xm) ** (1 - al), color="#D1495B", lw=2, label=f"power law, α = {al:.2f} (x ≥ {xm:.0f})")
    ax.set_xlabel("Family size (models descending from one root)")
    ax.set_ylabel("P(size ≥ x)")
    ax.set_title("(a) Family sizes are heavy-tailed", loc="left")
    ax.legend(frameon=False, fontsize=8.8, loc="lower left")
    ax.text(0.98, 0.97, f"Top 1% of roots hold {S['top1pct_roots_share_of_connected']:.1%}\nof all connected models · Gini {S['gini_root_family_size']:.2f}",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color="#333")
    # (b) lag ECDF
    ax = axs[0, 1]
    lg = pd.read_csv(TAB / "lag_ecdf.csv")
    T = R["rq3"]
    for r in REL4:
        ax.semilogx(lg["days"], lg[r], color=LC[r], lw=2.1, label=f"{r} (median {T['lag_' + r]['median_days']:.0f} d)")
    ax.axvline(7, color="#999", lw=0.8, ls=":")
    ax.axvline(30, color="#999", lw=0.8, ls=":")
    ax.text(7, 0.02, " 1 week", fontsize=8, color="#777")
    ax.text(30, 0.02, " 1 month", fontsize=8, color="#777")
    ax.set_xlim(0.05, 2500)
    ax.set_xlabel("Days between parent and child creation")
    ax.set_ylabel("Share of edges")
    ax.set_title("(b) Quantisations follow their parent within weeks", loc="left")
    ax.legend(frameon=False, fontsize=8.8, loc="upper left")
    # (c) reaction time by release cohort
    ax = axs[1, 0]
    rt = pd.read_csv(TAB / "reaction_times.csv")
    halves = sorted(rt.release.unique())
    for j, r in enumerate(["finetune", "quantized", "adapter"]):
        med, lo_, hi_ = [], [], []
        for h in halves:
            v = rt.loc[rt.release == h, r].dropna().values
            med.append(np.median(v) if len(v) else np.nan)
            lo_.append(np.percentile(v, 25) if len(v) else np.nan)
            hi_.append(np.percentile(v, 75) if len(v) else np.nan)
        x = np.arange(len(halves)) + (j - 1) * 0.18
        med, lo_, hi_ = np.maximum(np.array(med), 0.05), np.maximum(np.array(lo_), 0.05), np.maximum(np.array(hi_), 0.05)
        ax.errorbar(x, med, yerr=[med - lo_, hi_ - med], fmt="o-", color=LC[r], ms=4.5, lw=1.6, capsize=2.5, label=r)
    ax.set_yscale("log")
    ax.set_xticks(range(len(halves)))
    ns = rt.groupby("release").size()
    ax.set_xticklabels([f"{h}\nn={ns[h]}" for h in halves], fontsize=8.2)
    ax.set_ylabel("Days to first child of each kind")
    ax.set_xlabel("Release cohort of the base model (bases with ≥100 children)")
    ax.set_title("(c) The ecosystem reacts faster every half-year", loc="left")
    ax.legend(frameon=False, fontsize=8.8, loc="upper right")
    # (d) forest plot
    ax = axs[1, 1]
    lgt = pd.read_csv(TAB / "logit_active.csv").set_index("name")
    rows = [("rel_quantized", "quantised (vs fine-tune)"), ("rel_adapter", "adapter (vs fine-tune)"), ("rel_merge", "merge (vs fine-tune)"),
            ("hybrid", "≥2 parents"), ("gen2", "generation 2 (vs 1)"), ("gen3p", "generation ≥3 (vs 1)"),
            ("log_author", "uploader size (×10 models)"), ("log_age", "age (×10 days)")]
    for i, (k, lab) in enumerate(rows[::-1]):
        rr_ = lgt.loc[k]
        col = "#0A8F96" if rr_["or"] > 1 else "#D1495B"
        ax.plot([rr_.or_lo, rr_.or_hi], [i, i], color=col, lw=2)
        ax.plot([rr_["or"]], [i], "o", color=col, ms=6)
        ax.text(rr_.or_hi * 1.12, i, f"{rr_['or']:.2f}", va="center", fontsize=8.6, color="#333")
    ax.axvline(1, color="#888", lw=0.9, ls="--")
    ax.set_xscale("log")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([lab for _, lab in rows[::-1]], fontsize=9)
    ax.set_xlabel("Odds ratio of being downloaded in the last 30 days (95% CI)")
    A = R["rq4"]
    ax.set_title(f"(d) What keeps a derivative alive (n = {A['logit_n']:,})", loc="left")
    ax.set_xlim(0.2, 60)
    fig.tight_layout(h_pad=2.2, w_pad=2.0)
    fig.savefig(FIG / "F6_statistics.png", facecolor="white")
    plt.close(fig)
    print("F6 done")


if __name__ == "__main__":
    which = sys.argv[1:] or ["coral", "web", "stats"]
    if "stats" in which:
        stats_panel()
    if "web" in which:
        hybrid_web()
    if "coral" in which:
        coral()
