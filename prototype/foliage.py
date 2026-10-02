"""Shared prototype library: fetch Sentinel-2, classify foliage colour, persist per place.

Data layout (all regenerable, gitignored):
  prototype/output/places/<place>/meta.json        dates, distributions, bbox, ...
  prototype/output/places/<place>/classified.npz   per-date class rasters + per-year canopy
  prototype/output/places/<place>/rgb_<date>.png   true-colour quicklooks
"""

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"

CLASSES = ["green", "yellow-green", "yellow", "orange", "red", "brown/bare"]
PALETTE = ["#2d7d2d", "#9acd32", "#ffd700", "#ff8c00", "#cc2200", "#8b6f47"]
SCL_CLEAR = (4, 5)

PLACES = {
    "kelso": {"name": "Kelso Summit / Milton", "lat": 43.506, "lon": -79.960},
    "rattlesnake": {"name": "Rattlesnake Point", "lat": 43.470, "lon": -79.953},
    "hilton-falls": {"name": "Hilton Falls", "lat": 43.508, "lon": -80.011},
    "forks-credit": {"name": "Forks of the Credit", "lat": 43.823, "lon": -80.020},
    "mono-cliffs": {"name": "Mono Cliffs", "lat": 44.026, "lon": -80.075},
    "dundas-peak": {"name": "Dundas Peak / Spencer Gorge", "lat": 43.276, "lon": -79.985},
    "albion-hills": {"name": "Albion Hills", "lat": 43.926, "lon": -79.836},
    "bronte-creek": {"name": "Bronte Creek", "lat": 43.407, "lon": -79.759},
    "terra-cotta": {"name": "Terra Cotta", "lat": 43.720, "lon": -79.945},
    "elora-gorge": {"name": "Elora Gorge", "lat": 43.679, "lon": -80.432},
}

OUTPUT_ROOT = Path(__file__).parent / "output" / "places"


def bbox_around(lat: float, lon: float, half_km: float = 1.2) -> tuple:
    dlat = half_km / 111.0
    dlon = half_km / (111.0 * math.cos(math.radians(lat)))
    return (round(lon - dlon, 5), round(lat - dlat, 5),
            round(lon + dlon, 5), round(lat + dlat, 5))


def clear_fraction(scl: np.ndarray) -> float:
    valid = scl > 0
    if valid.sum() == 0:
        return 0.0
    return float(np.isin(scl, SCL_CLEAR).sum() / valid.sum())


def classify(red, green, blue, nir, scl, canopy) -> np.ndarray:
    """Classify canopy pixels into 0..5 (CLASSES); -1 elsewhere/obscured.

    Heuristic thresholds on reflectance — uncalibrated (spike-grade)."""
    clear = np.isin(scl, SCL_CLEAR)
    usable = canopy & clear & (red + green + blue > 0)
    ndvi = np.where(nir + red > 0, (nir - red) / (nir + red + 1e-6), 0.0)

    out = np.full(red.shape, -1, dtype="i2")
    brown = usable & (ndvi < 0.4)
    green_cls = usable & ~brown & (ndvi >= 0.75) & (green >= red)
    ygreen = usable & ~brown & ~green_cls & (ndvi >= 0.6) & (green >= red * 0.9)
    remaining = usable & ~brown & ~green_cls & ~ygreen
    rg = np.where(green > 0, red / (green + 1e-6), 0.0)
    out[green_cls] = 0
    out[ygreen] = 1
    out[remaining & (rg < 1.15)] = 2
    out[remaining & (rg >= 1.15) & (rg < 1.45)] = 3
    out[remaining & (rg >= 1.45)] = 4
    out[brown] = 5
    return out


def distribution(classified: np.ndarray) -> dict:
    n = int((classified >= 0).sum())
    if n == 0:
        return {}
    return {c: float((classified == i).sum() / n) for i, c in enumerate(CLASSES)}


def fetch_year(bbox: tuple, year: int, log=print, fallback_canopy=None) -> dict:
    """Fetch+classify one fall season. Returns {date: {"cls", "rgb", "dist", "cf"}},
    plus "_canopy". Empty dict if season unusable."""
    from odc.stac import load as stac_load
    from pystac_client import Client

    end = dt.date(year, 11, 20)
    today = dt.date.today()
    if year == today.year:
        end = min(end, today)
    items = []
    for collection in (COLLECTION, "sentinel-2-l2a"):  # legacy fallback: c1 has archive gaps
        search = Client.open(STAC_URL).search(
            collections=[collection], bbox=bbox,
            datetime=f"{year}-09-01/{end.isoformat()}",
            query={"eo:cloud_cover": {"lt": 70}})
        items = list(search.items())
        if items:
            break
    log(f"[{year}] {len(items)} candidate scenes")
    if not items:
        return {}
    # c1 assets are raw DN with a +1000 offset; the legacy collection's COGs
    # already have the offset applied — subtracting twice reads green as yellow.
    dn_offset = 1000.0 if collection == COLLECTION else 0.0
    ds = stac_load(items, bands=["blue", "green", "red", "nir", "scl"],
                   bbox=bbox, resolution=10, groupby="solar_day", chunks={}).compute()
    for b in ("blue", "green", "red", "nir"):
        ds[b] = (ds[b].astype("f4") - dn_offset).clip(min=0.0) / 10000.0

    # Canopy mask: clearest scene with the strongest vegetation signal
    # (any date works — we only need "where is canopy", and forests don't move)
    canopy = None
    for min_clear in (0.75, 0.6):
        best, best_score = None, -1.0
        for t in ds.time.values:
            s = ds.sel(time=t)
            if clear_fraction(s["scl"].values) < min_clear:
                continue
            ndvi = (s["nir"] - s["red"]) / (s["nir"] + s["red"] + 1e-6)
            score = float(np.nanmedian(ndvi.values))
            if score > best_score:
                best, best_score = t, score
        if best is not None:
            e = ds.sel(time=best)
            ndvi0 = ((e["nir"] - e["red"]) / (e["nir"] + e["red"] + 1e-6)).values
            cand = (ndvi0 > 0.75) & np.isin(e["scl"].values, SCL_CLEAR)
            if cand.mean() >= 0.05:
                canopy = cand
                break
    if canopy is None and fallback_canopy is not None \
            and fallback_canopy.shape == ds["scl"].isel(time=0).shape:
        log(f"[{year}] borrowing canopy mask from another season")
        canopy = fallback_canopy
    if canopy is None:
        log(f"[{year}] no usable canopy mask — season skipped")
        return {}
    if canopy.mean() < 0.05:
        log(f"[{year}] <5% canopy in AOI — not a forested area? season skipped")
        return {}

    result = {"_canopy": canopy}
    for t in ds.time.values:
        s = ds.sel(time=t)
        cf = clear_fraction(s["scl"].values)
        date = str(t)[:10]
        if cf < 0.6:
            log(f"  {date}: skipped ({cf * 100:.0f}% clear)")
            continue
        cls = classify(s["red"].values, s["green"].values, s["blue"].values,
                       s["nir"].values, s["scl"].values, canopy)
        dist = distribution(cls)
        if not dist:
            continue
        rgb = np.dstack([s[b].values for b in ("red", "green", "blue")])
        rgb = np.clip(rgb / 0.25, 0, 1) ** (1 / 2.2)
        result[date] = {"cls": cls, "rgb": rgb, "dist": dist, "cf": round(cf, 2)}
        top = max(dist, key=dist.get)
        log(f"  {date}: clear {cf * 100:.0f}% | dominant {top} {dist[top] * 100:.0f}%")
    return result


def persist(place_key: str, place_name: str, bbox: tuple, year: int,
            season: dict) -> None:
    """Merge one fetched season into the place's on-disk data."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pdir = OUTPUT_ROOT / place_key
    pdir.mkdir(parents=True, exist_ok=True)
    meta_path = pdir / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {
        "place": place_name, "bbox": list(bbox), "classes": CLASSES,
        "palette": PALETTE, "distributions": {}, "clear_frac": {}}
    npz_path = pdir / "classified.npz"
    arrays = dict(np.load(npz_path)) if npz_path.exists() else {}

    arrays[f"canopy_{year}"] = season["_canopy"]
    for date, d in season.items():
        if date.startswith("_"):
            continue
        arrays[date] = d["cls"]
        meta["distributions"][date] = {c: round(v, 4) for c, v in d["dist"].items()}
        meta["clear_frac"][date] = d["cf"]
        plt.imsave(pdir / f"rgb_{date}.png", d["rgb"])

    meta["dates"] = sorted(k for k in meta["distributions"])
    meta["years"] = sorted({int(d[:4]) for d in meta["dates"]})
    np.savez_compressed(npz_path, **arrays)
    meta_path.write_text(json.dumps(meta, indent=1))


def existing_canopy(place_key: str):
    """Most recent stored canopy mask for a place, or None."""
    npz_path = OUTPUT_ROOT / place_key / "classified.npz"
    if not npz_path.exists():
        return None
    arrays = np.load(npz_path)
    keys = sorted(k for k in arrays.files if k.startswith("canopy_"))
    return arrays[keys[-1]] if keys else None


def load_place(place_key: str):
    pdir = OUTPUT_ROOT / place_key
    meta = json.loads((pdir / "meta.json").read_text())
    return meta, np.load(pdir / "classified.npz")


def load_meta(place_key: str) -> dict:
    return json.loads((OUTPUT_ROOT / place_key / "meta.json").read_text())


def available_places() -> dict:
    """{place_key: display name} for places with fetched data."""
    out = {}
    if OUTPUT_ROOT.exists():
        for p in sorted(OUTPUT_ROOT.iterdir()):
            if p.name.endswith(".old"):
                continue
            if (p / "meta.json").exists():
                out[p.name] = json.loads((p / "meta.json").read_text())["place"]
    return out


def best_window(meta: dict, want=("yellow", "orange", "red"),
                min_cov: float = 0.3):
    """Historical best-viewing window for the wanted colours.

    Per past season, interpolate the wanted-colour coverage across the fall and
    find the span where it holds >= 75% of that season's peak (and a floor).
    Returns (start_doy, end_doy, n_seasons, typical_peak_cov) or None."""
    spans, peaks = [], []
    for y in meta["years"]:
        pts = sorted((dt.date.fromisoformat(d).timetuple().tm_yday,
                      sum(meta["distributions"][d][c] for c in want))
                     for d in meta["dates"] if d.startswith(str(y)))
        if len(pts) < 3:
            continue
        xs, vs = zip(*pts)
        grid = np.arange(min(xs), max(xs) + 1)
        curve = np.interp(grid, xs, vs)
        pk = float(curve.max())
        if pk < 0.15:
            continue  # season never showed these colours (or data too sparse)
        good = grid[curve >= max(min_cov, 0.75 * pk)]
        if len(good):
            spans.append((int(good.min()), int(good.max())))
            peaks.append(pk)
    if not spans:
        return None
    start = int(np.median([s for s, _ in spans]))
    end = int(np.median([e for _, e in spans]))
    return start, end, len(spans), float(np.median(peaks))


def doy_to_date(doy: int, year: int) -> dt.date:
    return dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)


def expected_coverage(meta: dict, doy: int, want=("yellow", "orange", "red")):
    """Median historical coverage of the wanted colours on this day-of-year,
    interpolated per past season. None if no season brackets the date."""
    vals = []
    for y in meta["years"]:
        pts = sorted((dt.date.fromisoformat(d).timetuple().tm_yday,
                      sum(meta["distributions"][d][c] for c in want))
                     for d in meta["dates"] if d.startswith(str(y)))
        if len(pts) < 2:
            continue
        xs, vs = zip(*pts)
        if min(xs) - 7 <= doy <= max(xs) + 7:
            vals.append(float(np.interp(doy, xs, vs)))
    return float(np.median(vals)) if vals else None


def forecast_ensemble(meta: dict, want=("yellow", "orange", "red"),
                      horizon: int = 21):
    """Per-past-year trajectories of wanted-colour coverage, each anchored at
    the latest observation. The spread across years IS the uncertainty.
    Returns (future_dates, trajectories, anchor_date, anchor_cov) or None."""
    dates = meta["dates"]
    if not dates:
        return None
    latest = dates[-1]
    latest_year = int(latest[:4])
    doy = lambda s: dt.date.fromisoformat(s).timetuple().tm_yday
    anchor_cov = sum(meta["distributions"][latest][c] for c in want)
    grid = np.arange(doy(latest), doy(latest) + horizon + 1)
    trajs = []
    for y in sorted({int(d[:4]) for d in dates if int(d[:4]) < latest_year}):
        pts = sorted((doy(d), sum(meta["distributions"][d][c] for c in want))
                     for d in dates if d.startswith(str(y)))
        if len(pts) < 2:
            continue
        xs, vs = zip(*pts)
        curve = np.interp(grid, xs, vs)
        trajs.append(np.clip(anchor_cov + (curve - curve[0]), 0.0, 1.0))
    if not trajs:
        return None
    base = dt.date.fromisoformat(latest)
    fdates = [base + dt.timedelta(days=int(i)) for i in range(horizon + 1)]
    return fdates, trajs, latest, anchor_cov


def climatology_forecast(meta: dict, horizon: int = 14):
    """Naive forecast: anchor the latest observation, add the multi-year mean
    day-of-year colour trend. Returns list of rows or None if no history."""
    dates = meta["dates"]
    if not dates:
        return None
    latest = dates[-1]
    latest_year = int(latest[:4])
    past = [d for d in dates if int(d[:4]) < latest_year]
    years = sorted({int(d[:4]) for d in past})
    if not years:
        return None

    doy = lambda s: dt.date.fromisoformat(s).timetuple().tm_yday
    grid = np.arange(doy(latest), doy(latest) + horizon + 1)
    obs = meta["distributions"][latest]
    clim = {}
    for c in meta["classes"]:
        curves = []
        for y in years:
            pts = sorted((doy(d), meta["distributions"][d][c])
                         for d in past if int(d[:4]) == y)
            if len(pts) >= 2:
                xs, vs = zip(*pts)
                curves.append(np.interp(grid, xs, vs))
        clim[c] = np.mean(curves, axis=0) if curves else np.full(len(grid), obs[c])

    base = dt.date.fromisoformat(latest)
    rows = []
    for i in range(1, horizon + 1):
        raw = {c: max(0.0, obs[c] + float(clim[c][i] - clim[c][0]))
               for c in meta["classes"]}
        s = sum(raw.values()) or 1.0
        rows.append({"date": (base + dt.timedelta(days=i)).isoformat(),
                     "horizon": i, "anchor": latest,
                     "dist": {c: raw[c] / s for c in meta["classes"]},
                     "confidence": ("moderate" if i <= 3 else
                                    "low" if i <= 7 else "very low")})
    return rows
