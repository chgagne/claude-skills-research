-- Pandoc filter: give every table explicit relative column widths.
--
-- Without this, pandoc emits pipe tables with no width information and LaTeX
-- sets them as unwrappable columns. Wide audit tables then run off the right
-- margin and the rightmost column -- usually the "Correct" entry, i.e. the
-- actual content of the finding -- is silently truncated in the PDF.
--
-- Tune the entries below per document if a particular table reads badly.

local WIDTHS = {
  [2] = {0.30, 0.70},
  [3] = {0.27, 0.27, 0.46},
  [4] = {0.25, 0.25, 0.25, 0.25},
  [5] = {0.20, 0.20, 0.20, 0.20, 0.20},
}

function Table(tbl)
  local n = #tbl.colspecs
  local w = WIDTHS[n]
  for i = 1, n do
    tbl.colspecs[i][2] = w and w[i] or (1.0 / n)
  end
  return tbl
end
