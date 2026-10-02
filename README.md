# 🍂 Rising Foliage

**Know before you go.** Rising Foliage tells you *where and when* to see the fall
colours you actually want — measured from satellites and ground evidence, not
vibes.

> "I live near Milton and can drive an hour. I want forests that are mostly
> yellow, orange, or red this Saturday. Where should I go — and if nowhere,
> when?"

Every existing foliage report answers with a region-wide "peak" label. Rising
Foliage answers with a **colour distribution for a specific 2.4 km square**
("63% green, 27% yellow-green, 5% orange — observed 2 days ago, 93%
cloud-free"), a personalized best-viewing window, and a ranked list of
destinations for *your* date and *your* colours.

## Try it

Needs only [uv](https://docs.astral.sh/uv/) — no accounts, no API keys. The
repo ships with a data snapshot for 10 Southern Ontario destinations, so the
app works immediately:

```sh
uv run prototype/app.py          # app at http://localhost:8501
```

Optional:

```sh
uv run prototype/fetch.py --place kelso --years 2022-2026   # (re)fetch a place
uv run prototype/refresh.py                                  # pull today's new data
uv run prototype/smoke_test.py                               # run the test suite
```

## What it does

- **🎯 When should I go?** — pick a visit date and a colour range (visual
  slider, green → brown); get the typical best window for that exact spot,
  a verdict for your date ("too early — expect mostly green"), and the
  historically-expected coverage.
- **🏆 Where should I go?** — all analyzed destinations ranked by expected
  coverage of your colours on your date, with "past peak — skip" warnings.
- **📷 Observations** — per-date colour distributions from Sentinel-2
  (10 m), a classified foliage map, what the area looked like around your
  date in past years, and a season time-lapse of true-colour imagery.
- **🔮 Forecast** — plain-language milestones ("colour arriving ~Oct 17")
  computed by replaying how past seasons unfolded from the latest
  observation. The year-to-year spread is shown as the uncertainty.
- **🌿 Ground evidence** — the nearest PhenoCam forest camera's daily
  greenness/redness, Ontario Parks observer reports ranked by distance, and
  this park's own satellite curve overlaid for comparison.
- **➕ Analyze anywhere** — postal code, place name, coordinates, or click
  any map. New areas fetch in ~4–6 minutes and are cached forever.

## Principles

1. **Observed ≠ inferred.** Every number says which it is, how old the
   evidence is, and how cloudy the scene was.
2. **No black-box numbers.** The spread across past seasons *is* the
   confidence interval; assumptions are drawn faded; captions say what the
   data can't.
3. **Free and reproducible.** Core pipeline uses only free, open data
   (Copernicus Sentinel-2, PhenoCam CC-BY, ECCC) — anyone can rebuild every
   number from source.

## How it works

Sentinel-2 scenes (via the anonymous [Earth Search](https://element84.com/earth-search/)
STAC API) are cloud-masked (SCL), converted to surface reflectance, and each
canopy pixel — a mask built from peak-summer NDVI — is classified into six
colour classes by NDVI and red/green-ratio thresholds. Per-date distributions
feed the best-window, ranking, and forecast analytics (`prototype/foliage.py`).
Ground evidence (`prototype/ground.py`) is fetched live and archived daily by
a GitHub Action.

**Honest status:** the colour classes are *uncalibrated heuristics* — early
yellowing registers late (human observers nearby reported 40% change while
the NDVI-based classes still read green). The 2026 season is being recorded
daily precisely to measure and fix this — see `docs/PRD.md` §27 (SC-03) and
`docs/tool-survey.md`.

## Data sources & licences

| Source | Role | Licence |
|---|---|---|
| Sentinel-2 L2A (Earth Search / AWS) | imagery | Copernicus — open, attributed |
| PhenoCam Network | ground cameras | CC-BY 4.0 |
| Ontario Parks fall report | human labels | Crown © — non-commercial, attributed |
| OSM / Nominatim | basemap, geocoding | ODbL |

Details and red lines: [`docs/data-licences.md`](docs/data-licences.md).
Contains modified Copernicus Sentinel data (2022–2026).

## Deploying (free)

[Streamlit Community Cloud](https://share.streamlit.io): point it at this
repo, main file `prototype/app.py`. The bundled snapshot makes it work
immediately; the daily GitHub Action keeps the data fresh.

## Project documents

- [`docs/PRD.md`](docs/PRD.md) — requirements & system spec (v0.1)
- [`docs/tool-survey.md`](docs/tool-survey.md) — survey of free/open data sources
- [`docs/data-licences.md`](docs/data-licences.md) — licence obligations
- [`AGENTS.md`](AGENTS.md) — conventions for contributors and AI coding agents

## Licence

Code: MIT. Fetched data keeps its own licences (see above).

### Note for development on exFAT drives (macOS)

macOS creates AppleDouble `._*` files on exFAT volumes that can corrupt the
git object store. Before git operations in a working copy on such a drive:

```sh
find .git -name '._*' -delete
```
