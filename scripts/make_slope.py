"""
Builds the slope overlay for the map from the Jezero CTX DEM (20 m/pixel).

Input : data/jezero_ctx_dem_20m.tif  (USGS / Mars 2020 TRN, equirectangular, Mars sphere R = 3,396,190 m)
Output: data/slope.png        coloured slope (green / yellow / red, transparent where there is no data)
        data/slope_meta.json  lon/lat bounds of the image + thresholds, read by index.html

Run:  .venv/Scripts/python scripts/make_slope.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))   # so "terrain" is found from any folder
from terrain import Terrain

ROOT = Path(__file__).resolve().parent.parent

# Walkability classes in degrees:
#   > 20°  avoid on foot. NASA's xEVA suit requirement: a suited astronaut must be able to walk up,
#          down and across a 20-degree slope (xEVA System Requirements Document, cited in Scoville 2021,
#          https://ntrs.nasa.gov/citations/20210026296).
#   10–20° careful. Our own safety margin (half of the suit limit), not a NASA number.
#   < 10°  easy walking.
EASY, HARD = 10.0, 20.0

t = Terrain()
z, slope, rows, cols = t.z, t.slope, t.rows, t.cols
west, north, east, south = t.west, t.north, t.east, t.south

rgba = np.zeros((rows, cols, 4), dtype=np.uint8)
valid = np.isfinite(slope)
for mask, colour in [
    (valid & (slope < EASY), (46, 204, 113, 45)),                 # green
    (valid & (slope >= EASY) & (slope < HARD), (241, 196, 15, 150)),  # yellow
    (valid & (slope >= HARD), (231, 76, 60, 180)),                 # red
]:
    rgba[mask] = colour
Image.fromarray(rgba, "RGBA").save(ROOT / "data" / "slope.png", optimize=True)

s = slope[valid]
meta = {
    "bounds": [[south, west], [north, east]],
    "thresholds_deg": {"easy": EASY, "hard": HARD},
    "source": "Jezero CTX DTM 20 m (JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m), USGS Astrogeology / Mars 2020 TRN",
    "stats_pct": {
        "easy": round(100 * float((s < EASY).mean()), 1),
        "careful": round(100 * float(((s >= EASY) & (s < HARD)).mean()), 1),
        "avoid": round(100 * float((s >= HARD).mean()), 1),
    },
    "elevation_m": [round(float(np.nanmin(z)), 1), round(float(np.nanmax(z)), 1)],
}
(ROOT / "data" / "slope_meta.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta, indent=2))
print("max slope:", round(float(s.max()), 1), "deg · median:", round(float(np.median(s)), 1), "deg")
