#!/bin/bash
# protocol C, one case at a time, each batch behind the usage gate
X="${X:?set X to the run directory holding skill/, self/ and out/}"
GATE="$HOME/.claude/skills/_evals/_harness/usage_gate.py"
GR=(--allow-tools Bash Write Edit WebFetch WebSearch "WebFetch(domain:api.crossref.org)" "WebFetch(domain:export.arxiv.org)" "WebFetch(domain:sparql.dblp.org)" "WebFetch(domain:api.semanticscholar.org)" "WebFetch(domain:api.openalex.org)" "WebFetch(domain:doi.org)" "WebFetch(domain:api.biorxiv.org)" "WebFetch(domain:openlibrary.org)")
COMMON=(--runs 2 -j 2 --model claude-opus-5-5 --no-publish --trust-plugin --keep-temp --scaffold "${GR[@]}")
for c in lt1 lt2 lt3 lt4 lt5 lt6; do
  [ -s "$X/out/$c.skill.json" ] && [ -s "$X/out/$c.self.json" ] && continue
  python3 "$GATE" --five 0.40 --seven 0.75
  claude plugin eval "$X/skill/verifying-bibliography" --case "$c" --ablation with-without --json "$X/out/$c.skill.json" "${COMMON[@]}" </dev/null >> "$X/out/run.log" 2>&1
  claude plugin eval "$X/self/self-verifying-bibliography" --case "$c" --ablation none --json "$X/out/$c.self.json" "${COMMON[@]}" </dev/null >> "$X/out/run.log" 2>&1
  echo "$(date +%H:%M) $c done" >> "$X/out/progress.log"
done
echo ALLDONE >> "$X/out/progress.log"
