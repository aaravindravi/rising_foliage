# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pystac-client~=0.9",
#     "odc-stac~=0.5",
#     "xarray",
#     "numpy",
#     "pandas",
#     "matplotlib",
#     "requests",
# ]
# ///
"""Daily refresh: new satellite scenes for every analyzed place + ground
evidence archives. Run by .github/workflows/daily-refresh.yml (or cron).

Idempotent — re-running merges by date and changes nothing if no new data.
"""

import datetime as dt

import foliage
import ground


def main() -> None:
    today = dt.date.today()
    if dt.date(today.year, 9, 1) <= today <= dt.date(today.year, 11, 25):
        for key in sorted(foliage.available_places()):
            meta = foliage.load_meta(key)
            before = len(meta["dates"])
            season = foliage.fetch_year(
                tuple(meta["bbox"]), today.year, log=lambda s: None,
                fallback_canopy=foliage.existing_canopy(key))
            usable = [k for k in season if not k.startswith("_")]
            if usable:
                foliage.persist(key, meta["place"], tuple(meta["bbox"]),
                                today.year, season)
                after = len(foliage.load_meta(key)["dates"])
                print(f"{key}: {after - before:+d} new scene(s)")
            else:
                print(f"{key}: no usable new scenes")
    else:
        print("outside fall season — skipping satellite refresh")

    reports = ground.ontario_parks_reports(max_age_hours=0)
    print(f"Ontario Parks: archived {len(reports)} reports")
    try:
        gcc = ground.phenocam_gcc(max_age_hours=0)
        print(f"PhenoCam: through {gcc['date'].max().date()}")
    except Exception as e:
        print(f"PhenoCam refresh failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
