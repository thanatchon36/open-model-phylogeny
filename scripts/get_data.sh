#!/usr/bin/env bash
# Verify (or fetch) the lineage snapshot used by the paper: Open Model Family Tree, 2026-11-05.
# Files come from our Hugging Face dataset at a fixed revision, because upstream `data-latest` is rebuilt nightly.
set -euo pipefail
cd "$(dirname "$0")/../data/raw"
BASE=https://huggingface.co/datasets/thanatchon36/open-model-phylogeny/resolve/bea629e47d04a36b9b13e827dc88af84d3048715/data/raw
for f in nodes.parquet edges.parquet mft.zip; do
  [ -f "$f" ] || { echo "downloading $f (pinned 2026-11-05 snapshot)"; curl -fL -o "$f" "$BASE/$f"; }
done
if command -v sha256sum >/dev/null; then CHECK="sha256sum -c --quiet"; else CHECK="shasum -a 256 -c --quiet"; fi
if $CHECK SHA256SUMS; then
  echo "OK: data/raw matches the 2026-11-05 snapshot used in the paper."
else
  echo "WARNING: data/raw differs from the paper snapshot (2026-11-05). Results will change; log it as a new study version."
fi
