#!/bin/sh
# Render a markdown review to PDF.
#
#   sh build-review-pdf.sh review-<reviewer>-<YYYYMMDD>.md [out.pdf]
#
# Preferred route: pandoc + xelatex. If pandoc is missing, ASK the user before
# installing anything; a python-markdown + headless-Chrome fallback is described
# at the bottom of this file.
#
# Copy this script plus pandoc-header.tex and colwidths.lua into the paper
# directory (e.g. as review-assets/) so the review stays reproducible after the
# skill is gone.
set -e

SRC="${1:?usage: build-review-pdf.sh <review.md> [out.pdf]}"
OUT="${2:-${SRC%.md}.pdf}"
DIR="$(cd "$(dirname "$0")" && pwd)"

command -v pandoc  >/dev/null || { echo "pandoc not found — ask the user before installing"; exit 1; }
command -v xelatex >/dev/null || { echo "xelatex not found — ask the user before installing"; exit 1; }

# Charter is a macOS system serif with a real bold face. Substitute per platform;
# verify the chosen font actually resolves a bold face, or every **bold** in the
# review renders at regular weight and the emphasis silently disappears.
MAINFONT="${MAINFONT:-Charter}"
MONOFONT="${MONOFONT:-Menlo}"
LOG=$(mktemp)

pandoc "$SRC" -o "$OUT" \
  --pdf-engine=xelatex \
  --from=gfm+hard_line_breaks \
  --lua-filter="$DIR/colwidths.lua" \
  -H "$DIR/pandoc-header.tex" \
  -V geometry:margin=2cm \
  -V mainfont="$MAINFONT" \
  -V monofont="$MONOFONT" \
  -V monofontoptions="Scale=0.78" \
  -V fontsize=10pt \
  -V linkcolor=blue \
  --toc --toc-depth=2 2>"$LOG"

# A missing glyph is dropped silently from the PDF -- the character simply is
# not there, and the review reads as if you never wrote it. This has happened
# with U+223C (~) and U+2713 (check mark), both of which Charter lacks.
if grep -q "Missing character" "$LOG" 2>/dev/null; then
  echo "WARNING: characters were dropped from $OUT --" >&2
  grep -o "There is no [^ ]* (U+[0-9A-F]*)" "$LOG" | sort -u | sed 's/^/  /' >&2
  printf '  Replace them with ASCII in the .md, or map them with a\n' >&2
  printf '  newunicodechar entry in pandoc-header.tex, then rebuild.\n' >&2
fi
rm -f "$LOG"

echo "wrote $OUT"

# Checks worth running afterwards, because each has bitten before:
#   pdftoppm -r 100 -png "$OUT" /tmp/rev         -> then LOOK at the pages:
#       wide tables running off the right margin, bold not rendering,
#       metadata lines collapsed into one paragraph
#
# No-pandoc fallback (no installs needed if python3 + Chrome are present):
#   python3 -c "import markdown" && render with
#   markdown.markdown(src, extensions=['tables','fenced_code','sane_lists','nl2br'])
#   into a print-styled HTML page, then:
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
#     --no-pdf-header-footer --print-to-pdf=out.pdf file:///tmp/review.html
