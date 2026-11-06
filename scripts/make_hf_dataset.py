#!/usr/bin/env python3
"""Assemble the Hugging Face dataset (thanatchon36/open-model-phylogeny) from the local research data.

Includes the pinned raw snapshot, the processed graph (run `make build layout` first), the results and the dataset card
(docs/hf_dataset_card.md). Files are hard-linked, so the staging folder takes no extra disk space. Stops if the raw
files do not match data/raw/SHA256SUMS. Writes to build/hf_dataset by default; upload with
    hf upload thanatchon36/open-model-phylogeny build/hf_dataset . --repo-type dataset
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ["nodes.parquet", "edges.parquet", "mft.zip", "SHA256SUMS"]
PROCESSED = ["nodes_conn.parquet", "edges_conn.parquet", "layout_radial.parquet", "wedges.csv"]


def verify_raw() -> None:
    for line in (ROOT / "data/raw/SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        if hashlib.sha256((ROOT / "data/raw" / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"{name} does not match SHA256SUMS: this is not the paper's snapshot")


def link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.link(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "hf_dataset"))
    out = Path(ap.parse_args().out)
    verify_raw()
    if out.exists():
        shutil.rmtree(out)
    for name in RAW:
        link(ROOT / "data/raw" / name, out / "data/raw" / name)
    for name in PROCESSED:
        link(ROOT / "data/processed" / name, out / "data/processed" / name)
    for path in sorted((ROOT / "results").rglob("*")):
        if path.is_file():
            link(path, out / path.relative_to(ROOT))
    link(ROOT / "docs/hf_dataset_card.md", out / "README.md")
    files = [p for p in out.rglob("*") if p.is_file()]
    print(f"{out}: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
