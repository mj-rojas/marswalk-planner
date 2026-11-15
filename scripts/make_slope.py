"""
Builds the slope overlay for the map from the Jezero CTX DEM (20 m/pixel).

Input : data/jezero_ctx_dem_20m.tif  (USGS / Mars 2020 TRN, equirectangular, Mars sphere R = 3,396,190 m)
Output: data/slope.png        coloured slope (green / yellow / red, transparent where there is no data)
        data/slope_meta.json  lon/lat bounds of the image + thresholds, read by index.html

Run:  .venv/Scripts/python scripts/make_slope.py
"""
import json
import math
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DEM = ROOT / "data" / "jezero_ctx_dem_20m.tif"

# Walkability classes in degrees. Planning assumption, to be checked against NASA EVA guidance:
#   < 10°  easy walking · 10–20° careful · > 20° avoid on foot
EASY, HARD = 10.0, 20.0

with tifffile.TiffFile(DEM) as tif:
    page = tif.pages[0]
    z = page.asarray().astype("float64")
    sx, sy, _ = page.tags["ModelPixelScaleTag"].value          # metres per pixel (20, 20)
    _, _, _, x0, y0, _ = page.tags["ModelTiepointTag"].value    # top-left corner, metres
    R = page.tags["GeoDoubleParamsTag"].value[5]                # sphere radius used by the projection

z[(z < -1e30) | ~np.isfinite(z)] = np.nan                       # GDAL nodata = -3.4e38
rows, cols = z.shape

# Equirectangular with latitude of true scale 0: x = R·lon, y = R·lat (radians). Linear in degrees,
# so the image maps straight onto Leaflet's EPSG:4326 grid.
deg = lambda m: math.degrees(m / R)
west, north = deg(x0), deg(y0)
east, south = deg(x0 + cols * sx), deg(y0 - rows * sy)

# Ground spacing. North–south is 20 m; east–west shrinks with cos(latitude) (~19 m here).
lat = np.radians(np.linspace(north, south, rows))[:, None]
dx = sx * np.cos(lat)
dy = sy

dz_dy, dz_dx = np.gradient(z)           # change per pixel (rows, then columns)
slope = np.degrees(np.arctan(np.hypot(dz_dx / dx, dz_dy / dy)))

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
