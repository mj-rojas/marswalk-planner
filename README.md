# Marswalk Planner · Jezero Crater

NASA Space Apps Challenge 2026 · Challenge: **Interplanetary Survival Guide: Martian Map**

A web map that helps the first human explorers plan safe walks in Jezero Crater, Mars,
using real NASA orbital imagery, terrain data and Perseverance's actual route.

## What it does (so far)

- Mars basemaps and high-resolution imagery of Jezero (HiRISE 25 cm/px, CTX 6 m/px).
- **Walkability layer**: terrain slope computed from a 20 m/px elevation model.
  Green < 10° (easy), yellow 10–20° (careful), red > 20° (avoid on foot).
  The thresholds are a planning assumption. A 20 m grid smooths out boulders and small
  scarps, so real local slopes can be steeper than shown.
- Perseverance rover's real traverse as a reference route.

## Run locally

```
python -m http.server 8090
```

Then open http://localhost:8090.

To rebuild the slope layer, download the DEM (URL below) to `data/jezero_ctx_dem_20m.tif`, then run:

```
python -m venv .venv
.venv/Scripts/python -m pip install numpy tifffile pillow
.venv/Scripts/python scripts/make_slope.py
```

## Data sources

| Data | Provider | Link |
|---|---|---|
| HiRISE Jezero orthomosaic 25 cm | NASA/JPL/University of Arizona/USGS, via NASA Mars Trek | https://trek.nasa.gov/mars/ |
| CTX Jezero orthomosaic 6 m | NASA/JPL/MSSS/USGS, via NASA Mars Trek | https://trek.nasa.gov/mars/ |
| Viking MDIM 2.1 color mosaic | NASA/JPL/USGS, via NASA Mars Trek | https://trek.nasa.gov/mars/ |
| MGS MOLA shaded relief | NASA/JPL/GSFC, via NASA Mars Trek | https://trek.nasa.gov/mars/ |
| THEMIS day IR mosaic 100 m | NASA/JPL/Arizona State University, via NASA Mars Trek | https://trek.nasa.gov/mars/ |
| Jezero CTX DTM 20 m (Mars 2020 TRN) | USGS Astrogeology / NASA | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif |
| Perseverance traverse and waypoints | NASA/JPL-Caltech (MMGIS) | https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_traverse.json |

Map library: [Leaflet](https://leafletjs.com/) 1.9.4 (BSD-2-Clause).

## AI disclosure

Built with help from Claude (Anthropic) as a coding assistant.

## License

Apache License 2.0. See [LICENSE](LICENSE).
