"""
Picks a crew base site and computes the safest walking route to the science goal.

Science goal: Cheyava Falls (Bright Angel formation, Neretva Vallis), the rock where Perseverance
found a potential biosignature ("leopard spots") and cored the sample "Sapphire Canyon".

Input : data/jezero_ctx_dem_20m.tif  (same DEM as make_slope.py)
Output: data/route.json  base, route (lat, lon, distance, elevation, slope), stats and points of interest

Run:  .venv/Scripts/python scripts/make_route.py

How it works
1. Base site  = a cell whose whole surroundings (200 m radius) are flatter than 5°.
2. Route      = least-cost path over the slope grid (Dijkstra). Steeper cells cost more and cells
                steeper than the suit limit (20°) are forbidden.
3. Of all possible base sites, we keep the one with the cheapest route to the goal.
"""
import heapq
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))   # so "terrain" is found from any folder
from terrain import Terrain

ROOT = Path(__file__).resolve().parent.parent

# ---- Planning numbers, each with its source -------------------------------------------------------
# Rover position while it worked on Cheyava Falls (sols 1210–1218, M20_waypoints.json).
# The core "Sapphire Canyon" was sealed on sol 1215 (21 July 2024).
GOAL = {"lat": 18.49748, "lon": 77.30519}

SUIT_LIMIT_DEG = 20.0     # suited astronaut must walk up, down and across 20° (NASA xEVA SRD, via Scoville 2021)
CAREFUL_DEG = 10.0        # our own margin: half of the suit limit
BASE_MAX_SLOPE_DEG = 5.0  # Artemis III landing-site study used circles with slope < 5° (Scoville 2021)
BASE_RADIUS_M = 200.0     # our assumption: twice the 100 m landing circle of that study
SEARCH_KM = 3.5           # 1-hour walkback radius at 2.2 mph (Ogilvie et al. 2026)

MPH = 1.609344            # km/h in one mile per hour
SPEED_PLAN_KMH = 1.7 * MPH      # Apollo planning speed for walks longer than 1 hour
SPEED_WALKBACK_KMH = 2.2 * MPH  # Apollo planning speed for an emergency walkback shorter than 1 hour
SPEED_SLOW_KMH = 1.0 * MPH      # real pace on Apollo 15 (0.7–1.4 mph)
EVA_HOURS = 6.0           # nominal Artemis EVA: 6 hours ± 2 (Artemis III Science Definition Team, via Scoville 2021)

# Radiation. Curiosity's RAD instrument measured an average of 0.67 mSv per day on the surface (Gale crater,
# Aug 2012 – June 2013, no major solar storm in that period). NASA news release 13-366, 9 Dec 2013.
RAD_MSV_PER_DAY = 0.67
CHEST_XRAY_MSV = 0.02     # "a typical chest X-ray is about 0.02 millisievert" (same NASA release)
CAREER_LIMIT_MSV = 600    # career limit for space flight radiation, NASA-STD-3001 Vol. 1 Rev B [V1 4030]

SOURCES = [
    {"what": "20° slope limit, 6 h EVA, flat landing circle",
     "cite": "Scoville (2021), Artemis III EVA Mission Capability for de Gerlache-Shackleton Ridge, "
             "citing the NASA xEVA System Requirements Document",
     "url": "https://ntrs.nasa.gov/citations/20210026296"},
    {"what": "Walking speeds and walkback",
     "cite": "Ogilvie et al. (2026), Mars Spacesuit Mass Requirements, ICES-2026-127",
     "url": "https://ntrs.nasa.gov/citations/20260005410"},
    {"what": "Cheyava Falls science",
     "cite": "Hurowitz et al. (2025), Nature 645, 332–340",
     "url": "https://doi.org/10.1038/s41586-025-09413-0"},
    {"what": "Cheyava Falls, NASA release",
     "cite": "NASA/JPL, 10 Sept 2025",
     "url": "https://www.jpl.nasa.gov/news/nasa-says-mars-rover-discovered-potential-biosignature-last-year/"},
    {"what": "Rover position at the rock",
     "cite": "NASA/JPL-Caltech, M20 waypoints",
     "url": "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json"},
    {"what": "Surface radiation (Curiosity RAD) and chest X-ray dose",
     "cite": "NASA news release 13-366, 9 Dec 2013; Hassler et al. (2014), Science 343, 1244797",
     "url": "https://www.nasa.gov/press/2013/december/"
            "nasa-rover-results-include-first-age-measurement-on-mars-and-help-for-human/"},
    {"what": "Career radiation limit, 600 mSv",
     "cite": "NASA-STD-3001 Technical Brief OCHMO-TB-020 Rev E, Design for Ionizing Radiation Protection",
     "url": "https://www.nasa.gov/wp-content/uploads/2023/03/radiation-protection-technical-brief-ochmo.pdf"},
    {"what": "Terrain",
     "cite": "Jezero CTX DTM 20 m, USGS Astrogeology / Mars 2020 TRN",
     "url": "https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/"
            "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"},
]

t = Terrain()
z, slope = t.z, t.slope

# ---- Work on a square window around the goal -----------------------------------------------------
goal_r, goal_c = t.cell(GOAL["lat"], GOAL["lon"])
half = int(SEARCH_KM * 1000 / t.sy)
r0, c0 = goal_r - half, goal_c - half
n = 2 * half + 1
win = slope[r0:r0 + n, c0:c0 + n]
walkable = np.isfinite(win) & (win < SUIT_LIMIT_DEG)

# ---- 1. Base candidates: every cell within BASE_RADIUS_M is flatter than BASE_MAX_SLOPE_DEG -------
too_steep = ~(win < BASE_MAX_SLOPE_DEG)            # also true where there is no data
near_steep = np.zeros_like(too_steep)
rad = int(BASE_RADIUS_M / t.sy)
for dr in range(-rad, rad + 1):
    for dc in range(-rad, rad + 1):
        if dr * dr + dc * dc <= rad * rad:
            a0, a1 = max(0, dr), min(n, n + dr)
            b0, b1 = max(0, dc), min(n, n + dc)
            near_steep[a0:a1, b0:b1] |= too_steep[a0 - dr:a1 - dr, b0 - dc:b1 - dc]
base_ok = ~near_steep
base_ok[:rad, :] = base_ok[-rad:, :] = base_ok[:, :rad] = base_ok[:, -rad:] = False   # circle must fit

# ---- 2. Dijkstra from the goal to every cell ------------------------------------------------------
# Cost of a step = ground distance × (1 + (slope / 10°)²). So 10° costs double and 20° costs 5×.
penalty = 1.0 + (win / CAREFUL_DEG) ** 2
dx_row = t.dx[r0:r0 + n, 0]                         # east–west metres per cell, for each row
steps = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

INF = float("inf")
cost = np.full((n, n), INF)
prev = {}
start = (half, half)
cost[start] = 0.0
queue = [(0.0, start)]
while queue:
    c, (r, col) = heapq.heappop(queue)
    if c > cost[r, col]:
        continue
    for dr, dc in steps:
        rr, cc = r + dr, col + dc
        if not (0 <= rr < n and 0 <= cc < n) or not walkable[rr, cc]:
            continue
        dist = math.hypot(dr * t.dy, dc * dx_row[r])
        new = c + dist * (penalty[r, col] + penalty[rr, cc]) / 2
        if new < cost[rr, cc]:
            cost[rr, cc] = new
            prev[(rr, cc)] = (r, col)
            heapq.heappush(queue, (new, (rr, cc)))

# ---- 3. Best base = candidate with the cheapest route ---------------------------------------------
candidates = np.where(base_ok, cost, INF)
base = np.unravel_index(np.argmin(candidates), candidates.shape)
if not np.isfinite(candidates[base]):
    raise SystemExit("No base site can reach the goal without crossing slopes above the suit limit.")

cells = [tuple(int(v) for v in base)]
while cells[-1] != start:
    cells.append(prev[cells[-1]])                   # base → goal

# Smooth the staircase of the grid path (moving average over 5 points ≈ 100 m). Ends stay fixed.
pts = np.array(cells, dtype=float)
smooth = pts.copy()
for i in range(1, len(pts) - 1):
    a, b = max(0, i - 2), min(len(pts), i + 3)
    smooth[i] = pts[a:b].mean(axis=0)

# ---- Profile along the route ----------------------------------------------------------------------
route = []
dist = 0.0
for i, (r, c) in enumerate(smooth):
    if i:
        pr, pc = smooth[i - 1]
        dist += math.hypot((r - pr) * t.dy, (c - pc) * dx_row[int(r)])
    lat, lon = t.latlon(r0 + r, c0 + c)
    route.append({
        "lat": round(lat, 6), "lon": round(lon, 6), "dist_m": round(dist, 1),
        "elev_m": round(t.sample(z, r0 + r, c0 + c), 1),
        "slope_deg": round(t.sample(slope, r0 + r, c0 + c), 1),
    })

length = route[-1]["dist_m"]
elev = [p["elev_m"] for p in route]
climbs = [b - a for a, b in zip(elev, elev[1:])]
seg = [(b["dist_m"] - a["dist_m"], max(a["slope_deg"], b["slope_deg"])) for a, b in zip(route, route[1:])]
share = lambda lo, hi: round(100 * sum(d for d, s in seg if lo <= s < hi) / length, 1)
steepest = max(route, key=lambda p: p["slope_deg"])
hours = lambda km, kmh: km / kmh
one_way_h = hours(length / 1000, SPEED_PLAN_KMH)

stats = {
    "length_m": round(length),
    "straight_line_m": round(math.hypot((base[0] - half) * t.dy, (base[1] - half) * dx_row[half])),
    "ascent_m": round(sum(c for c in climbs if c > 0)),
    "descent_m": round(-sum(c for c in climbs if c < 0)),
    "elev_start_m": elev[0], "elev_end_m": elev[-1],
    "max_slope_deg": steepest["slope_deg"],
    "pct_easy": share(0, CAREFUL_DEG), "pct_careful": share(CAREFUL_DEG, SUIT_LIMIT_DEG),
    "pct_over_limit": share(SUIT_LIMIT_DEG, 90),
    "one_way_min": round(60 * one_way_h),
    "one_way_min_slow": round(60 * hours(length / 1000, SPEED_SLOW_KMH)),
    "walkback_min": round(60 * hours(length / 1000, SPEED_WALKBACK_KMH)),
    "round_trip_h": round(2 * one_way_h, 1),
    "time_on_site_h": round(EVA_HOURS - 2 * one_way_h, 1),
}

# ---- Radiation dose for one EVA: dose rate × hours outside ------------------------------------------
eva_dose = RAD_MSV_PER_DAY * EVA_HOURS / 24
safety = {
    "rate_msv_per_day": RAD_MSV_PER_DAY,
    "eva_dose_msv": round(eva_dose, 2),
    "chest_xrays": round(eva_dose / CHEST_XRAY_MSV),
    "career_limit_msv": CAREER_LIMIT_MSV,
    "pct_career_limit": round(100 * eva_dose / CAREER_LIMIT_MSV, 2),
    "note": "Dose rate measured by Curiosity's RAD in Gale crater (Aug 2012 – June 2013), not in Jezero, "
            "in a period with no major solar storm. It changes with the solar cycle. In a solar storm "
            "the crew must get back to shelter.",
}

# ---- Why not walk in a straight line? Sample the direct line base → goal every 10 m ---------------
(br, bc), (gr, gc) = smooth[0], smooth[-1]
k = int(stats["straight_line_m"] / 10)
line = [(br + (gr - br) * i / k, bc + (gc - bc) * i / k) for i in range(k + 1)]
line_slopes = [t.sample(slope, r0 + r, c0 + c) for r, c in line]
wall_i = int(np.argmax(line_slopes))
wall_lat, wall_lon = t.latlon(r0 + line[wall_i][0], c0 + line[wall_i][1])
stats["straight_line_max_slope_deg"] = round(line_slopes[wall_i], 1)
stats["straight_line_over_limit_m"] = 10 * sum(s >= SUIT_LIMIT_DEG for s in line_slopes)
stats["straight_line_careful_m"] = 10 * sum(s >= CAREFUL_DEG for s in line_slopes)
stats["route_careful_m"] = round(sum(d for d, s in seg if s >= CAREFUL_DEG))
stats["detour_m"] = stats["length_m"] - stats["straight_line_m"]

# ---- Points of interest: few, each with a job ----------------------------------------------------
# The ramp is the steepest point of the route before the final approach to the rock.
ramp = max((p for p in route if p["dist_m"] < length - 150), key=lambda p: p["slope_deg"])
near = lambda lo, hi: [p["elev_m"] for p in route if lo <= p["dist_m"] - ramp["dist_m"] <= hi]
ramp_drop = round(max(near(-200, 0)) - min(near(0, 200)))

pois = [
    {"id": "base", "role": "Shelter", "name": "Crew base",
     "lat": route[0]["lat"], "lon": route[0]["lon"], "elev_m": elev[0], "dist_m": 0,
     "text": f"Flat ground: every slope within {BASE_RADIUS_M:.0f} m is under {BASE_MAX_SLOPE_DEG:.0f}°. "
             "The planner picked it as the flat site with the easiest walk to the science goal."},
    {"id": "ramp", "role": "Orientation", "name": "Neretva Vallis ramp",
     "lat": ramp["lat"], "lon": ramp["lon"], "elev_m": ramp["elev_m"], "dist_m": ramp["dist_m"],
     "text": f"The route drops about {ramp_drop} m into the ancient river channel through a gap in the "
             f"valley wall ({ramp['slope_deg']}° at its steepest). The channel is about 400 m wide: "
             "follow the foot of its north wall to the west."},
    {"id": "wall", "role": "Safety", "name": "Valley wall: no-go",
     "lat": round(wall_lat, 6), "lon": round(wall_lon, 6),
     "elev_m": round(t.sample(z, r0 + line[wall_i][0], c0 + line[wall_i][1]), 1), "dist_m": None,
     "text": f"The straight line from the base crosses {stats['straight_line_careful_m']} m of slopes over "
             f"{CAREFUL_DEG:.0f}° and peaks at {stats['straight_line_max_slope_deg']}° here, over the "
             f"{SUIT_LIMIT_DEG:.0f}° limit of the suit. A 20 m grid smooths real scarps, so the wall is "
             f"likely steeper. The route goes around: {stats['detour_m']} m longer, but only "
             f"{stats['route_careful_m']} m over {CAREFUL_DEG:.0f}°."},
    {"id": "goal", "role": "Science goal", "name": "Cheyava Falls",
     "lat": GOAL["lat"], "lon": GOAL["lon"], "elev_m": elev[-1], "dist_m": stats["length_m"],
     "text": "A 1 m rock with \"leopard spots\" (the minerals vivianite and greigite): a potential "
             "biosignature found by Perseverance in July 2024. Not confirmed: non-biological origins are "
             "not ruled out. Crew task: map how far the spots extend, choose the best samples and carry "
             f"them back. The last metres climb at up to {stats['max_slope_deg']}°."},
]

out = {
    "goal": {**GOAL, "elev_m": elev[-1], "name": "Cheyava Falls"},
    "base": {"lat": route[0]["lat"], "lon": route[0]["lon"], "elev_m": elev[0],
             "flat_radius_m": BASE_RADIUS_M, "max_slope_deg": BASE_MAX_SLOPE_DEG},
    "pois": pois,
    "stats": stats,
    "safety": safety,
    "assumptions": {
        "suit_limit_deg": SUIT_LIMIT_DEG, "careful_deg": CAREFUL_DEG,
        "speed_plan_kmh": round(SPEED_PLAN_KMH, 2), "speed_walkback_kmh": round(SPEED_WALKBACK_KMH, 2),
        "speed_slow_kmh": round(SPEED_SLOW_KMH, 2), "eva_hours": EVA_HOURS,
        "note": "Times use flat-ground speeds and do not slow down on slopes. "
                "A 20 m grid hides boulders and small scarps.",
    },
    "sources": SOURCES,
    "route": route,
}
(ROOT / "data" / "route.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

print(json.dumps({k: out[k] for k in ("goal", "base", "pois", "stats", "safety")}, indent=2, ensure_ascii=False))
print("base candidates:", int(base_ok.sum()), "cells · route points:", len(route))
