# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "streamlit~=1.40",
#     "streamlit-folium~=0.27",
#     "folium",
#     "numpy",
#     "pandas",
#     "matplotlib",
#     "pystac-client~=0.9",
#     "odc-stac~=0.5",
#     "xarray",
#     "requests",
# ]
# ///
"""Smoke test: data integrity + the app renders and reacts, no network needed
beyond ground-evidence fetches (which fail soft).

Run:  uv run prototype/smoke_test.py
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import foliage

FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global FAIL
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAIL += 1


print("1. Data integrity")
places = foliage.available_places()
check("places on disk", len(places) >= 1, f"{len(places)} found")
for key in places:
    meta, stacks = foliage.load_place(key)
    dists_ok = all(abs(sum(d.values()) - 1) < 0.02
                   for d in meta["distributions"].values())
    dates_ok = all(d in stacks for d in meta["dates"])
    check(key, dists_ok and dates_ok,
          f"{len(meta['dates'])} dates, years {meta['years']}")

print("2. Analytics")
meta = foliage.load_meta(sorted(places)[0])
win = foliage.best_window(meta)
check("best_window", win is None or (240 < win[0] <= win[1] < 330),
      f"{win}")
ens = foliage.forecast_ensemble(meta)
check("forecast_ensemble", ens is None or
      (len(ens[1]) >= 1 and all(0 <= v <= 1 for t in ens[1] for v in t)))
exp = foliage.expected_coverage(meta, 297)  # ~Oct 24
check("expected_coverage Oct 24", exp is None or 0 <= exp <= 1, f"{exp}")

print("3. App renders (AppTest)")
from streamlit.testing.v1 import AppTest

at = AppTest.from_file(str(Path(__file__).parent / "app.py"),
                       default_timeout=300)
at.run()
check("no exceptions on load", not at.exception,
      "; ".join(str(e.value)[:80] for e in at.exception))
check("hero present", bool(at.success or at.info))
check("ranking table present", bool(at.dataframe))

print("4. App reacts")
future = dt.date.today() + dt.timedelta(days=24)
at.date_input[0].set_value(future).run()
check(f"visit date -> {future}", not at.exception)
sl = at.select_slider[0]
sl.set_range("orange", "red").run()
check("colour range -> orange–red", not at.exception)

print(f"\n{'ALL PASS' if FAIL == 0 else f'{FAIL} FAILURE(S)'}")
sys.exit(1 if FAIL else 0)
