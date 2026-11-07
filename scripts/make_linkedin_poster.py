#!/usr/bin/env python3
"""Portrait LinkedIn poster (4:5, 2160 x 2700 px) for the working draft. Writes docs/assets/linkedin_poster.png.

The poster is the radial chronogram (F1) with a title, one headline number per research question and the links.
Every number is read from results/results.json, so the poster cannot disagree with the paper. The tree is cut out
of the full F1 render (figures/F1_tree_of_open_models_5000.png, made by `make figures`); without it the script
falls back to the paper's copy, paper/figs/f1.jpg, which is smaller.

Design: the figures' own dark surface and type (Inter), near-white ink for every number and label, one warm accent
for the kickers and rules, and no other colour, so that the tree is the only coloured thing on the page. Inter is
found among the system fonts, or pass --font-dir with its .ttf files; without it the poster falls back to DejaVu Sans.

Usage: python scripts/make_linkedin_poster.py [--font-dir DIR]
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from PIL import Image  # noqa: E402

from common import BG, INK, MUTED, font_setup  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--font-dir", help="directory with Inter .ttf files, if Inter is not installed")
args = ap.parse_args()
if args.font_dir:
    for f in glob.glob(str(Path(args.font_dir) / "*.ttf")):
        font_manager.fontManager.addfont(f)
font_setup()
if not any(f.name == "Inter" for f in font_manager.fontManager.ttflist):
    print("warning: Inter not found, falling back to DejaVu Sans (pass --font-dir)", file=sys.stderr)

W, H, DPI = 10.8, 13.5, 200          # inches; 2160 x 2700 px
L, R = 0.6, W - 0.6                  # side margins
GOLD = "#E2B04A"                     # accent: kickers, rules, tile labels
INK_2 = "#C9D2E3"                    # secondary text (the figures' caption colour)
PAPER_URL = "thanatchon36.github.io/open-model-phylogeny"
CODE_URL = "github.com/thanatchon36/open-model-phylogeny"
DATA_URL = "huggingface.co/datasets/thanatchon36/open-model-phylogeny"
DOI = "10.5281/zenodo.24029159"

# ------------------------------------------------------------------ numbers, all from results.json
R_ = json.loads((ROOT / "results" / "results.json").read_text())
O, S, Hy, T, A, Sp = R_["overview"], R_["rq1"], R_["rq2"], R_["rq3"], R_["rq4"], R_["rq5"]
rt = T["reaction_median_days_by_half"]
pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
tiles = [
    ("Structure", pct(S["top1pct_roots_share_of_connected"]),
     f"of connected models\ndescend from the top 1%\nof bases ({S['top1pct_roots_n']:,} roots)"),
    ("Hybridisation", f"{Hy['assortativity_ratio_related']:.0f}×",
     f"more often than chance,\na merge joins relatives\n({pct(Hy['related_share'])} vs {pct(Hy['null_related_share_mean'])} random)"),
    ("Tempo", f"{rt['2026H1']['finetune']:.1f} days",
     f"median wait for a major\nbase's first fine-tune in\n2026, from {rt['2023H2']['finetune']:.1f} in 2023"),
    ("Attention", pct(A["share_child_downloads_top1pct"]),
     f"of derivative downloads\ngo to the top 1% of them;\n{pct(A['share_children_dormant_30d'])} had none in 30 days"),
    ("Speciation", pct(Sp["speciation_rate"]),
     "of lineage links change\ntask group, most often\nfill-mask → classifier"),
]
assert Sp["top_pipeline_transitions"][0]["src"] == "fill-mask" and \
    Sp["top_pipeline_transitions"][0]["dst"] == "text-classification"

# ------------------------------------------------------------------ the tree, cut out of the F1 render
SIZE_IN = 8.5                                       # inches on the poster
TOP = 2.45
src_png = ROOT / "figures" / "F1_tree_of_open_models_5000.png"
src = src_png if src_png.exists() else ROOT / "paper" / "figs" / "f1.jpg"
img = Image.open(src).convert("RGB")
side = img.size[0]                                  # the F1 canvas is square
f = side / 1600                                     # fig_hero.py scales its typography by this factor
scale = 0.5 * side * 0.86                           # radius 1 -> pixels, as in fig_hero.py
cx, cy = side / 2, side * 0.515
r_out = 0.965 * scale                               # outermost model (layout.R_OUT)
r_crop = r_out + 26 * f + 36 * f                    # rim labels sit at r_out + 26 f; keep their full height
r_crop = int(round(r_crop))
box = (int(round(cx - r_crop)), int(round(cy - r_crop)))
disc = np.asarray(img.crop((box[0], box[1], box[0] + 2 * r_crop, box[1] + 2 * r_crop)), dtype=np.float32)
bg = np.array([int(BG[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
yy, xx = np.mgrid[0:2 * r_crop, 0:2 * r_crop]
dist = np.hypot(xx - r_crop + 0.5, yy - r_crop + 0.5)
# F1 draws its title block at the top of the canvas and its legend at the bottom, in greys, just outside the disc.
# Beyond the wedge arcs (r_out + 10 f), in those two bands, everything grey is that chrome; the rim labels are
# saturated palette colours and stay.
band = (yy + box[1] < 150 * f) | (yy + box[1] > side - 110 * f)
grey = (disc.max(axis=2) - disc.min(axis=2) < 60) & (disc.max(axis=2) > 25)
disc[band & grey & (dist > r_out + 14 * f)] = bg
# circular cut, feathered
alpha = np.clip(r_crop - dist, 0, 3) / 3
disc = disc * alpha[..., None] + bg * (1 - alpha[..., None])
px = int(round(SIZE_IN * DPI))
tree = Image.fromarray(disc.astype(np.uint8)).resize((px, px), Image.LANCZOS)

# ------------------------------------------------------------------ canvas in inches from the top-left corner
fig = plt.figure(figsize=(W, H), dpi=DPI, facecolor=BG)
cv = fig.add_axes([0, 0, 1, 1], zorder=0)
cv.set_xlim(0, W)
cv.set_ylim(H, 0)
cv.axis("off")
texts = []


def text(x, y, s, size, color=INK, weight="normal", ha="left", va="top", **kw):
    t = cv.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, parse_math=False, **kw)
    texts.append(t)
    return t


def lines(x, y0, s, size, color, pitch, **kw):
    """Multi-line text on a fixed baseline grid."""
    return [text(x, y0 + k * pitch, line, size, color, va="baseline", **kw) for k, line in enumerate(s.split("\n"))]


def caps(s: str) -> str:
    return " ".join(s.upper())


def hline(y, x0=L, x1=R, color=GOLD, lw=0.8, alpha=0.5):
    cv.plot([x0, x1], [y, y], color=color, lw=lw, alpha=alpha, solid_capstyle="butt")


# ------------------------------------------------------------------ title band
text(L, 0.42, caps("Working draft") + "   ·   " + caps("November 2026"), 10.5, GOLD, va="center")
text(R, 0.42, caps("Thanatchon Chongmankhong"), 10.5, GOLD, ha="right", va="center")
hline(0.64)
title = text(L - 0.04, 0.84, "The Tree of Open Models", 50, INK, "bold")
subtitle = text(L, 1.68, f"Every Hugging Face model that declares a parent or has a child, drawn as one phylogeny: "
                         f"{O['n_connected']:,} models\njoined by {O['n_edges']:,} lineage links, "
                         f"{pct(O['share_declare_parent'])} of the Hub's {O['n_models_hub']:,} models. "
                         "Snapshot of 5 November 2026.",
                12.5, INK_2, linespacing=1.4)

# ------------------------------------------------------------------ the tree
x0 = (W - SIZE_IN) / 2
ax = fig.add_axes([x0 / W, 1 - (TOP + SIZE_IN) / H, SIZE_IN / W, SIZE_IN / H], zorder=1)
ax.imshow(np.asarray(tree), interpolation="none")
ax.axis("off")
key = lines(L, TOP + SIZE_IN + 0.1,
            "Angle = lineage, offspring sweeping around their base in birth order   ·   "
            "Radius = creation date, 2022 at the centre to November 2026 at the rim   ·   Colour = family\n"
            f"Pale bundled curves = {Hy['n_hybrids']:,} merged models with two or more parents   ·   "
            "Stars = the most-descended bases, brightness = all-time downloads", 8.6, MUTED, 0.16)

# ------------------------------------------------------------------ one number per research question
y = TOP + SIZE_IN + 0.42
hline(y, alpha=0.35)
col = (R - L) / len(tiles)
caption_lines = []
for i, (label, value, caption) in enumerate(tiles):
    x = L + i * col
    if i:
        cv.plot([x - 0.14, x - 0.14], [y + 0.16, y + 1.28], color=INK, lw=0.5, alpha=0.16)
    text(x, y + 0.28, caps(label), 9, GOLD, "bold", va="baseline")
    text(x - 0.02, y + 0.69, value, 32, INK, "semibold", va="baseline")
    caption_lines += lines(x, y + 0.92, caption, 8.8, INK_2, 0.165)

# ------------------------------------------------------------------ footer
F = y + 1.46
hline(F, alpha=0.35)
text(L, F + 0.17, "Thanatchon Chongmankhong", 10.5, INK, "bold", va="baseline")
text(R, F + 0.17, "Data: Open Model Family Tree (h9-tec), CC BY 4.0, from the hub-stats dump of Hugging Face Hub metadata",
     8, MUTED, ha="right", va="baseline")
link_rows = [[("Paper", PAPER_URL), ("Code", CODE_URL)], [("Data", DATA_URL), ("DOI", DOI)]]
for j, row in enumerate(link_rows):
    yy_ = F + 0.36 + j * 0.17
    for k, (name, url) in enumerate(row):
        xx_ = L + k * 5.1
        text(xx_, yy_, caps(name), 7.8, GOLD, "bold", va="baseline")
        text(xx_ + 0.62, yy_, url, 9, INK_2, va="baseline")

# ------------------------------------------------------------------ fit checks: nothing may overflow its column
fig.canvas.draw()
rend = fig.canvas.get_renderer()
w_px = lambda t: t.get_window_extent(rend).width / DPI  # noqa: E731
assert w_px(title) < R - L + 0.1, f"title too wide: {w_px(title):.2f} in"
for t in caption_lines:
    assert w_px(t) < col - 0.26, f"caption line too wide: {t.get_text()!r} ({w_px(t):.2f} in)"
for t in texts:
    bb = t.get_window_extent(rend)
    assert bb.x1 / DPI <= R + 0.05, f"text past the right margin: {t.get_text()[:40]!r} ({bb.x1 / DPI:.2f} in)"
    assert bb.y0 / DPI >= 0.1, f"text past the bottom edge: {t.get_text()[:40]!r}"

out = ROOT / "docs" / "assets" / "linkedin_poster.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, dpi=DPI, facecolor=BG)
Image.open(out).convert("RGB").save(out, optimize=True)  # opaque RGB PNG for LinkedIn
im = Image.open(out)
print(out, im.size, f"tree from {src.name}")
