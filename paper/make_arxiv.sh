#!/usr/bin/env bash
# Build the arXiv submission bundle paper/arxiv.tar.gz from paper/paper.tex.
#
# arXiv compiles with pdfLaTeX. The bibliography is inline, so no .bbl is needed: the bundle holds paper.tex, the
# generated macros, tables and ledger, and only the figures the paper uses. The script compiles the bundle in a clean
# directory to prove it stands alone. Needs tectonic on PATH, or its path in $TECTONIC. Usage:
#   bash paper/make_arxiv.sh
set -euo pipefail
cd "$(dirname "$0")"
TECTONIC=${TECTONIC:-tectonic}
STAGE=$(mktemp -d)
CHECK=$(mktemp -d)
trap 'rm -rf "$STAGE" "$CHECK"' EXIT

cp paper.tex macros.tex ledger.tex "$STAGE/"
for t in $(grep -o '\\input{tab_[^}]*}' paper.tex | sed 's/\\input{\(.*\)}/\1/' | sort -u); do
  cp "$t.tex" "$STAGE/"
done
mkdir -p "$STAGE/figs"
for f in $(grep -o '\\includegraphics\(\[[^]]*\]\)\?{[^}]*}' paper.tex | sed 's/.*{\(.*\)}/\1/' | sort -u); do
  cp "$f" "$STAGE/figs/"
done

# tectonic is XeTeX-based, so the check runs before \pdfoutput=1 is added; that line only tells arXiv to use pdfLaTeX.
cp -r "$STAGE/." "$CHECK/"
(cd "$CHECK" && "$TECTONIC" --keep-logs paper.tex >/dev/null 2>&1)
if grep -qi 'citation.*undefined\|reference.*undefined' "$CHECK/paper.log"; then
  grep -i 'citation.*undefined\|reference.*undefined' "$CHECK/paper.log" >&2
  echo "arXiv bundle has undefined citations or references" >&2
  exit 1
fi
{ echo '\pdfoutput=1 % arXiv: process with pdfLaTeX'; cat paper.tex; } > "$STAGE/paper.tex"

tar -czf arxiv.tar.gz -C "$STAGE" .
echo "built $(pwd)/arxiv.tar.gz ($(tar -tzf arxiv.tar.gz | grep -vc '/$') files); upload it at https://arxiv.org/submit"
