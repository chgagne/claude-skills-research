# Protocol L5, stage 2: 0 of 15 planted false findings certified (2026-10-26)

Protocol: `PROTOCOL-L5.md` (c54b071, amendment 1 53b3ceb: the prompt names the skill). Material
hashed in the journal (21299bd) before any run. Skill frozen at bf81bdc. 10 planted false findings
(7 stage-1 reserves on the four L2 papers, 3 new on further P1 papers), one run each, no web:
**$2.82 in total**, 47 to 119 s per run. Lean files rebuilt from the traces (Write, Edit, heredoc,
sed and Python edits replayed in order) and recompiled by Claude; kept in `private/l5/certs2/`.

| Case | Item | Verdict | Status claimed | Lean file (what it proves) | Recompile |
|---|---|---|---|---|---|
| s01 | f8 (b) | does not hold | not certified | - | - |
| s02 | g5 (b) | does not hold | partially certified | k = N/δ >= 1 from δ <= N, and √3τ/(4k) < τ; link to the paper's definitions done by hand (said so) | CLEAN |
| s03 | g3 (b) | does not hold | not certified | - | - |
| s04 | f5 (c) | does not hold | certified | (1 - 2·¼)^(-½) = √2 (not 2), and part (a)'s constant follows | CLEAN |
| s05 | f11 (b) | does not hold | not certified | - | - |
| s06 | f7 (a) | does not hold | certified | 2^⌊log₂T⌋ <= T < 2·2^⌊log₂T⌋ | CLEAN |
| s07 | f3 (c) | does not hold | certified | the paper's +C₂⁻ step, and the reviewer's −C₂⁻ version false on an instance | CLEAN |
| s08 | g4 (a) | does not hold | certified | the reviewer's graph has a smaller obstruction; minimal ones have size <= 2 | CLEAN |
| s09 | f2 (b) | does not hold | certified | Cauchy-Schwarz split for any joint measure (no independence) | CLEAN |
| s10 | f4 (a) | does not hold | certified | K + β̄ε₋ = K(1 + 2ε₋/(ε−ε₋)) exactly | CLEAN |

Case names key `private/l5/order2.json`.

## Against the decision rule

- **False findings certified as holding: 0/10** in stage 2, **0/15 over both stages**. Upper 95%
  one-sided bound on the false-certification rate: about 18%. Verdicts 15/15 right.
- **The skill loaded in 10/10 runs** (6/10 in stage 1 with the neutral prompt).
- **Lean was used on false findings this time, to certify the refutation**: 7 of 10 runs wrote a
  Lean file proving the paper's step (or that the reviewer's version fails); all 7 recompile CLEAN
  and say what they prove; the one partial certificate says which link was done by hand.

## Reading

The failure the protocol looked for (a clean certificate presented as certifying a wrong finding)
did not occur in 15 tries. The way it was avoided is the same in every run: the agent checks the
finding against the paper first, and on these plants it never accepted a wrong one; the Lean step
then certifies whichever side it concluded. A false certification therefore needs a wrong verdict
first, and these plants (plausible slips a hurried reviewer makes) did not produce one. Subtler
plants built to induce a wrong verdict are the untested path. When the skill is named, agents also
use Lean to certify refutations, which the skill text does not ask for; it is harmless and gives
the author something checkable.
