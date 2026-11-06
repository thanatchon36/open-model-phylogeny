#!/usr/bin/env bash
# Verify (or fetch) the lineage snapshot used by the paper: Open Model Family Tree, 2026-11-05.
# Upstream `data-latest` is rebuilt nightly, so a fresh download is a NEWER snapshot and will not match SHA256SUMS.
set -euo pipefail
cd "$(dirname "$0")/../data/raw"
BASE=https://github.com/h9-tec/model-family-tree/releases/download/data-latest
for f in nodes.parquet edges.parquet; do
  [ -f "$f" ] || { echo "downloading $f (latest upstream snapshot)"; curl -fL -o "$f" "$BASE/$f"; }
done
[ -f mft.zip ] || curl -fL -o mft.zip https://codeload.github.com/h9-tec/model-family-tree/zip/refs/heads/main
if command -v sha256sum >/dev/null; then CHECK="sha256sum -c --quiet"; else CHECK="shasum -a 256 -c --quiet"; fi
if $CHECK SHA256SUMS; then
  echo "OK: data/raw matches the 2026-11-05 snapshot used in the paper."
else
  echo "WARNING: data/raw differs from the paper snapshot (2026-11-05). Results will change; log it as a new study version."
fi
