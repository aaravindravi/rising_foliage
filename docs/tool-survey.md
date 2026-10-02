# Free & Open-Source Tool Survey

**Status:** verified 2026-09-29 (web-checked, not from memory)
**Scope:** data sources and tools for Phase 1 (Data Feasibility) through Phase 5 (User Prototype), Kelso Summit / Southern Ontario.

This survey informs — but does not yet fix — technology choices, per PRD §25.

---

## Recommended evidence stack (summary)

| Role | Source | Resolution / cadence | Cost | Python path |
|---|---|---|---|---|
| Accuracy layer | Sentinel-2 L2A (Earth Search STAC) | 10 m / ~5 days | Free, **no auth** | pystac-client → odc-stac |
| Accuracy layer #2 | NASA HLS (S30+L30) | 30 m / ~2–3 days combined | Free Earthdata login | earthaccess |
| Daily coarse layer | NOAA-20/21 VIIRS (VJ109GA/VJ209GA) | 500 m / daily (~3 h via LANCE NRT) | Free Earthdata login | earthaccess |
| Weather (forecast + historical) | Open-Meteo; ECCC GeoMet | hourly | Free (Open-Meteo non-commercial) | openmeteo-requests; OGC API |
| Ground reference | PhenoCam network | sub-daily imagery + GCC CSVs | Free, CC-BY 4.0 | plain requests |
| Ground reference #2 | Ontario Parks fall colour report | ~weekly per park | Free to scrape; Crown copyright | httpx + parser |
| Ground reference #3 | iNaturalist geotagged photos | ad hoc | Free, licence-filterable | pyinaturalist |
| Isochrones | openrouteservice (hosted) or Valhalla (self-host) | — | Free tier / free | routingpy |
| Photo classification (optional) | Qwen3.5-9B or -4B (Apache-2.0) | local | Free | Ollama / vLLM |

---

## 1. Sentinel-2 (primary imagery — 10 m, the only source that can resolve Kelso's forest patches)

- **Element84 Earth Search** (`https://earth-search.aws.element84.com/v1`): free, anonymous, COGs on public S3 (`s3://sentinel-cogs/`, us-west-2, `--no-sign-request`). Use collection `sentinel-2-c1-l2a` (note archive gaps 2016–2019 — Element84/earth-search#45; `sentinel-2-l2a` as fallback). Scenes appear within hours of Copernicus publication.
- **Copernicus Data Space Ecosystem** as backup: new STAC endpoint `https://stac.dataspace.copernicus.eu/v1/` (the legacy `catalogue.dataspace.copernicus.eu/stac` was deprecated Nov 2025). Anonymous search, free-account downloads; generous quotas (12 TB / 30 days).
- Licence: Copernicus Sentinel Data Legal Notice — free, open, commercial OK, attribution "Copernicus Sentinel data [year]".
- Revisit over Southern Ontario ~5 days (2 satellites), before cloud losses. **Cloud gaps are the key feasibility risk** — hence the daily VIIRS layer and ground evidence below.

## 2. NASA HLS (Harmonized Landsat + Sentinel-2 — 30 m)

- Sentinel-2 and Landsat 8/9 harmonized to one 30 m analysis-ready product; combined revisit ~2–3 days.
- Free Earthdata login; latency ~1.7 days nominal, 2–3 days in practice → the **accuracy/history layer, not the daily-refresh layer**.
- Access: `earthaccess` (`search_data(short_name="HLSS30")`) or CMR-STAC at `https://cmr.earthdata.nasa.gov/stac/LPCLOUD`.

## 3. Daily coarse monitoring — VIIRS (MODIS is dead)

- **Do not build on MODIS**: Terra MODIS products ended Dec 2025, Aqua Aug 2026. **Avoid Suomi NPP (VNP\*)** too — delivery ceases 2026-11-01.
- Use **NOAA-20/21 VIIRS** daily surface reflectance `VJ109GA` / `VJ209GA` (500 m); compute daily NDVI/greenness yourself (the VI products are 16-day composites).
- Standard latency 1–3 days; **LANCE NRT within ~3 h**, free with Earthdata login.
- 500 m won't resolve Kelso itself — role is regional trend/change detection between Sentinel-2 passes.

## 4. Weather / environmental predictors

- **Open-Meteo**: free, no key, **non-commercial only** (paid plan for commercial). Forecast API includes Canadian GEM/HRDPS blends; historical ERA5 back to 1940 (`archive-api.open-meteo.com`). Data CC-BY 4.0. Python: `openmeteo-requests`.
- **ECCC GeoMet / api.weather.gc.ca**: free, anonymous, operational. `climate-daily`, `climate-hourly`, `climate-normals`, `swob-realtime` station obs (GDD/frost accumulation for Milton area); HRDPS gridded forecasts via WMS/WCS or Datamart GRIB2. ECCC end-use licence permits reuse incl. commercial with attribution.
- Fit: GeoMet for Canadian station ground truth and an open-licence path; Open-Meteo for convenience while non-commercial.

## 5. PhenoCam + webcams (continuous ground truth)

- **PhenoCam network** (phenocam.nau.edu): 1,000+ cameras, fully open (CC-BY 4.0). JSON API, deterministic archive image URLs, and precomputed 1-/3-day **GCC (green chromatic coordinate)** + NDVI CSVs per site — essentially the project's foliage-transition signal, pre-solved, for camera sites.
- Southern Ontario sites (verified via API): **`turkeypointurban` (Hamilton, ~30 km from Milton — closest)**, `koffler` (King City), `elora1`/`elora3`, `queens`, plus the Turkey Point cluster on Lake Erie.
- No official Python client (phenocamr is R) — plain `requests` suffices, no auth.
- **Kelso/Glen Eden webcams: not usable** — ski-season cams only, currently offline; Conservation Halton webcam page 404s. Nearest Ontario Parks cam is Algonquin (~250 km).

## 6. Ontario Parks fall colour report (validation labels)

- Live and updating at `ontarioparks.ca/fallcolour` — 70 parks, ~weekly, fields: date, dominant colour, % colour change, % leaf fall, free text. (E.g., Bronte Creek 2026-09-29: Yellow, 40% change, 20% leaf fall.)
- Scrape-only (server-rendered HTML, single page, trivially parseable). **Crown copyright**: non-commercial reproduction OK with "© King's Printer for Ontario" attribution; commercial reuse needs a licence. Treat as validation evidence, not a redistributed dataset.
- Closest reporting parks to Milton: **Bronte Creek (~15 km)**, Forks of the Credit (~35 km), Mono Cliffs (~60 km). Kelso itself (Conservation Halton) is *not* covered — expect to bridge via nearby parks + PhenoCam.

## 7. Geotagged photos

- **iNaturalist**: free read-only API (v2 now official, v1 supported ≥1 yr), ~1 req/s, licence-filterable (`photo_license=cc0,cc-by,...`). Python: `pyinaturalist`. Bulk data via the AWS Open Data bucket / GBIF, not API scraping. **Flag:** ToU prohibit commercial ML training on iNaturalist data; non-commercial open-source use is fine.
- **Flickr: skip.** New API keys now require a paid Flickr Pro subscription; proprietary ToS prohibit long-term photo caching and restrict commercial use.
- Google reviews/photos (PRD §11.3): no free, ToS-compliant, reproducible access path — treat as manual spot-check evidence only.

## 8. Drive-time isochrones (Discovery Mode, Phase 6)

- **openrouteservice** hosted: free with registration; per-request caps (120 km / 1 h driving — exactly matches the PRD's use case); GPL-3.0, self-hostable.
- **Valhalla**: MIT, native `/isochrone`, zero-registration FOSSGIS public instance (fair use), or docker self-host with Geofabrik `ontario-latest.osm.pbf` (~1 GB, ~8 GB RAM to build tiles).
- **OSRM: no isochrone endpoint** — skip.
- `routingpy` wraps all of these behind one Python interface.

## 9. Open-weights VLM for photo foliage classification (optional, later phases)

- **Recommended: Qwen3.5-9B** (Apache-2.0, natively multimodal, ~6.6 GB Q4 via Ollama `qwen3.5`); **Qwen3.5-4B** if throughput matters — negligible loss for coarse colour staging. Fallback: Qwen3-VL-8B (Apache-2.0). vLLM supports both.
- **Avoid for a clean open-source project:** Llama 3.2/4 Vision (community licence, not open source), Moondream 3 (BSL 1.1), Gemma 3 / PaliGemma 2 (Gemma Terms with use restrictions). InternVL3.5 (Apache-2.0) is a legitimate alternative.
- Note: an LLM is **not required** for the core pipeline — spectral indices + classical colour analysis come first (PRD §26 explicitly defers ML). The VLM is for classifying crowdsourced/iNaturalist photos in Phases 3+.

## 10. Python geospatial stack (all Apache/BSD/MIT, all maintained)

- `pystac-client` 0.9.x → **`odc-stac`** 0.5.x (has won over stagnant `stackstac`) → `xarray` (+ dask) → `rioxarray` 0.23 clip with a `geopandas` 1.2 AOI polygon.
- Pipeline for Kelso: STAC search (Earth Search) → `odc.stac.load()` → cloud-mask (SCL band) → NDVI / red-edge / RGB chromatic coordinates → clip to Kelso AOI → colour-distribution estimate.
- `stac-geoparquet`/`rustac` exist for bulk STAC work — overkill for a single-AOI prototype.

## 11. Lightweight visualization (foliage map with colours)

All open source, all Python-friendly, in order of when the project will need them:

- **Phases 1–4 (notebooks/validation):** `matplotlib` for foliage-progression time series and validation plots; **`leafmap`** (MIT) for interactive notebook maps — displays local GeoTIFFs/COGs directly via `localtileserver`, so classified foliage rasters render on a basemap with zero infrastructure.
- **Static/shareable maps:** **`folium`** (MIT, Leaflet wrapper) — outputs a self-contained HTML file; ideal for "here's the Kelso foliage map for Oct 5" artifacts, GeoJSON choropleths of per-destination colour distributions, and embedding in docs.
- **Phase 5 prototype UI:** **Streamlit** (Apache-2.0) + `streamlit-folium` — location/date/colour-range/coverage widgets plus the map in ~100 lines, pure Python. (Gradio is the alternative; Streamlit's layout suits a map-centric app better.)
- **Foliage colour ramp:** define one fixed project palette for the six PRD classes — e.g. green `#2d7d2d`, yellow-green `#9acd32`, yellow `#ffd700`, orange `#ff8c00`, red `#cc2200`, brown/bare `#8b6f47` — and use it consistently across rasters, charts, legends, and the eventual colour-range selector, so the map *is* the legend.
- **Later, if needed:** MapLibre GL JS (BSD) for a production web front end; `lonboard`/pydeck for large vector datasets. Not needed for the prototype.

---

## Cross-cutting licence/cost flags

- **Not free or not open:** Flickr API (Pro-gated, proprietary), Open-Meteo commercial use, Ontario Parks report commercial reuse (Crown copyright), Llama/Moondream/Gemma model licences, iNaturalist commercial-ML training.
- Everything in the recommended stack is reproducible by a third party with at most one free account (NASA Earthdata) — satisfying PRD §28 (Cost, Reproducibility).
- To re-verify manually (official pages blocked automated checks): exact current openrouteservice free-tier isochrone quota; exact Flickr Pro API-key wording.

## Architecture implication (for the feasibility spec)

Daily layer = NOAA-20/21 VIIRS; accuracy layer = Sentinel-2 (Earth Search, anonymous) + HLS (earthaccess); ground reference = PhenoCam `turkeypointurban` + Ontario Parks Bronte Creek + iNaturalist; forecast inputs = ECCC GeoMet / Open-Meteo. Cloud-gap handling and the Sentinel-2 "can it distinguish yellow vs orange vs red" question (PRD §29) are the two things Phase 1 must answer first.
