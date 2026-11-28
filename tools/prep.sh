# A paper's inputs, made in one go: what a generating agent needs beside DESIGN.md before it can start.
#   bash tools/prep.sh <video> <paper.pdf>          (Linux, macOS or Git Bash; needs pixi, which fetches poppler)
# Writes <video>/src/paper.pdf, src/paper.txt (pdftotext -layout, UTF-8), src/hi-NN.png (300 dpi) and
# src/lo-NN.png (80 dpi) for every page, assets/front.png for front_page(), and a brief.md with the source
# section filled in from the PDF and the three choices that are the user's -- audience, format, length --
# left as TODO lines. tools/brief.sh refuses a brief that still has one, so a default is never taken by
# accident. Marks `received` and `figures` in the video's timelog.
# On geant4 this was fourteen minutes done by hand, most of it finding which PDF tool was installed where.
set -euo pipefail
source "$(dirname "$0")/platform.sh"
V=${1:?usage: bash tools/prep.sh <video> <paper.pdf>}
PDF=${2:?usage: bash tools/prep.sh <video> <paper.pdf>}
R="$(cd "$(dirname "$0")/.." && pwd)"
D="$R/$V"; [ -d "$D" ] || [ ! -d "$R/private" ] || D="$R/private/$V"   # with a private/, new videos go there
[ -f "$PDF" ] || { echo "no such file: $PDF" >&2; exit 2; }
[ ! -f "$D/brief.md" ] || { echo "$V/brief.md exists: this video already has its inputs (delete it to start over)" >&2; exit 2; }
# paperstore checks the plan's cite quotes (vlint plan): take its latest for each new video, in the render env
[ -d "$RENDER_ROOT" ] && { (cd "$RENDER_ROOT" && cp "$R/pixi.toml" . && pixi update -q paperstore) >&2 \
  || echo "prep: paperstore not refreshed in the render env" >&2; }
pp() { pixi exec -s poppler "$@" 2> >(grep -v -E "Invalid XRef entry|No display font|Syntax (Error|Warning)" >&2); }

mkdir -p "$D/src" "$D/assets"
pyhost "$R/tools/timelog.py" mark "$V" received
cp "$PDF" "$D/src/paper.pdf"
cd "$D/src"
pyhost "$R/tools/timelog.py" mark "$V" figures --note "tools/prep.sh"
pp pdftotext -layout -enc UTF-8 -eol unix paper.pdf paper.txt
pp pdftoppm -r 300 -png paper.pdf hi
pp pdftoppm -r 80 -png paper.pdf lo
# pdftoppm pads the page number to the width of the page count, so a 9-page paper comes out as hi-1.png
# and a 14-page one as hi-01.png. Every script here reads hi-NN (si_psf, the first paper under ten pages).
for f in hi-?.png lo-?.png; do [ -f "$f" ] && mv "$f" "${f%-*}-0${f#*-}"; done
pp pdftoppm -f 1 -l 1 -r 110 -png -singlefile paper.pdf ../assets/front
info="$(pp pdfinfo paper.pdf)"
pages=$(echo "$info" | sed -n 's/^Pages: *//p')
title=$(echo "$info" | sed -n 's/^Title: *//p' | sed 's/ *$//')
# no Title in the metadata (pet_mrpc, an arXiv preprint): the first run of text lines on page 1, which is the title
# on nearly every paper. Said as a guess in the brief, for the agent to check against the front page.
if [ -z "$title" ]; then
  # an author line (names with affiliation marks, "Yi1,2,3," or "Lee*", three commas, or an e-mail) ends the title
  guess=$(awk 't && /[a-z][0-9]+(,[0-9]+)*[, ]|[a-z][*†‡]|,.*,.*,|@/ { exit }
               NF && !/arXiv|[Pp]repared for|[Ss]ubmitted to|[Pp]reprint|^[ \t]*[0-9]+[ \t]*$/ { gsub(/^[ \t]+|[ \t]+$/, ""); t = t (t ? " " : "") $0; n++; if (n == 3) exit; next }
               t { exit } END { print t }' paper.txt)
  [ -n "$guess" ] && title="\"$guess\" (title read off page 1; check it)"
fi
size=$(echo "$info" | sed -n 's/^Page size: *//p')
# where each figure and table is: the page of every caption (pdftotext ends a page with a form feed)
caps=$(awk 'BEGIN { p = 1 }
  { p += gsub(/\f/, ""); s = $0                       # a form feed opens the first line of the next page
    # a caption opens a line or a column; "as shown in Figure 3." in the prose does not
    # "Fig. 1 Spatial self-interference..." has no colon at all (Nature Communications: si_psf found none)
    while (match(s, /(^ *|   +)(Figure|Fig\.|Table|TABLE) +[0-9IVX]+([:.]| +[A-Z])/)) {
      c = substr(s, RSTART, RLENGTH); sub(/^ +/, "", c); sub(/([:.]| +[A-Z])$/, "", c)
      print "  - page " p ": " c; s = substr(s, RSTART + RLENGTH) } }' paper.txt \
  | sort -u -t: -k2,2 | sort -s -t' ' -k6,6 -k7,7n | sort -s -t' ' -k5,5n)
# a table whose caption is in the text and whose cells are not is an image in the PDF: number-unsourced
# cannot see its numbers either way (pet_hetero_nn, Tables II and IV)
words=$(wc -w < paper.txt)
# What may be reused: the paper's own licence line, and every figure credited to someone else. A CC BY paper's
# licence does not cover a figure it reproduced "with permission" (Kraan 2015: Figs 3, 9 and 11, cropped before
# anyone read the captions), and "NoDerivatives" rules out a crop (prototwin_pet). Found by hand twice.
lic=$( (grep -iE "creative ?commons|CC[ -]BY|open[ -]access|all rights reserved|no ?derivative" paper.txt || true) | sed 's/^ */  - /; s/  */ /g' | cut -c1-160 | sort -u | head -4)
cred=$(awk 'BEGIN { p = 1 } { p += gsub(/\f/, "") }
  tolower($0) ~ /(reproduced|adapted|reprinted|redrawn|taken) (from|with)|with permission|courtesy of/ {
    s = $0; gsub(/^ +| +$/, "", s); gsub(/  +/, " ", s); print "  - page " p ": " substr(s, 1, 130) }' paper.txt | head -12)

cat > "$D/brief.md" <<BRIEF
# $V: brief (the inputs, and nothing else)

The words, the scene list, the pictures and the cue on every clause are the generating agent's to decide
(DESIGN Part III). What is written down here is a constraint, not a decision already made for you: the
source, who is watching, the format the video is in, and what has already been cut out of the paper so
you do not have to cut it again.

## Source

\`src/paper.pdf\` -- ${title:-TODO: authors, title, venue, year}. $pages pages ($size).
TODO: authors, venue and year if the line above lacks them; where the body ends; what kind of paper it is.
The front page names the authors, so nothing on screen needs to list them again (vlint \`authors-brief\`).
Its text is \`src/paper.txt\` (\`pdftotext -layout\`, UTF-8, $words words). Its pages are \`src/hi-NN.png\`
(300 dpi) and \`src/lo-NN.png\` (80 dpi, for reading a page at a glance).

## What may be reused

Licence lines found in the text (none found means all rights reserved until the front page says otherwise):
${lic:-  - (none found)}
Figures credited to another source, which this paper's licence does not cover (redraw them from their numbers):
${cred:-  - (none found)}
An open licence without "NoDerivatives" lets a figure be cropped; anything else is redrawn, or shown whole and small
as the paper's page (DESIGN Part II, "Reusing a figure").

## Audience

TODO: who is watching. The default is DESIGN's opening, a PET physics PhD and colleagues; say so if it is.

## Format

TODO: the default (one drawn figure per scene), or a walk through the paper (DESIGN Part II).

## What is already cut from the paper, and how to cut more

Which parts of the paper the video uses is yours to choose. These are spare parts, not a route.

- \`assets/front.png\` -- page 1 at 110 dpi, for \`front_page()\`.
- \`src/hi-NN.png\`, \`src/lo-NN.png\` -- every page. Nothing has been cropped from them. Captions found in
  the text:
${caps:-  - (none found: look at the pages)}
- More: \`pixi exec -s pillow -s numpy python tools/figcrop.py $V <page> <name>.png x0 y0 x1 y1\` cuts a
  figure into assets/ from a rough box in page fractions (stop it above the caption); it grows each edge until it
  runs through white paper, so tick numbers and axis titles are never cut (DESIGN Part II, "Reusing a figure").

**What the text does not hold.** vlint \`number-unsourced\` holds every number you say or show against
\`paper.txt\`. A chart's bar heights are not in it, and neither are the cells of a table the PDF stores as
an image: look at the page before trusting the text for either. Take the paper's numbers from its prose
where it gives them; where you read one off a figure or a page, say so on the line that carries it
(\`# vlint: ignore[number-unsourced] read off Fig. 5: ...\`).

## Constraints

- Every number on screen is the paper's own, or is marked as above.
- TODO: length. The default is 5 to 8 minutes.
- Never above 1080p.

\`received\` and \`figures\` are already marked in \`timelog.json\` (tools/prep.sh). Mark \`script\`, \`check\`,
\`render\` and \`sent\` as you pass them.
BRIEF
echo "== $V: $pages pages, $words words, $(ls hi-*.png | wc -l) page renders, front page"
echo "$caps"
echo "== fill in the TODO lines of $V/brief.md, then: bash tools/brief.sh $V"
