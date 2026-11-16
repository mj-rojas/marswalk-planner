"""
Exports the slope grid around the crew base as a small binary file, so the map can plan a walk to any
point in the browser (click on the map) with the same rules as make_route.py.

Input : data/jezero_ctx_dem_20m.tif
Output: data/slope_grid.bin   slope in hundredths of a degree, 16-bit unsigned, row by row from the north-west
        data/slope_grid.json  size and position of the grid, and the planning numbers the browser needs

Run:  .venv/Scripts/python scripts/make_grid.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from terrain import Terrain

ROOT = Path(__file__).resolve().parent.parent
NORTH, SOUTH, WEST, EAST = 18.56, 18.40, 77.25, 77.46   # covers the base, Cheyava Falls and Three Forks
NODATA = 65535

t = Terrain()
r0, c0 = t.cell(NORTH, WEST)
r1, c1 = t.cell(SOUTH, EAST)
win = t.slope[r0:r1, c0:c1]
grid = np.where(np.isfinite(win), np.minimum(np.round(win * 100), NODATA - 1), NODATA).astype("<u2")
grid.tofile(ROOT / "data" / "slope_grid.bin")

meta = {
    "rows": int(grid.shape[0]), "cols": int(grid.shape[1]),
    "north": t.north - r0 * t.dlat, "west": t.west + c0 * t.dlon,   # outer edge of the first cell
    "dlat": t.dlat, "dlon": t.dlon, "cell_m": t.sy,
    "scale": 100, "nodata": NODATA,
    "walkback_limit_min": 30,   # shortest walkback design case in Ogilvie et al. (2026)
}
(ROOT / "data" / "slope_grid.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
print(json.dumps(meta, indent=1))
print(f"{grid.size} cells · {100 * np.mean(grid == NODATA):.1f}% without data")
