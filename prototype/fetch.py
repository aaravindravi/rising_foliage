# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pystac-client~=0.9",
#     "odc-stac~=0.5",
#     "xarray",
#     "numpy",
#     "pandas",
#     "matplotlib",
# ]
# ///
"""Fetch + classify fall seasons for a place (preset or custom coordinates).

Examples:
  uv run prototype/fetch.py --place kelso --years 2022-2026
  uv run prototype/fetch.py --lat 44.026 --lon -80.075 --name "Mono Cliffs" --years 2025,2026
"""

import argparse

import foliage


def parse_years(spec: str) -> list:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", choices=sorted(foliage.PLACES), default=None)
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--name", default=None, help="display name for custom areas")
    ap.add_argument("--years", default="2026")
    args = ap.parse_args()

    if args.place:
        key, name = args.place, foliage.PLACES[args.place]["name"]
        lat, lon = foliage.PLACES[args.place]["lat"], foliage.PLACES[args.place]["lon"]
    elif args.lat is not None and args.lon is not None:
        name = args.name or f"{args.lat:.3f}, {args.lon:.3f}"
        key = args.name.lower().replace(" ", "-") if args.name else \
            f"{args.lat:.3f}_{args.lon:.3f}".replace(".", "p").replace("-", "m")
        lat, lon = args.lat, args.lon
    else:
        ap.error("give --place or --lat/--lon")

    bbox = foliage.bbox_around(lat, lon)
    print(f"{name} — bbox {bbox}")
    for year in parse_years(args.years):
        season = foliage.fetch_year(bbox, year,
                                    fallback_canopy=foliage.existing_canopy(key))
        usable = [k for k in season if not k.startswith("_")]
        if usable:
            foliage.persist(key, name, bbox, year, season)
            print(f"[{year}] persisted {len(usable)} scenes")
        else:
            print(f"[{year}] nothing usable")


if __name__ == "__main__":
    main()
