#!/usr/bin/env python3
"""Radial chronogram layout for the hero figure (F1) and the explorer.

angle  : super-family wedges in RING_ORDER; inside, each root's primary subtree gets an
         angular interval proportional to its size; children are laid out in birth order,
         so a parent's offspring sweep around it as they appear.
radius : date of creation, linear from 2022-03 (inner ring) to the snapshot (outer ring).
"""
import numpy as np
import pandas as pd

from common import PROC, RING_ORDER, SNAP, super_of

R_IN, R_OUT = 0.13, 0.965
T0 = pd.Timestamp("2022-03-01")
GAP_DEG = 1.6


def radius_of(ts):
    t = ((pd.to_datetime(ts) - T0).total_seconds() / ((SNAP - T0).total_seconds()))
    return R_IN + (R_OUT - R_IN) * np.clip(t, 0, 1)


def main():
    nd = pd.read_parquet(PROC / "nodes_conn.parquet",
                         columns=["id", "created", "ghost", "n_par", "n_kid", "primary", "root", "sub", "family", "topo"])
    M = len(nd)
    prim = nd["primary"].values
    sub = nd["sub"].values
    day = ((nd["created"] - T0).dt.total_seconds() / 86400).values
    span = (SNAP - T0).total_seconds() / 86400
    r = R_IN + (R_OUT - R_IN) * np.clip(day / span, 0, 1)
    r[np.isnan(day)] = np.nan
    # backfilled (pre-2022-03) models sit just inside the first ring
    r[day < 1] = R_IN * 0.82
    sup = super_of(nd["family"].values)

    # children in birth order (ties: topological order)
    dfill = np.where(np.isnan(day), -1e9, day)
    birth = np.lexsort((nd["topo"].values, dfill))
    kids = birth[prim[birth] >= 0]
    par = prim[kids]
    s = np.argsort(par, kind="stable")
    kid_csr = kids[s]
    ptr = np.concatenate([[0], np.cumsum(np.bincount(par, minlength=M))])

    roots = np.flatnonzero(prim < 0)
    rf = pd.DataFrame({"v": roots, "sup": sup[roots], "fam": nd["family"].values[roots], "size": sub[roots]})
    rf["sup_rank"] = rf["sup"].map({k: i for i, k in enumerate(RING_ORDER)})
    famsize = rf.groupby("fam")["size"].sum()
    rf["fam_size"] = rf["fam"].map(famsize)
    rf = rf.sort_values(["sup_rank", "fam_size", "fam", "size"], ascending=[True, False, True, False])

    n_sup = rf["sup"].nunique()
    total = 2 * np.pi - np.deg2rad(GAP_DEG) * n_sup
    w = total / M
    theta = np.zeros(M)
    start = 0.0
    prev_sup = None
    kid_l, ptr_l, sub_l = kid_csr.tolist(), ptr.tolist(), sub.tolist()
    th = theta.tolist()
    for v, sp in zip(rf["v"].tolist(), rf["sup"].tolist()):
        if sp != prev_sup:
            if prev_sup is not None:
                start += np.deg2rad(GAP_DEG)
            prev_sup = sp
        stack = [(v, start)]
        while stack:
            u, s0 = stack.pop()
            th[u] = s0 + sub_l[u] * w / 2
            a = s0
            ch = kid_l[ptr_l[u]:ptr_l[u + 1]]
            pos = []
            for k in ch:
                pos.append((k, a))
                a += sub_l[k] * w
            stack.extend(reversed(pos))
        start += sub_l[v] * w
    theta = np.array(th)

    # ghosts (unknown date): just inside their earliest child
    gh = np.flatnonzero(np.isnan(r))
    if len(gh):
        e = pd.DataFrame({"p": prim[kids], "r": r[kids]}).groupby("p")["r"].min()
        r[gh] = np.maximum(R_IN * 0.75, e.reindex(gh).fillna(R_IN).values - 0.012)
    ang = theta - np.pi / 2  # start at 12 o'clock, clockwise when y is flipped
    x, y = r * np.cos(ang), r * np.sin(ang)
    wedges = rf.assign(theta=theta[rf["v"].values]).groupby("sup")["theta"].agg(["min", "max"])
    out = pd.DataFrame({"theta": theta, "r": r, "x": x, "y": y, "super": sup})
    out.to_parquet(PROC / "layout_radial.parquet", index=False)
    wedges.to_csv(PROC / "wedges.csv")
    print("layout done", M, "nodes; wedges:\n", (np.rad2deg(wedges)).round(1))


if __name__ == "__main__":
    main()
