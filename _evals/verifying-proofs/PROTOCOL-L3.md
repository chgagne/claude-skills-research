# Protocol L3: the cost of default Lean certification

Written 2026-10-25, before any run. The researcher chose to make Lean certification the default for
serious findings, conditional on a cost re-measurement (journal, L2 decision record).

## Arm and material

The skill with the default Lean step (branch `lean-step`, b651504): every "step is false" finding, up to
five per paper, certified when Lean is available. The three documented-defect papers of L2 stage 2,
one run each, same prompt, tools (no web), scaffold (toolchain and project cloned into the run's
HOME), limits (100 turns, 40 minutes, $20 cap). Compared with L2 stage 2's reduced arm on the same
papers (/bin/zsh.64 per run, 6/6 found).

## Measures

Per run: wall time, cost, documented defect found (L2 scorer), Lean used (Bash calls to
`lean-certify.py`), certificates attempted, certificates CLEAN (recompiled by Claude), and for each
CLEAN certificate Claude's fidelity verdict (does it certify the finding on the paper's objects).
Timeouts and turn exhaustion are counted.

## Reading (no automatic decision)

Reported to the researcher, who decides on merging: cost and time per run against the reduced
skill, the share of runs that used Lean, the share of attempted certificates that came out CLEAN and
faithful. One condition blocks shipping regardless of cost: a CLEAN certificate presented as
certifying a finding when its statement does not (an unfaithful certificate reported as a
certificate). A defect found in stage 2 but missed here is reported as a regression.
