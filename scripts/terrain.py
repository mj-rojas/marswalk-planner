"""
Shared terrain loader: reads the Jezero CTX DEM (20 m/pixel) and computes the slope grid.
Used by make_slope.py (map overlay) and make_route.py (base site + walking route).

Input: data/jezero_ctx_dem_20m.tif  (USGS / Mars 2020 TRN, equirectangular, Mars sphere R = 3,396,190 m)
"""
import logging
import math
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parent.parent
DEM = ROOT / "data" / "jezero_ctx_dem_20m.tif"

logging.getLogger("tifffile").setLevel(logging.ERROR)   # hides a harmless warning about the nodata tag


class Terrain:
    """Elevation z (m), slope (degrees) and the helpers to go between lat/lon and grid cells."""

    def __init__(self):
        with tifffile.TiffFile(DEM) as tif:
            page = tif.pages[0]
            z = page.asarray().astype("float64")
            self.sx, self.sy, _ = page.tags["ModelPixelScaleTag"].value       # metres per pixel (20, 20)
            _, _, _, x0, y0, _ = page.tags["ModelTiepointTag"].value           # top-left corner, metres
            self.R = page.tags["GeoDoubleParamsTag"].value[5]                  # sphere radius of the projection

        z[(z < -1e30) | ~np.isfinite(z)] = np.nan                              # GDAL nodata = -3.4e38
        self.z = z
        self.rows, self.cols = z.shape

        # Equirectangular with latitude of true scale 0: x = R·lon, y = R·lat (radians). Linear in
        # degrees, so the grid maps straight onto Leaflet's EPSG:4326 grid.
        deg = lambda m: math.degrees(m / self.R)
        self.west, self.north = deg(x0), deg(y0)
        self.east, self.south = deg(x0 + self.cols * self.sx), deg(y0 - self.rows * self.sy)
        self.dlon, self.dlat = deg(self.sx), deg(self.sy)                      # degrees per pixel

        # Ground spacing. North–south is 20 m; east–west shrinks with cos(latitude) (~19 m here).
        lat = np.radians(np.linspace(self.north, self.south, self.rows))[:, None]
        self.dx = self.sx * np.cos(lat)                                        # one value per row
        self.dy = self.sy

        dz_dy, dz_dx = np.gradient(z)                                          # change per pixel
        self.slope = np.degrees(np.arctan(np.hypot(dz_dx / self.dx, dz_dy / self.dy)))

    def cell(self, lat, lon):
        """Row and column of the cell that contains a lat/lon point."""
        return int((self.north - lat) / self.dlat), int((lon - self.west) / self.dlon)

    def latlon(self, row, col):
        """Lat/lon of a cell centre. Row and column can be fractional."""
        return self.north - (row + 0.5) * self.dlat, self.west + (col + 0.5) * self.dlon

    def sample(self, grid, row, col):
        """Bilinear interpolation of a grid at a fractional cell position (cell centres)."""
        r0, c0 = int(math.floor(row)), int(math.floor(col))
        fr, fc = row - r0, col - c0
        g = grid[r0:r0 + 2, c0:c0 + 2]
        return float(g[0, 0] * (1 - fr) * (1 - fc) + g[0, 1] * (1 - fr) * fc
                     + g[1, 0] * fr * (1 - fc) + g[1, 1] * fr * fc)
