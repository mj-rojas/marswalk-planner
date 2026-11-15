# Marswalk Planner · Jezero Crater

NASA Space Apps Challenge 2026 · Challenge: **Interplanetary Survival Guide: Martian Map**

A web map that helps the first human explorers plan safe walks in Jezero Crater, Mars,
using real NASA orbital imagery, terrain data and Perseverance's actual route.

- **Live map:** https://mj-rojas.github.io/marswalk-planner/
- **Demo slides (7):** https://mj-rojas.github.io/marswalk-planner/slides/marswalk-planner-demo.pdf

## What it does (so far)

**EVA 01, "Follow the leopard spots".** The planner sends a crew on foot to Cheyava Falls, the rock
where Perseverance found a potential biosignature in July 2024 (not confirmed). Humans can do what
the rover could not: map how far the spots extend, choose the best samples and carry them back.

- **Crew base**: picked by the planner. It is the flat site (every slope within 200 m under 5°) with
  the easiest walk to the science goal.
- **Walking route**: least-cost path over the slope grid. Steeper ground costs more and slopes over
  20° are forbidden. Result: 1.65 km one way, 97% of it under 10°. The straight line (1.42 km) would
  cross 350 m of slopes over 10° and the valley wall.
- **Route numbers**: walking time, emergency walkback time, climb and descent, time left at the rock
  in a 6-hour EVA, and an elevation profile you can move along.
- **Four points of interest**, each with a job: shelter, orientation, safety and science.
- **Radiation**: the dose for the 6-hour EVA (about 0.17 mSv, roughly 8 chest X-rays), from the surface
  dose rate measured by Curiosity's RAD instrument, and the time to reach shelter if a solar storm hits.
- **Walkability layer**: terrain slope from a 20 m/px elevation model. Green < 10° (easy),
  yellow 10–20° (careful), red > 20° (over the suit limit).
- Mars basemaps and high-resolution imagery of Jezero (HiRISE 25 cm/px, CTX 6 m/px), and
  Perseverance's real traverse as a reference.

### Planning numbers and where they come from

| Number | Value | Source |
|---|---|---|
| Slope limit on foot | 20° | NASA xEVA System Requirements Document: a suited astronaut must walk up, down and across a 20° slope. Cited in Scoville (2021), https://ntrs.nasa.gov/citations/20210026296 |
| Nominal EVA length | 6 h (± 2) | Artemis III Science Definition Team report, cited in Scoville (2021) |
| Flat ground for the base | slope < 5° | Landing circle used in Scoville (2021). The 200 m radius is our own margin (the study used 100 m) |
| Walking speed | 2.7 km/h (1.7 mph) | Apollo planning speed for walks over 1 hour. Ogilvie et al. (2026), ICES-2026-127, https://ntrs.nasa.gov/citations/20260005410 |
| Emergency walkback speed | 3.5 km/h (2.2 mph) | Apollo planning speed for walkbacks under 1 hour, same source. Design cases: 30 min or 1 h |
| Slow pace | 1.6 km/h (1 mph) | Real pace on Apollo 15 (0.7–1.4 mph), same source |
| Surface radiation | 0.67 mSv/day | Average measured by Curiosity's RAD in Gale crater, Aug 2012 – June 2013, with no major solar storm. NASA news release 13-366 (9 Dec 2013); Hassler et al. (2014), *Science* 343, 1244797 |
| Chest X-ray | 0.02 mSv | Same NASA release |
| Career radiation limit | 600 mSv | NASA-STD-3001 Vol. 1 Rev B [V1 4030], in Technical Brief OCHMO-TB-020 Rev E |
| "Careful" class | 10° | Our own margin: half of the suit limit. Not a NASA number |

Radiation dose = 0.67 mSv/day × 6 h / 24 h = 0.17 mSv, which is 0.17 / 0.02 ≈ 8 chest X-rays and
0.03% of the career limit. The rate was measured in Gale crater, not in Jezero, and changes with the
solar cycle.

Limits: times use flat-ground speeds and do not slow down on slopes. A 20 m grid smooths out
boulders and small scarps, so real local slopes can be steeper than shown. The route cost
(distance × (1 + (slope / 10°)²)) is our own choice.

## Run locally

```
python -m http.server 8090
```

Then open http://localhost:8090.

To rebuild the slope layer and the route, download the DEM (URL below) to `data/jezero_ctx_dem_20m.tif`, then run:

```
python -m venv .venv
.venv/Scripts/python -m pip install numpy tifffile pillow
.venv/Scripts/python scripts/make_slope.py
.venv/Scripts/python scripts/make_route.py
```

`make_slope.py` writes the slope overlay (`data/slope.png`). `make_route.py` picks the base, computes
the route and writes `data/route.json`, which the map reads.

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
| Cheyava Falls science | Hurowitz et al. (2025), *Nature* 645, 332–340 | https://doi.org/10.1038/s41586-025-09413-0 |
| Cheyava Falls, rock size and minerals | NASA/JPL news release, 10 Sept 2025 | https://www.jpl.nasa.gov/news/nasa-says-mars-rover-discovered-potential-biosignature-last-year/ |
| Slope limit, EVA length, landing circle | Scoville (2021), NASA NTRS 20210026296 | https://ntrs.nasa.gov/citations/20210026296 |
| Walking and walkback speeds | Ogilvie et al. (2026), NASA NTRS 20260005410 | https://ntrs.nasa.gov/citations/20260005410 |
| Surface radiation (Curiosity RAD) | NASA news release 13-366, 9 Dec 2013 | https://www.nasa.gov/press/2013/december/nasa-rover-results-include-first-age-measurement-on-mars-and-help-for-human/ |
| Surface radiation, paper | Hassler et al. (2014), *Science* 343, 1244797 | https://doi.org/10.1126/science.1244797 |
| Career radiation limit | NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev E | https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf |

Map library: [Leaflet](https://leafletjs.com/) 1.9.4 (BSD-2-Clause).

## AI disclosure

The code, the texts (this README, the map panel) and the demo slides were written with AI assistance
(Claude, Anthropic), which also helped find and read the NASA sources. No AI runs inside the map and
no image is AI-generated: the slides use screenshots of the live map.

## License

Apache License 2.0. See [LICENSE](LICENSE).
