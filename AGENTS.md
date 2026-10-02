# AGENTS.md — conventions for contributors and AI coding agents

Rising Foliage estimates fall-foliage colour distributions for specific places from
free satellite + ground data, and turns them into trip-planning answers.
Read `README.md` first; `docs/PRD.md` is the product contract.

## Commands

```sh
uv run prototype/app.py                  # run the Streamlit app (self-bootstraps)
uv run prototype/smoke_test.py           # REQUIRED before claiming any change works
uv run prototype/fetch.py --place kelso --years 2022-2026   # fetch a place
uv run prototype/refresh.py              # daily incremental refresh (CI runs this)
```

Everything runs via `uv` with PEP 723 inline dependencies — there is no
requirements install step for development (`requirements.txt` exists only for
Streamlit Community Cloud). Python ≥3.11. Plain `python3` may be 3.8 on dev
machines — always use `uv run`.

## Layout

- `prototype/foliage.py` — shared library: STAC fetch, colour classification,
  persistence, analytics (`best_window`, `expected_coverage`,
  `forecast_ensemble`). No Streamlit imports here, ever.
- `prototype/ground.py` — ground evidence: PhenoCam, Ontario Parks scrape,
  iNaturalist, Nominatim geocoding. All fetchers cache under
  `prototype/output/ground/` and must fail soft (app works offline).
- `prototype/app.py` — the Streamlit app. UI only; analytics belong in
  `foliage.py`.
- `prototype/output/places/<key>/` — per-place data. Only `meta.json` and
  `classified.npz` are committed (see Data rules); PNGs/GIFs are regenerable.

## Verification

- After any change to `app.py`, run the smoke test. It uses Streamlit's
  `AppTest` and fails on any uncaught exception, missing hero, or broken
  interaction. Add a check when you add a feature.
- Code-only `app.py` edits hot-reload (press R in the browser). Adding a NEW
  module file requires a real server restart — kill by port, not by name
  (the process is `python app.py`, not `streamlit`):
  `kill $(lsof -t -iTCP:8501 -sTCP:LISTEN)`.

## Product rules (from the PRD — do not regress these)

1. **Observed vs inferred must stay distinguishable.** Observations carry
   their date, age, and cloud fraction. Forecasts/assumptions are labelled
   inferred, drawn faded, or captioned as estimates. Never present an
   interpolation as a measurement.
2. **No black-box numbers.** Uncertainty = the spread across past seasons,
   shown, not scored. If a value rests on <3 seasons, say so.
3. **End-user language.** No stats jargon in the UI ("≥60% coverage reached"
   → "colour arriving around Oct 17"). Technical detail goes in captions.
4. **The six colour classes and palette in `foliage.CLASSES`/`PALETTE` are
   canonical** — use them everywhere (maps, charts, legends, selectors).

## Data rules

- Never commit: raw imagery, RGB quicklooks, GIFs, PhenoCam/iNat caches,
  credentials. The `.gitignore` negations are deliberate — don't "fix" them.
- `onparks_history.csv` is committed as attributed non-commercial
  reproduction (Crown copyright) — keep the attribution note in
  `docs/data-licences.md` in sync with any change.
- New data sources require a licence/robots review and an entry in
  `docs/data-licences.md` BEFORE integration. Red lines live there.
- Attribution strings in the UI (Copernicus, PhenoCam CC-BY, King's Printer,
  OSM) are licence obligations, not decoration.

## Known pitfalls (hard-won — believe them)

- **Sentinel-2 DN offset**: `sentinel-2-c1-l2a` assets are raw DN with a
  +1000 offset; the legacy `sentinel-2-l2a` collection has it already
  applied. Subtracting twice reads green forest as yellow. See
  `fetch_year()`'s `dn_offset`.
- **MODIS is dead** (Terra 2025, Aqua 2026) and Suomi-NPP ended Nov 2026.
  Daily coarse layer = NOAA-20/21 VIIRS only.
- **Leaflet in hidden Streamlit tabs** gets a zero-size container:
  `fit_bounds` computes max-zoom garbage. Use fixed `zoom_start`, or render
  static images (`st.image` of an RGBA array) for maps in non-default tabs.
- **st_folium** takes `use_container_width`, not `width="stretch"`.
- **exFAT + git**: delete AppleDouble files before every git op on the
  external drive: `find .git -name '._*' -delete`.
- **Cloud gaps are structural**, not incidental: 2025's entire peak window
  had zero usable scenes. Features must degrade gracefully when a year has
  2–3 observations.

## Current priority

SC-03 validation (PRD §27): the 2026 season is being recorded daily
(satellite + parks reports + camera). The next substantial task is a
notebook quantifying agreement between our distributions and ground truth,
then calibrating the classifier thresholds against it. Do not add new
user-facing precision before that lands.
