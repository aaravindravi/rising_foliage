# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pandas"]
# ///
"""Ground evidence: PhenoCam daily greenness + Ontario Parks fall colour reports.

Attribution requirements:
  PhenoCam data: CC-BY 4.0 — cite the PhenoCam Network (phenocam.nau.edu).
  Ontario Parks reports: (c) King's Printer for Ontario — non-commercial use.

Run standalone to refresh caches:  uv run prototype/ground.py
"""

import datetime as dt
import io
import json
import re
from pathlib import Path

import pandas as pd
import requests

GROUND_DIR = Path(__file__).parent / "output" / "ground"
PHENOCAM_SITE = "turkeypointurban"  # Hamilton, ON — closest camera to Milton
PHENOCAM_CSV = ("https://phenocam.nau.edu/data/archive/{site}/ROI/"
                "{site}_DB_1000_1day.csv")
PARKS_URL = "https://www.ontarioparks.ca/fallcolour"
UA = {"User-Agent": "fall-colour-trip-planner/0.1 (open-source research)"}

# Parks closest to the Milton / escarpment prototype area, with coordinates
# so reports can be ranked by distance from any analyzed place
PARK_COORDS = {
    "Bronte Creek": (43.407, -79.759),
    "Forks of the Credit": (43.826, -80.010),
    "Mono Cliffs": (44.023, -80.074),
    "Earl Rowe": (44.152, -79.905),
    "Craigleith": (44.541, -80.336),
    "Sibbald Point": (44.327, -79.323),
    "Darlington": (43.872, -78.770),
    "Algonquin": (45.584, -78.469),
}
NEARBY_PARKS = list(PARK_COORDS)


def parks_by_distance(reports: list, lat: float, lon: float) -> list:
    """Reports that have known coordinates, sorted by distance (km added)."""
    import math
    out = []
    for r in reports:
        c = PARK_COORDS.get(r["park"])
        if not c:
            continue
        km = 111.0 * math.hypot(c[0] - lat,
                                (c[1] - lon) * math.cos(math.radians(lat)))
        out.append({**r, "distance_km": round(km)})
    return sorted(out, key=lambda r: r["distance_km"])


def _fresh(path: Path, max_age_hours: float) -> bool:
    if not path.exists():
        return False
    age = dt.datetime.now().timestamp() - path.stat().st_mtime
    return age < max_age_hours * 3600


def phenocam_sites(max_age_hours: float = 168.0) -> list:
    """All PhenoCam sites with coordinates (cached weekly)."""
    GROUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = GROUND_DIR / "phenocam_sites.json"
    if not _fresh(cache, max_age_hours):
        r = requests.get("https://phenocam.nau.edu/api/cameras/"
                         "?format=json&limit=3000", headers=UA, timeout=60)
        r.raise_for_status()
        data = r.json()
        cache.write_text(json.dumps(data.get("results", data)))
    return json.loads(cache.read_text())


def _site_db_roi(site: str) -> str | None:
    """Deciduous-broadleaf 1-day ROI id for a site (dir-listing scrape, cached)."""
    GROUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = GROUND_DIR / "phenocam_rois.json"
    rois = json.loads(cache.read_text()) if cache.exists() else {}
    if site not in rois:
        try:
            html = requests.get(f"https://phenocam.nau.edu/data/archive/"
                                f"{site}/ROI/", headers=UA, timeout=30).text
            found = re.findall(rf"{site}_([A-Z]{{2}}_\d{{4}})_1day\.csv", html)
            db = [x for x in found if x.startswith("DB")]
            rois[site] = db[0] if db else None
        except requests.RequestException:
            return None  # transient — don't cache failures
        cache.write_text(json.dumps(rois))
    return rois[site]


def nearest_phenocam(lat: float, lon: float, max_km: float = 150.0):
    """Nearest camera with a deciduous-forest ROI. Returns (site, km, roi)."""
    import math
    cands = []
    for s in phenocam_sites():
        try:
            slat, slon = float(s.get("Lat")), float(s.get("Lon"))
        except (TypeError, ValueError):
            continue
        km = 111.0 * math.hypot(slat - lat,
                                (slon - lon) * math.cos(math.radians(lat)))
        if km <= max_km:
            cands.append((km, s.get("Sitename")))
    for km, site in sorted(cands)[:8]:
        roi = _site_db_roi(site)
        if roi:
            return site, round(km), roi
    return PHENOCAM_SITE, None, "DB_1000"  # fallback: Hamilton


def phenocam_gcc(site: str = PHENOCAM_SITE, roi: str = "DB_1000",
                 max_age_hours: float = 24.0) -> pd.DataFrame:
    """Daily GCC/RCC time series for a PhenoCam site (cached)."""
    GROUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = GROUND_DIR / f"phenocam_{site}_{roi}_1day.csv"
    if not _fresh(cache, max_age_hours):
        r = requests.get(f"https://phenocam.nau.edu/data/archive/{site}/ROI/"
                         f"{site}_{roi}_1day.csv", headers=UA, timeout=60)
        r.raise_for_status()
        cache.write_text(r.text)
    df = pd.read_csv(cache, comment="#")
    df["date"] = pd.to_datetime(df["date"])
    gcc = "gcc_90" if "gcc_90" in df.columns else "midday_gcc"
    rcc = "rcc_90" if "rcc_90" in df.columns else "midday_rcc"
    return df[["date", gcc, rcc]].rename(columns={gcc: "gcc", rcc: "rcc"})


def ontario_parks_reports(max_age_hours: float = 12.0) -> list:
    """Current fall colour reports for all Ontario Parks (cached + archived)."""
    GROUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = GROUND_DIR / "onparks_latest.json"
    if _fresh(cache, max_age_hours):
        return json.loads(cache.read_text())

    html = requests.get(PARKS_URL, headers=UA, timeout=60).text
    reports = []
    for block in re.findall(r'<div class="report-data">(.*?)</div>', html,
                            re.S):
        m = re.search(
            r"<strong>(.*?)</strong>\s*-\s*<strong>Report Date\s*:</strong>\s*"
            r"([^<]+)<br>\s*<strong>Dominant Colour\s*:</strong>\s*([^<]+)<br>"
            r"\s*<strong>Colour Change\s*:</strong>\s*([\d.]+)\s*-\s*"
            r"Leaf Fall\s*:\s*([\d.]+)", block)
        if not m:
            continue
        best = re.search(r"<strong>Best viewing\s*:</strong>\s*(.*)", block, re.S)
        reports.append({
            "park": m.group(1).strip(),
            "report_date": str(pd.to_datetime(m.group(2).strip()).date()),
            "dominant_colour": m.group(3).strip(),
            "colour_change_pct": float(m.group(4)),
            "leaf_fall_pct": float(m.group(5)),
            "best_viewing": re.sub(r"<[^>]+>", "", best.group(1)).strip()
            if best else "",
        })
    if reports:
        cache.write_text(json.dumps(reports, indent=1))
        # archive so a season's history accumulates across fetches
        hist_path = GROUND_DIR / "onparks_history.csv"
        hist = pd.DataFrame(reports).drop(columns=["best_viewing"])
        if hist_path.exists():
            old = pd.read_csv(hist_path)
            hist = pd.concat([old, hist]).drop_duplicates(
                subset=["park", "report_date"], keep="last")
        hist.to_csv(hist_path, index=False)
    return reports


def geocode(query: str):
    """Postal code / place-name lookup via OSM Nominatim (free, 1 req/s,
    attribution required). Returns (display_name, lat, lon) or None."""
    for q in (query, f"{query}, Ontario, Canada"):
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": q, "format": "json", "limit": 1,
                                 "countrycodes": "ca"},
                         headers=UA, timeout=30)
        r.raise_for_status()
        res = r.json()
        if res:
            return (res[0]["display_name"], float(res[0]["lat"]),
                    float(res[0]["lon"]))
    return None


INAT_API = "https://api.inaturalist.org/v1/observations"


def inaturalist_recent(bbox: tuple, days: int = 21, per_page: int = 12,
                       max_age_hours: float = 12.0) -> list:
    """Recent geotagged photo observations inside a bbox (w, s, e, n)."""
    GROUND_DIR.mkdir(parents=True, exist_ok=True)
    cache = GROUND_DIR / (f"inat_{bbox[0]:.3f}_{bbox[1]:.3f}.json"
                          .replace("-", "m"))
    if _fresh(cache, max_age_hours):
        return json.loads(cache.read_text())
    params = {"swlng": bbox[0], "swlat": bbox[1], "nelng": bbox[2],
              "nelat": bbox[3], "photos": "true", "verifiable": "true",
              "d1": (dt.date.today() - dt.timedelta(days=days)).isoformat(),
              "order_by": "observed_on", "order": "desc",
              "per_page": per_page}
    r = requests.get(INAT_API, params=params, headers=UA, timeout=60)
    r.raise_for_status()
    out = []
    for o in r.json().get("results", []):
        photos = o.get("photos") or []
        if not photos:
            continue
        out.append({
            "date": o.get("observed_on") or "",
            "url": (photos[0].get("url") or "").replace("square", "medium"),
            "attribution": photos[0].get("attribution") or "",
            "taxon": (o.get("taxon") or {}).get("preferred_common_name") or "",
            "link": o.get("uri") or "",
        })
    cache.write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    gcc = phenocam_gcc()
    print(f"PhenoCam {PHENOCAM_SITE}: {len(gcc)} days, "
          f"{gcc['date'].min().date()} -> {gcc['date'].max().date()}")
    print(gcc.tail(3).to_string(index=False))
    reps = ontario_parks_reports()
    print(f"\nOntario Parks: {len(reps)} reports")
    for r in reps:
        if r["park"] in NEARBY_PARKS:
            print(f"  {r['park']}: {r['dominant_colour']}, "
                  f"{r['colour_change_pct']:.0f}% change, "
                  f"{r['leaf_fall_pct']:.0f}% leaf fall ({r['report_date']})")
