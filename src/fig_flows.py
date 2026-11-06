#!/usr/bin/env python3
"""F3 speciation chord diagram (task changes along lineage edges) and
F4 'Cambrian explosion' streamgraph (monthly births of derivative models)."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch

from common import BG, FIG, INK, MUTED, PALETTE, RES, font_setup

font_setup()
TAB = RES / "tables"
R = json.loads((RES / "results.json").read_text())
TASK_COL = {
    "Text generation": "#9D7BFF", "Vision-language": "#FF5FB0", "Text classification": "#3EE08F",
    "Token classification": "#C7F464", "Embeddings & ranking": "#2FD9F5", "Fill-mask": "#FFD447",
    "Question answering": "#FF8C42", "Translation & summarization": "#FFB4A2", "Speech & audio": "#5EEAD4",
    "Image & video generation": "#E879F9", "Vision": "#4C8DFF", "Robotics & RL": "#FF6B6B", "Other": "#8A94A6",
}


def stream():
    b = pd.read_csv(TAB / "monthly_births.csv", index_col=0)
    b = b.loc["2022-06":"2026-10"]
    order = ["Other", "BERT family", "Whisper", "Stable Diffusion", "FLUX", "Gemma", "Qwen", "Llama", "Mistral",
             "DeepSeek", "Phi", "SmolLM", "T5"]
    order = [o for o in order if o in b.columns]
    b = b[order]
    sm = b.rolling(3, center=True, min_periods=1).mean()
    x = np.arange(len(sm))
    # smooth on a finer grid for a flowing silhouette
    xf = np.linspace(0, len(sm) - 1, len(sm) * 8)
    Y = np.vstack([np.interp(xf, x, sm[c].values) for c in order])
    fig, ax = plt.subplots(figsize=(16, 7.2), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    cols = [PALETTE[o] for o in order]
    polys = ax.stackplot(xf, Y, baseline="wiggle", colors=cols, alpha=0.92, linewidth=0)
    polys[0].set_alpha(0.45)
    # outline glow
    ax.set_xlim(0, len(sm) - 1)
    ax.axis("off")
    # year ticks
    months = list(sm.index)
    base = np.cumsum(Y, axis=0)
    g0 = -0.5 * Y.sum(0) - (np.cumsum((np.arange(len(order))[:, None] + 0.5) * np.gradient(Y, axis=1), axis=0).sum(0) * 0)
    lo, hi = ax.get_ylim()
    for yr in range(2023, 2027):
        k = months.index(f"{yr}-01") if f"{yr}-01" in months else None
        if k is None:
            continue
        ax.axvline(k, color="#9fb3d9", alpha=0.18, lw=0.8, ls=(0, (2, 3)))
        ax.text(k + 0.2, lo + (hi - lo) * 0.02, str(yr), color="#b9c7e6", fontsize=11, alpha=0.8)
    # labels at the widest point of each major stream
    y0 = np.array(polys[0].get_paths()[0].vertices)
    lower = np.zeros(len(xf))
    # recompute baseline positions with matplotlib's wiggle formula
    m = Y.shape[0]
    center = np.zeros(len(xf))
    total = Y.sum(0)
    wig = (m - 0.5 - np.arange(m))[:, None] * Y
    center = wig.sum(0) / m
    first_line = -center  # matplotlib: first_line = center - 0.5*total? use path vertices instead
    for i, (o, poly) in enumerate(zip(order, polys)):
        if o in ("Other", "T5", "Phi"):
            continue
        v = poly.get_paths()[0].vertices
        n = len(xf)
        top = v[1:n + 1, 1] if len(v) > 2 * n else None
        thick = Y[i]
        j = int(np.argmax(thick))
        if thick[j] < 2500:
            continue
        # find vertical centre of the band at j
        verts = v[:, :]
        xs = verts[:, 0]
        col_pts = verts[np.abs(xs - xf[j]) < 1e-6][:, 1]
        if len(col_pts) >= 2:
            yc = col_pts.mean()
            ax.text(xf[j], yc, o, color="#0B0F1A", fontsize=12 if thick[j] > 8000 else 10, ha="center", va="center",
                    fontweight="bold")
    T = R["rq3"]
    pk = T["births_peak_month"]
    kx = months.index(pk)
    ax.annotate(f"Peak: {pd.Timestamp(pk + '-01'):%b %Y}\n{T['births_peak_count']:,} new derivatives in one month",
                xy=(kx, hi * 0.80), xytext=(kx + 6, hi * 0.93), color=INK, fontsize=11.5,
                arrowprops=dict(arrowstyle="-", color="#cfd8ea", lw=0.8, alpha=0.7))
    ax.text(0.005, 0.99, "The Cambrian explosion of open-model derivatives", transform=ax.transAxes, color=INK,
            fontsize=20, fontweight="bold", va="top")
    by = T["births_by_year"]
    ax.text(0.005, 0.91, f"Monthly births of models that declare a parent, by lineage (3-month moving average). "
                         f"2023: {by['2023']:,}  ·  2024: {by['2024']:,}  ·  2025: {by['2025']:,}  ·  2026 (Jan–Oct): {by['2026']:,}",
            transform=ax.transAxes, color=MUTED, fontsize=11, va="top")
    hs = [plt.Rectangle((0, 0), 1, 1, color=PALETTE[o], alpha=0.9 if o != "Other" else 0.45) for o in order[::-1]]
    ax.legend(hs, [o if o != "Other" else "Long tail" for o in order[::-1]], loc="lower left", ncol=7, frameon=False,
              labelcolor="#C9D2E3", fontsize=10, bbox_to_anchor=(0.0, -0.06))
    fig.savefig(FIG / "F4_cambrian_streamgraph.png", facecolor=BG, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("F4 done")


def chord():
    t = pd.read_csv(TAB / "task_transitions.csv")
    t = t[t.src != t.dst]
    tot0 = t.groupby("src").n.sum().add(t.groupby("dst").n.sum(), fill_value=0)
    small = set(tot0[tot0 < 0.025 * tot0.sum()].index) | {"Other"}
    t = t.assign(src=t.src.where(~t.src.isin(small), "Other tasks"), dst=t.dst.where(~t.dst.isin(small), "Other tasks"))
    t = t[t.src != t.dst].groupby(["src", "dst"], as_index=False).n.sum()
    t = t[t.n >= 150]
    TASK_COL["Other tasks"] = "#8A94A6"
    groups = [g for g in TASK_COL if g in set(t.src) | set(t.dst)]
    out_ = t.groupby("src").n.sum().reindex(groups).fillna(0)
    in_ = t.groupby("dst").n.sum().reindex(groups).fillna(0)
    tot = out_ + in_
    gap = np.deg2rad(2.2)
    span = 2 * np.pi - gap * len(groups)
    scale = span / tot.sum()
    starts, a = {}, np.pi / 2
    for g in groups:
        starts[g] = a
        a -= tot[g] * scale + gap  # clockwise
    fig, ax = plt.subplots(figsize=(13, 13), dpi=200)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")
    R0 = 1.0
    cursor = {g: starts[g] for g in groups}
    seg = {}
    # outgoing first (ordered by destination), then incoming
    for g in groups:
        for _, row in t[t.src == g].sort_values("n", ascending=False).iterrows():
            w = row.n * scale
            seg[(g, row.dst, "out")] = (cursor[g], cursor[g] - w)
            cursor[g] -= w
    for g in groups:
        for _, row in t[t.dst == g].sort_values("n", ascending=False).iterrows():
            w = row.n * scale
            seg[(row.src, g, "in")] = (cursor[g], cursor[g] - w)
            cursor[g] -= w

    def pt(ang, r=R0):
        return (r * np.cos(ang), r * np.sin(ang))

    rows = t.sort_values("n")
    for _, row in rows.iterrows():
        a1, a2 = seg[(row.src, row.dst, "out")]
        b1, b2 = seg[(row.src, row.dst, "in")]
        arc1 = np.linspace(a1, a2, 30)
        arc2 = np.linspace(b1, b2, 30)
        verts = [pt(arc1[0])]
        codes = [MPath.MOVETO]
        for ang in arc1[1:]:
            verts.append(pt(ang)); codes.append(MPath.LINETO)
        verts += [(0, 0), pt(arc2[0])]
        codes += [MPath.CURVE3, MPath.CURVE3]
        for ang in arc2[1:]:
            verts.append(pt(ang)); codes.append(MPath.LINETO)
        verts += [(0, 0), pt(arc1[0])]
        codes += [MPath.CURVE3, MPath.CURVE3]
        frac = row.n / t.n.max()
        ax.add_patch(PathPatch(MPath(verts, codes), facecolor=TASK_COL[row.src], edgecolor=TASK_COL[row.src],
                               lw=0.3, alpha=0.30 + 0.45 * frac ** 0.5))
    for g in groups:
        a0 = starts[g]
        a1 = a0 - tot[g] * scale
        arc = np.linspace(a0, a1, 200)
        ax.plot(np.cos(arc) * 1.035, np.sin(arc) * 1.035, color=TASK_COL[g], lw=9, solid_capstyle="butt")
        am = (a0 + a1) / 2
        x, y = 1.10 * np.cos(am), 1.10 * np.sin(am)
        rot = np.rad2deg(am)
        ha = "left"
        if np.cos(am) < 0:
            rot += 180
            ha = "right"
        ax.text(x, y, f"{g}  {int(out_[g]):,} → · → {int(in_[g]):,}" if False else g, color=TASK_COL[g], fontsize=12.5,
                rotation=rot, rotation_mode="anchor", ha=ha, va="center", fontweight="bold")
    Sp = R["rq5"]
    ax.set_xlim(-1.75, 1.75)
    ax.set_ylim(-1.88, 2.12)
    ax.text(-1.72, 2.08, "Speciation: when a derivative changes its task", color=INK, fontsize=21, fontweight="bold", va="top")
    ax.text(-1.72, 1.96, f"{Sp['speciation_rate']:.1%} of {Sp['edges_with_both_tasks']:,} parent→child edges with known tasks cross a task group. "
                         f"Ribbons leave the parent's task and land on the child's;\nwidth ∝ number of edges, colour = parent task. "
                         f"Transitions with ≥150 edges shown; tasks with <2.5% of the flow are pooled as Other tasks.", color=MUTED, fontsize=11.5, va="top")
    top = Sp["top_pipeline_transitions"][0]
    ax.text(-1.72, -1.84, f"Largest single flow: {top['src']} → {top['dst']} ({top['n']:,} edges, "
                          f"{Sp['top_transition_share_of_changes']:.0%} of all pipeline changes): pretrained encoders becoming classifiers.",
            color="#C9D2E3", fontsize=11.5, va="bottom")
    fig.savefig(FIG / "F3_speciation_chord.png", facecolor=BG, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("F3 done")


if __name__ == "__main__":
    stream()
    chord()
