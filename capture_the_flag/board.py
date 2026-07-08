"""Board geometry for Capture the Flag.

The board is 12 columns x 12 rows: two 4-row home zones separated by a doubled
neutral buffer and two rows of lakes. These constants are the first concrete
brick; the GamePosition implementation will build on them.
"""

BOARD_COLUMNS = 12
BOARD_ROWS = 12

# Lake layout across the 12 columns of each of the two lake rows:
# 1 open | 2 lake | 2 open | 2 lake | 2 open | 2 lake | 1 open — three separate
# 2x2 lakes with single-column lanes at the edges. True = lake (impassable),
# False = open.
_L = True
_O = False
LAKE_PATTERN = (_O, _L, _L, _O, _O, _L, _L, _O, _O, _L, _L, _O)
