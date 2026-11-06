#!/usr/bin/env python3
"""F1 - The Tree of Open Models: a radial chronogram of every Hugging Face model with a
declared ancestor or descendant. Custom additive rasteriser (numpy), text via matplotlib.

usage: python fig_hero.py [size_px] [variant]   variant in {all, collapsed}
"""
import json
import sys
import time

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

from common import BG, FIG, INK, MUTED, PALETTE, PROC, RES, RING_ORDER, font_setup, hex2rgb
from layout import R_IN, R_OUT, T0, SNAP

SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 1600
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "all"
H = W = SIZE
SCALE = 0.5 * SIZE * 0.86  # radius 1 -> pixels
CX, CY = W / 2, H * 0.515


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def to_px(x, y):
    return CX + x * SCALE, CY + y * SCALE


class Canvas:
    def __init__(self):
        self.acc = np.zeros((3, H * W), np.float32)

    def splat(self, px, py, wts, rgb):
        ix = np.round(px).astype(np.int64)
        iy = np.round(py).astype(np.int64)
        ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        idx = iy[ok] * W + ix[ok]
        for ch in range(3):
            self.acc[ch] += np.bincount(idx, weights=(wts[ok] * rgb[ok, ch]), minlength=H * W).astype(np.float32)

    def image(self):
        return self.acc.reshape(3, H, W)


def bezier_batch(P0, P1, P2, P3, alpha, rgb, canvas, spacing=0.7, max_pts=2_500_000):
    """Sample cubic Bezier curves (pixel coords) and splat them; vectorised in chunks."""
    L = (np.hypot(*(P1 - P0).T) + np.hypot(*(P2 - P1).T) + np.hypot(*(P3 - P2).T))
    n = np.clip(np.ceil(L / spacing).astype(np.int64), 2, 6000)
    cs = np.cumsum(n)
    starts = np.concatenate([[0], cs[:-1]])
    i = 0
    E = len(n)
    while i < E:
        j = np.searchsorted(cs, starts[i] + max_pts, side="right")
        j = max(j, i + 1)
        sl = slice(i, j)
        nn = n[sl]
        eidx = np.repeat(np.arange(i, j), nn)
        off = np.arange(nn.sum()) - np.repeat(np.cumsum(nn) - nn, nn)
        t = (off / (np.repeat(nn, nn) - 1)).astype(np.float64)
        u = 1 - t
        b0, b1, b2, b3 = u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3
        px = b0 * P0[eidx, 0] + b1 * P1[eidx, 0] + b2 * P2[eidx, 0] + b3 * P3[eidx, 0]
        py = b0 * P0[eidx, 1] + b1 * P1[eidx, 1] + b2 * P2[eidx, 1] + b3 * P3[eidx, 1]
        wts = (L[eidx] / nn[eidx - i] if False else (L / n)[eidx]) * alpha[eidx]
        canvas.splat(px, py, wts, rgb[eidx])
        i = j


def polar_ctrl(th_a, r_a, th_b, r_b):
    """d3.linkRadial-style control points: leave radially, bend at mid radius, arrive radially."""
    rm = (r_a + r_b) / 2
    def cart(th, r):
        a = th - np.pi / 2
        return np.stack(to_px(r * np.cos(a), r * np.sin(a)), axis=1)
    return cart(th_a, r_a), cart(th_a, rm), cart(th_b, rm), cart(th_b, r_b)


def tone(acc, k):
    return 1 - np.exp(-np.float32(k) * acc)


def main():
    t0 = time.time()
    lay = pd.read_parquet(PROC / "layout_radial.parquet")
    nd = pd.read_parquet(PROC / "nodes_conn.parquet", columns=["id", "downloads_all", "sub", "n_par", "n_kid", "rel", "ghost", "primary", "root", "family"])
    ed = pd.read_parquet(PROC / "edges_conn.parquet")
    th, r = lay["theta"].values, lay["r"].values
    sup = lay["super"].values
    col = np.stack([hex2rgb(PALETTE[s]) for s in RING_ORDER])
    sidx = pd.Series(sup).map({s: i for i, s in enumerate(RING_ORDER)}).values
    rgb_node = col[sidx]
    other = sup == "Other"
    import colorsys, zlib
    fams = nd["family"].values
    uf, inv = np.unique(fams[other], return_inverse=True)
    hues = np.array([zlib.crc32(f.encode()) % 1000 / 1000 for f in uf])
    tail = np.array([colorsys.hsv_to_rgb(h, 0.55, 0.85) for h in hues])
    rgb_node[np.flatnonzero(other)] = tail[inv]

    keep_node = np.ones(len(nd), bool)
    if VARIANT == "collapsed":
        keep_node = nd["rel"].values != 2  # hide quantized tips
    prim = ed[ed["primary"]]
    prim = prim[keep_node[prim["c"].values]]
    hyb = ed[~ed["primary"]]
    log("edges", len(prim), "hybrid", len(hyb))

    # ------------------------------------------------ compose (layer by layer, float32)
    s = SIZE / 1600
    f32 = np.float32
    out = np.empty((3, H, W), f32)
    yy = (np.arange(H, dtype=f32)[:, None] - f32(CY))
    xx = (np.arange(W, dtype=f32)[None, :] - f32(CX))
    rr2 = (xx ** 2 + yy ** 2) / f32((SCALE * 1.15) ** 2)
    neb = np.exp(-rr2 * f32(2.2))
    del rr2
    for ch, (b, nb) in enumerate(zip(hex2rgb(BG), [0.05, 0.06, 0.12])):
        out[ch] = f32(b) + f32(nb) * neb
    del neb

    def blend(layer, wgt=1.0):
        np.clip(layer * f32(wgt), 0, 1, out=layer)
        out[:] = 1 - (1 - out) * (1 - layer)

    # ------------------------------------------------ layer 1: lineage curves
    lines = Canvas()
    pa, ca = prim["p"].values, prim["c"].values
    P0, P1, P2, P3 = polar_ctrl(th[pa], r[pa], th[ca], r[ca])
    rel = nd["rel"].values[ca]
    alpha = np.where(rel == 2, 0.55, 1.0) * np.where(other[ca], 0.20, 1.0)
    rgbE = rgb_node[ca].copy()
    rgbE[other[ca]] = rgbE[other[ca]] * 0.9
    bezier_batch(P0, P1, P2, P3, alpha.astype(np.float64), rgbE, lines, spacing=max(0.6, SIZE / 4000))
    log("lines splatted")

    L_img = lines.image()
    ref = f32(np.percentile(L_img[L_img > 0], 99.0))
    blend(tone(gaussian_filter(L_img, sigma=(0, 7 * s, 7 * s)), 1.6 / ref), 0.55)
    blend(tone(L_img, 2.6 / ref))
    del lines, L_img
    # ------------------------------------------------ layer 2: hybridisation (bundled through the common ancestor)
    hybc = Canvas()
    hp, hc = hyb["p"].values, hyb["c"].values
    root = nd["root"].values
    primv = nd["primary"].values
    # control point: position of the most recent common ancestor in the primary tree, or the centre
    def anc_chain(v, lim=60):
        out = [v]
        while primv[v] >= 0 and len(out) < lim:
            v = primv[v]
            out.append(v)
        return out
    lca_x, lca_y = np.zeros(len(hp)), np.zeros(len(hp))
    for i, (a, b) in enumerate(zip(hp.tolist(), hc.tolist())):
        if root[a] != root[b]:
            continue
        ca_ = anc_chain(a)
        sb = set(anc_chain(b))
        for u in ca_:
            if u in sb:
                lca_x[i], lca_y[i] = lay["x"].values[u], lay["y"].values[u]
                break
    A = np.stack(to_px(lay["x"].values[hc], lay["y"].values[hc]), axis=1)
    B = np.stack(to_px(lay["x"].values[hp], lay["y"].values[hp]), axis=1)
    same = root[hp] == root[hc]
    mx = (lay["x"].values[hp] + lay["x"].values[hc]) / 2
    my = (lay["y"].values[hp] + lay["y"].values[hc]) / 2
    lx_ = np.where(same, lca_x * 0.92, mx * 0.30)
    ly_ = np.where(same, lca_y * 0.92, my * 0.30)
    Lc = np.stack(to_px(lx_, ly_), axis=1)
    beta = 0.78
    Q1 = A + beta * (Lc - A)
    Q2 = B + beta * (Lc - B)
    hrgb = np.tile(np.array([0.86, 0.95, 1.0]), (len(hp), 1))
    bezier_batch(A, Q1, Q2, B, np.full(len(hp), 1.0), hrgb, hybc, spacing=max(0.6, SIZE / 4000))
    log("hybrid splatted")

    Hm = hybc.image()
    href = f32(np.percentile(Hm[Hm > 0], 99.5))
    blend(tone(gaussian_filter(Hm, sigma=(0, 4 * s, 4 * s)), 0.5 / href), 0.35)
    blend(tone(Hm, 0.75 / href), 0.55)
    del hybc, Hm
    # ------------------------------------------------ layer 3: nodes (sparkles) and stars
    dots = Canvas()
    kn = np.flatnonzero(keep_node)
    px, py = to_px(lay["x"].values[kn], lay["y"].values[kn])
    dl = np.log10(1 + nd["downloads_all"].values[kn])
    wdot = (0.25 + 0.22 * dl) * np.where(other[kn], 0.5, 1.0)
    dots.splat(px, py, wdot, np.clip(rgb_node[kn] * 0.6 + 0.4, 0, 1))
    D = dots.image()
    dref = f32(np.percentile(D[D > 0], 99.5))
    blend(tone(D, 1.0 / dref), 0.85)
    del dots, D
    star = Canvas()
    big = np.argsort(-nd["sub"].values)[:400]
    spx, spy = to_px(lay["x"].values[big], lay["y"].values[big])
    star.splat(spx, spy, np.log10(nd["sub"].values[big]) ** 2.2, np.clip(rgb_node[big] * 0.5 + 0.5, 0, 1))
    log("dots splatted")

    S_ = star.image()
    smax = f32(S_.max())
    blend(tone(gaussian_filter(S_, sigma=(0, 14 * s, 14 * s)), 40.0 / smax * (s ** 2) * 6), 0.8)
    blend(tone(gaussian_filter(S_, sigma=(0, 2.2 * s, 2.2 * s)), 3.0 / smax * (s ** 2) * 6))
    del star, S_
    img = (np.clip(out, 0, 1).transpose(1, 2, 0) * 255).astype(np.uint8)
    del out
    log("composed")

    # ------------------------------------------------ typography
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    font_setup()
    R = json.loads((RES / "results.json").read_text())
    dpi = 100
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img, interpolation="none" if SIZE >= 3000 else "antialiased")
    del img
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    f = SIZE / 1600
    # year rings
    for yr in [2023, 2024, 2025, 2026]:
        rr_ = R_IN + (R_OUT - R_IN) * ((pd.Timestamp(f"{yr}-01-01") - T0) / (SNAP - T0))
        circ = plt.Circle((CX, CY), rr_ * SCALE, fill=False, lw=0.6 * f, color="#9fb3d9", alpha=0.22, ls=(0, (2, 3)))
        ax.add_patch(circ)
        ax.text(CX + 6 * f, CY - rr_ * SCALE - 4 * f, str(yr), color="#b9c7e6", alpha=0.75, fontsize=7.2 * f,
                ha="left", va="bottom", fontweight="normal")
    # super-family labels on the rim
    lr = R_OUT * SCALE + 26 * f
    th_all = th
    for spf in RING_ORDER:
        m = sup == spf
        if not m.any():
            continue
        a0, a1 = np.percentile(th_all[m], 0.5), np.percentile(th_all[m], 99.5)
        am = (a0 + a1) / 2 - np.pi / 2
        x, y = CX + lr * np.cos(am), CY + lr * np.sin(am)
        rot = np.rad2deg(am) + 90
        if 90 < (rot % 360) < 270:
            rot += 180
        name = "Long tail · 24k smaller families" if spf == "Other" else spf
        ax.text(x, y, name, color=PALETTE[spf], fontsize=(11 if spf != "Other" else 9.5) * f, ha="center", va="center",
                rotation=-rot if False else -((rot + 360) % 360) + 360, rotation_mode="anchor", fontweight="bold")
        # arc marking the wedge
        arc_t = np.linspace(a0, a1, 200) - np.pi / 2
        ax.plot(CX + (R_OUT * SCALE + 10 * f) * np.cos(arc_t), CY + (R_OUT * SCALE + 10 * f) * np.sin(arc_t),
                color=PALETTE[spf], lw=1.6 * f, alpha=0.85, solid_capstyle="round")
    # labels for the largest bases
    ids = nd["id"].values
    lab = [v for v in np.argsort(-nd["sub"].values)[:60] if not nd["ghost"].values[v]]
    placed = []
    for v in lab:
        x, y = to_px(lay["x"].values[v], lay["y"].values[v])
        if any(np.hypot(x - a, y - b) < 70 * f for a, b in placed):
            continue
        placed.append((x, y))
        name = ids[v].split("/")[-1]
        ax.text(x + 7 * f, y - 5 * f, name, color="#F4F7FB", fontsize=6.6 * f, ha="left", va="bottom", alpha=0.92,
                fontweight="normal", path_effects=None)
        if len(placed) >= 16:
            break
    O = R["overview"]
    ax.text(48 * f, 62 * f, "The Tree of Open Models", color=INK, fontsize=30 * f, fontweight="bold", ha="left", va="top")
    ax.text(50 * f, 112 * f,
            f"{O['n_connected']:,} Hugging Face models that declare a parent or have a child, linked by {O['n_edges']:,} lineage edges",
            color="#C9D2E3", fontsize=10.5 * f, ha="left", va="top")
    ax.text(50 * f, 134 * f, "Angle = lineage (each base's offspring sweep around it in birth order)   ·   Radius = date of creation, 2022 → Nov 2026",
            color=MUTED, fontsize=9 * f, ha="left", va="top")
    # legend
    lx, ly = 50 * f, H - 92 * f
    ax.plot([lx, lx + 38 * f], [ly, ly], color="#cfe9ff", lw=2 * f, alpha=0.95)
    ax.text(lx + 48 * f, ly, f"Hybridisation: {R['rq2']['n_hybrids']:,} merged models with ≥2 parents, curves bundled through the common ancestor",
            color="#C9D2E3", fontsize=8.6 * f, va="center")
    ax.scatter([lx + 19 * f], [ly + 26 * f], s=(9 * f) ** 2, color="#FFF6D8", alpha=0.95, edgecolors="none")
    ax.text(lx + 48 * f, ly + 26 * f, "Stars: the most-descended base models; point brightness = all-time downloads",
            color="#C9D2E3", fontsize=8.6 * f, va="center")
    ax.text(W - 48 * f, H - 40 * f,
            "Data: Open Model Family Tree (h9-tec), CC BY 4.0, from the Hub's /api/models dump · snapshot 2026-11-05",
            color="#6F7A8E", fontsize=7.4 * f, ha="right", va="bottom")
    tag = "" if VARIANT == "all" else "_collapsed"
    out_png = FIG / f"F1_tree_of_open_models{tag}_{SIZE}.png"
    fig.savefig(out_png, dpi=dpi, facecolor=BG)
    plt.close(fig)
    log("saved", out_png, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
