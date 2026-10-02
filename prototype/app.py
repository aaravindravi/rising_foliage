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
"""Rising Foliage — viewer/planner prototype.

- Browse observed foliage colour distributions by place, year, and date.
- Experimental forecast: latest observation + multi-year climatology trend.
- Analyze new areas: presets, custom coordinates, or click the map.

Run:  uv run prototype/app.py      (self-bootstraps `streamlit run`)
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # sibling modules, regardless of cwd

import numpy as np

import foliage
import ground


def bootstrap() -> None:
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", __file__, "--server.headless=true"]
    sys.exit(stcli.main())


CLASS_EMOJI = {"green": "🟢", "yellow-green": "🍏", "yellow": "🟡",
               "orange": "🟠", "red": "🔴", "brown/bare": "🟤"}


def colour_range_slider(st, key: str, default=("yellow", "red")) -> list:
    """Visual colour-range picker: gradient bar + two-handle slider.
    Returns the contiguous list of selected classes."""
    n = len(foliage.CLASSES)
    stops = ", ".join(f"{c} {i / n * 100:.0f}%, {c} {(i + 1) / n * 100:.0f}%"
                      for i, c in enumerate(foliage.PALETTE))
    st.markdown(f"<div style='height:14px;border-radius:7px;margin:0 0 -8px 0;"
                f"background:linear-gradient(to right, {stops})'></div>",
                unsafe_allow_html=True)
    lo, hi = st.select_slider(
        "Colour range you want to see", options=foliage.CLASSES, value=default,
        key=key, format_func=lambda c: f"{CLASS_EMOJI[c]} {c}")
    i0, i1 = foliage.CLASSES.index(lo), foliage.CLASSES.index(hi)
    return foliage.CLASSES[i0:i1 + 1]


def dist_panel(st, dist: dict, key: str) -> None:
    """Colour swatch list + colour-range matcher for one distribution."""
    for c, p in zip(foliage.CLASSES, foliage.PALETTE):
        st.markdown(
            f"<span style='display:inline-block;width:0.9em;height:0.9em;"
            f"background:{p};border-radius:2px'></span> {c}: "
            f"**{dist[c] * 100:.0f}%**", unsafe_allow_html=True)


def overlay_map(st, st_folium, folium, arr, bbox, label, clickable=False):
    rgba = np.zeros((*arr.shape, 4), dtype="u1")
    for i, hexc in enumerate(foliage.PALETTE):
        c = tuple(int(hexc[j:j + 2], 16) for j in (1, 3, 5))
        rgba[arr == i] = (*c, 210)
    # fixed zoom, not fit_bounds: hidden-tab mounts have zero-size containers,
    # which makes fit_bounds compute garbage (max zoom)
    m = folium.Map(location=[(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2],
                   zoom_start=14, tiles="OpenStreetMap")
    folium.raster_layers.ImageOverlay(
        rgba, bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]], name=label).add_to(m)
    folium.LayerControl().add_to(m)
    return st_folium(m, height=520, use_container_width=True,
                     returned_objects=["last_clicked"] if clickable else [])


def ground_strip(st, bbox, dist=None):
    """Compact live ground-evidence cards; optional satellite comparison."""
    lat0, lon0 = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
    try:
        site, km, roi = ground.nearest_phenocam(lat0, lon0)
        gcc = ground.phenocam_gcc(site, roi)
        last = gcc.dropna().iloc[-1]
        turning = bool(last["rcc"] > last["gcc"])
        reps = ground.ontario_parks_reports()
    except Exception as e:
        st.caption(f"Ground evidence unavailable right now ({e}).")
        return
    near = ground.parks_by_distance(reps, lat0, lon0)
    cols = st.columns(3)
    cam_label = (f"Nearest forest cam · {site} · {km} km away" if km is not None
                 else f"Canopy cam (fallback) · {site}")
    cols[0].metric(cam_label, "🍁 turning" if turning else "🌳 still green",
                   delta=f"PhenoCam, {last['date'].date()}", delta_color="off")
    if near:
        r = near[0]
        cols[1].metric(f"{r['park']} observers · {r['distance_km']} km",
                       f"{r['colour_change_pct']:.0f}% changed",
                       delta=f"{r['dominant_colour']} · {r['report_date']}",
                       delta_color="off")
    if dist is not None:
        nongreen = (1 - dist["green"]) * 100
        gap = (f"humans report {near[0]['colour_change_pct']:.0f}% nearby"
               if near else None)
        cols[2].metric("Satellite non-green here", f"{nongreen:.0f}%",
                       delta=gap, delta_color="off")


def run_fetch(st, key, name, lat, lon, years):
    bbox = foliage.bbox_around(lat, lon)
    prog = st.progress(0.0, text=f"Fetching {name}…")
    done_any = False
    for i, year in enumerate(years):
        prog.progress(i / len(years), text=f"{name}: fetching fall {year} "
                                           f"(~1–2 min per season)")
        season = foliage.fetch_year(bbox, year, log=lambda s: None,
                                    fallback_canopy=foliage.existing_canopy(key))
        if any(not k.startswith("_") for k in season):
            foliage.persist(key, name, bbox, year, season)
            done_any = True
    prog.progress(1.0, text="Done")
    if done_any:
        st.session_state["place"] = key
        st.rerun()
    else:
        st.error("No usable scenes for that area/years (clouds, or not forested).")


def main() -> None:
    import folium
    import pandas as pd
    import streamlit as st
    from streamlit_folium import st_folium

    st.set_page_config(page_title="Rising Foliage", page_icon="🍁",
                       layout="wide")

    places = foliage.available_places()

    # ---------- sidebar: place selection + new-area analysis ----------
    with st.sidebar:
        st.header("Destination")
        if not places:
            st.error("No data yet — run:\n`uv run prototype/fetch.py --place kelso "
                     "--years 2022-2026`")
            st.stop()
        keys = list(places)
        default = st.session_state.get("place", keys[0])
        place_key = st.selectbox("Analyzed areas", keys,
                                 index=keys.index(default) if default in keys else 0,
                                 format_func=lambda k: places[k])
        st.session_state["place"] = place_key

        FETCH_YEARS = [2022, 2023, 2024, 2026]
        with st.expander("➕ Analyze a new area"):
            q = st.text_input("📮 Postal code or place name",
                              placeholder="e.g. L9T 2X5 or Tobermory")
            if st.button("🔎 Find & analyze (~4–6 min)") and q.strip():
                try:
                    hit = ground.geocode(q.strip())
                except Exception:
                    hit = None
                if not hit:
                    st.error("Couldn't find that — try adding the town or "
                             "province.")
                else:
                    gname, glat, glon = hit
                    st.caption(f"📍 {gname[:90]}")
                    run_fetch(st, q.strip().lower().replace(" ", ""),
                              q.strip().title(), glat, glon, FETCH_YEARS)
            st.caption("Search by OpenStreetMap Nominatim.")
            st.divider()
            preset_opts = {k: v["name"] for k, v in foliage.PLACES.items()
                           if k not in places}
            if preset_opts:
                pk = st.selectbox("Preset destination", list(preset_opts),
                                  format_func=lambda k: preset_opts[k])
                if st.button("Fetch preset (~4–6 min)"):
                    p = foliage.PLACES[pk]
                    run_fetch(st, pk, p["name"], p["lat"], p["lon"],
                              FETCH_YEARS)
            st.caption("Or exact coordinates:")
            lat = st.number_input("Latitude", value=43.506, format="%.4f")
            lon = st.number_input("Longitude", value=-79.960, format="%.4f")
            name = st.text_input("Name", value="Custom area")
            if st.button("Fetch custom (~4–6 min)"):
                k = name.lower().replace(" ", "-")
                run_fetch(st, k, name, lat, lon, FETCH_YEARS)
            st.caption("Tip: you can also click any map — the observation "
                       "map or the Region map — and use the button that "
                       "appears below it.")

    meta, stacks = foliage.load_place(place_key)
    bbox = meta["bbox"]
    dates = meta["dates"]

    st.title(f"🍁 {meta['place']}")
    st.caption("Prototype — colour classes are uncalibrated heuristics · "
               "Contains modified Copernicus Sentinel data (2022–2026)")

    # ---------- the answer first: when should I go? ----------
    today = dt.date.today()
    in_col, out_col = st.columns([1, 2], gap="large")
    with in_col:
        default_sat = today + dt.timedelta(days=(5 - today.weekday()) % 7 or 7)
        visit = st.date_input("📅 When do you plan to visit?",
                              value=default_sat, min_value=today,
                              max_value=today + dt.timedelta(days=75))
        want = colour_range_slider(st, "hero_want")
    win = foliage.best_window(meta, want=tuple(want))
    with out_col:
        if win:
            s_doy, e_doy, n_seasons, pk = win
            ws = foliage.doy_to_date(s_doy, today.year)
            we = foliage.doy_to_date(e_doy, today.year)
            vdoy = visit.timetuple().tm_yday
            exp = foliage.expected_coverage(meta, vdoy, tuple(want))
            exp_txt = (f" Historically ~**{exp * 100:.0f}%** of this canopy "
                       f"showed your colours on that date." if exp is not None
                       else "")
            if visit < ws - dt.timedelta(days=4):
                verdict = (f"⏳ Your date ({visit:%b %d}) is likely **too "
                           f"early** here — expect mostly green.{exp_txt}")
            elif visit > we + dt.timedelta(days=4):
                verdict = (f"🍂 Your date ({visit:%b %d}) is likely **past "
                           f"peak** — expect browns and bare "
                           f"branches.{exp_txt}")
            else:
                verdict = (f"✅ Your date ({visit:%b %d}) falls **inside** the "
                           f"typical window.{exp_txt}")
            st.success(
                f"### 🎯 Best time for {'–'.join(want)} here: "
                f"~**{ws:%b %d} – {we:%b %d}**\n"
                f"Median of {n_seasons} past seasons at this exact spot "
                f"(typical peak coverage ~{pk * 100:.0f}%).\n\n{verdict}")
        else:
            st.info("🎯 Not enough past-season data here (or these colours "
                    "never reached 15% coverage) for a best-time estimate.")

    tab_obs, tab_region, tab_fc, tab_season, tab_ground = st.tabs(
        ["📷 Observations", "🗺️ Region: when & where", "🔮 Forecast (experimental)",
         "📈 Seasons compared", "🌿 Ground evidence"])

    # ---------- observations ----------
    with tab_obs:
        left, right = st.columns([1, 2], gap="large")
        with left:
            years = meta["years"]
            year = st.selectbox("Year", years, index=len(years) - 1)
            ydates = [d for d in dates if d.startswith(str(year))]
            date = st.select_slider("Observation date", options=ydates,
                                    value=ydates[-1])
            age = (dt.date.today() - dt.date.fromisoformat(date)).days
            st.caption(f"Actual observation ({meta['clear_frac'][date] * 100:.0f}% "
                       f"cloud-free scene, {age} days ago). Dates missing between "
                       "observations were cloud-obscured.")
            dist_panel(st, meta["distributions"][date], "obs")
        st.divider()
        st.markdown("**Live ground evidence near this area**")
        ground_strip(st, bbox,
                     dist=meta["distributions"][date] if age <= 21 else None)
        with right:
            sub3, sub1, sub2 = st.tabs(
                ["📅 Around your visit date", "Classified map", "True colour"])
            with sub1:
                ret = overlay_map(st, st_folium, folium, stacks[date], bbox,
                                  f"Foliage {date}", clickable=True)
                st.caption("White gaps = non-canopy or cloud. Click anywhere on "
                           "the map to analyze that area.")
                clicked = (ret or {}).get("last_clicked")
                if clicked:
                    clat, clon = clicked["lat"], clicked["lng"]
                    if st.button(f"🔍 Analyze 2.4 km area at {clat:.4f}, "
                                 f"{clon:.4f} (2024–2026, ~3–5 min)"):
                        run_fetch(st, f"{clat:.3f}_{clon:.3f}".replace(".", "p")
                                  .replace("-", "m"),
                                  f"Area {clat:.3f}, {clon:.3f}", clat, clon,
                                  [2024, 2025, 2026])
            with sub3:
                vdoy = visit.timetuple().tm_yday
                picks = []
                for y in meta["years"]:
                    if y == today.year:
                        continue
                    cands = [(abs(dt.date.fromisoformat(d).timetuple().tm_yday
                                  - vdoy), d) for d in dates
                             if d.startswith(str(y))]
                    if cands:
                        off, d = min(cands)
                        if off <= 12:
                            picks.append((y, d, off))
                if not picks:
                    st.info(f"No past observation lands within ±12 days of "
                            f"{visit:%b %d} here — cloudy falls. Try a nearby "
                            "date.")
                else:
                    ref_shape = stacks[picks[0][1]].shape
                    arrs = [stacks[d] for _, d, _ in picks
                            if stacks[d].shape == ref_shape]
                    stack = np.stack(arrs)
                    counts = np.stack([(stack == i).sum(0) for i in range(6)])
                    comp = counts.argmax(0).astype("i2")
                    comp[(stack >= 0).sum(0) == 0] = -1
                    st.markdown(f"**Typical look around {visit:%b %d}** — "
                                f"pixel-wise most-common class from "
                                f"{len(arrs)} past year(s):")
                    crgba = np.full((*comp.shape, 4), 255, dtype="u1")
                    for i, hexc in enumerate(foliage.PALETTE):
                        col = tuple(int(hexc[j:j + 2], 16) for j in (1, 3, 5))
                        crgba[comp == i] = (*col, 255)
                    st.image(crgba, width="stretch")
                    mcols = st.columns(len(picks))
                    for (y, d, off), c in zip(picks, mcols):
                        arr = stacks[d]
                        rgba = np.full((*arr.shape, 4), 255, dtype="u1")
                        for i, hexc in enumerate(foliage.PALETTE):
                            col = tuple(int(hexc[j:j + 2], 16)
                                        for j in (1, 3, 5))
                            rgba[arr == i] = (*col, 255)
                        c.image(rgba, caption=f"{d} ({off:+d}d from your "
                                              f"date)", width="stretch")
                    st.caption("Historical appearance, not a forecast — the "
                               "same calendar days in past seasons.")

            with sub2:
                import matplotlib.pyplot as plt
                from PIL import Image

                pdir = foliage.OUTPUT_ROOT / place_key
                ypngs = [d for d in ydates if (pdir / f"rgb_{d}.png").exists()]
                if len(ypngs) >= 2:
                    gif = pdir / f"anim_{year}_{len(ypngs)}.gif"
                    if not gif.exists():
                        frames = []
                        for d in ypngs:
                            fig, ax = plt.subplots(figsize=(5.2, 5.5), dpi=110)
                            ax.imshow(plt.imread(pdir / f"rgb_{d}.png"))
                            ax.set_title(f"{d} · ~11:20 a.m. (Sentinel-2)",
                                         fontsize=12)
                            ax.axis("off")
                            fig.tight_layout()
                            fig.canvas.draw()
                            frames.append(Image.fromarray(np.asarray(
                                fig.canvas.buffer_rgba())).convert("RGB"))
                            plt.close(fig)
                        frames[0].save(gif, save_all=True,
                                       append_images=frames[1:],
                                       duration=900, loop=0)
                    st.markdown(f"**Fall {year} time-lapse** — every usable "
                                "Sentinel-2 pass, capture date on each frame. "
                                "Jumps between frames are cloud gaps.")
                    st.image(str(gif), width="stretch")
                elif len(ypngs) == 1:
                    st.markdown(f"**Satellite photo from {ypngs[0]}, ~11:20 "
                                "a.m. local** — only one usable pass stored "
                                "for this year.")
                    st.image(str(pdir / f"rgb_{ypngs[0]}.png"), width="stretch")
                else:
                    st.info("No quicklooks stored for this year (snapshot-only "
                            "deployment) — the classified map still works.")

    # ---------- region: best windows across all analyzed destinations ----------
    with tab_region:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        rows = []
        for k, nm in places.items():
            m = foliage.load_meta(k)
            w = foliage.best_window(m)
            b = m["bbox"]
            rows.append({
                "key": k, "name": nm, "meta": m,
                "lat": (b[1] + b[3]) / 2, "lon": (b[0] + b[2]) / 2,
                "win": w, "latest": m["dates"][-1] if m["dates"] else None,
                "latest_nongreen": (1 - m["distributions"][m["dates"][-1]]
                                    ["green"]) * 100 if m["dates"] else None})
        est = [r for r in rows if r["win"]]

        # ---- ranking for the user's visit date and colour range ----
        st.markdown(f"#### 🏆 Ranked for your visit — {visit:%A, %b %d} · "
                    f"colours {want[0]} → {want[-1]}")
        vdoy = visit.timetuple().tm_yday
        rank_rows = []
        for r in rows:
            m2 = r["meta"]
            exp = foliage.expected_coverage(m2, vdoy, tuple(want))
            brown = foliage.expected_coverage(m2, vdoy, ("brown/bare",))
            w2 = foliage.best_window(m2, tuple(want))
            if w2:
                ws2 = foliage.doy_to_date(w2[0], today.year)
                we2 = foliage.doy_to_date(w2[1], today.year)
                if visit < ws2 - dt.timedelta(days=4):
                    stat = "⏳ too early"
                elif visit > we2 + dt.timedelta(days=4):
                    stat = "🍂 past peak — skip"
                else:
                    stat = "✅ in window"
                wintxt = f"{ws2:%b %d} – {we2:%b %d}"
            else:
                stat, wintxt = "❓ not enough data", "—"
            rank_rows.append({
                "Park": r["name"],
                "Your colours (expected)": round((exp or 0) * 100),
                "Brown/fallen": f"{(brown or 0) * 100:.0f}%",
                "Status on your date": stat,
                "Typical window": wintxt})
        rank_rows.sort(key=lambda x: x["Your colours (expected)"], reverse=True)
        rank_df = pd.DataFrame(rank_rows)
        rank_df.index = np.arange(1, len(rank_df) + 1)
        st.dataframe(rank_df, width="stretch", column_config={
            "Your colours (expected)": st.column_config.ProgressColumn(
                "Your colours (expected)", format="%d%%",
                min_value=0, max_value=100)})
        st.caption("Expected coverage = median of past seasons at that "
                   "calendar date, per park. Change the date or colour range "
                   "at the top of the page and this re-ranks. High "
                   "brown/fallen or 'past peak' → skip; 'too early' → go "
                   "later or pick a park further along.")
        st.divider()

        def bucket(r):
            mid = (r["win"][0] + r["win"][1]) / 2
            return (0 if mid < 288 else 1 if mid <= 300 else 2)  # ~Oct15/Oct27

        BUCKET_COLOURS = ["#ffd700", "#ff8c00", "#cc2200"]
        BUCKET_NAMES = ["earlier (peaks by ~mid-Oct)",
                        "mid (peaks ~Oct 15–27)", "later (peaks after ~Oct 27)"]

        mcol, gcol2 = st.columns([1, 1], gap="large")
        with mcol:
            m = folium.Map(location=[43.75, -79.95], zoom_start=9,
                           tiles="OpenStreetMap")
            for r in rows:
                if r["win"]:
                    colour = BUCKET_COLOURS[bucket(r)]
                    ws = foliage.doy_to_date(r["win"][0], today.year)
                    we = foliage.doy_to_date(r["win"][1], today.year)
                    html = (f"<b>{r['name']}</b><br>Best: {ws:%b %d} – "
                            f"{we:%b %d}<br>Latest obs {r['latest']}: "
                            f"{r['latest_nongreen']:.0f}% non-green")
                else:
                    colour, html = "#888888", (f"<b>{r['name']}</b><br>"
                                               "Not enough seasons yet")
                folium.CircleMarker(
                    [r["lat"], r["lon"]], radius=10, color=colour, fill=True,
                    fill_color=colour, fill_opacity=0.85,
                    tooltip=r["name"],
                    popup=folium.Popup(html, max_width=220)).add_to(m)
            rret = st_folium(m, height=480, use_container_width=True,
                             returned_objects=["last_clicked"],
                             key="regionmap")
            rclick = (rret or {}).get("last_clicked")
            if rclick:
                rlat, rlon = rclick["lat"], rclick["lng"]
                if st.button(f"🔍 Analyze 2.4 km area at {rlat:.4f}, "
                             f"{rlon:.4f} (~4–6 min)", key="regionclickbtn"):
                    run_fetch(st, f"{rlat:.3f}_{rlon:.3f}".replace(".", "p")
                              .replace("-", "m"),
                              f"Area {rlat:.3f}, {rlon:.3f}", rlat, rlon,
                              [2022, 2023, 2024, 2026])
            st.caption("● " + " · ".join(
                f"<span style='color:{c}'>{n}</span>"
                for c, n in zip(BUCKET_COLOURS, BUCKET_NAMES)) +
                " · grey = insufficient data", unsafe_allow_html=True)

        with gcol2:
            if est:
                est.sort(key=lambda r: r["win"][0])
                fig, ax = plt.subplots(figsize=(7, 0.55 * len(est) + 1.6))
                for i, r in enumerate(est):
                    ws = dt.date(2001, 1, 1) + dt.timedelta(days=r["win"][0] - 1)
                    we = dt.date(2001, 1, 1) + dt.timedelta(days=r["win"][1] - 1)
                    ax.barh(i, (we - ws).days, left=ws,
                            color=BUCKET_COLOURS[bucket(r)], height=0.6)
                ax.set_yticks(range(len(est)))
                ax.set_yticklabels([r["name"] for r in est], fontsize=8)
                ax.invert_yaxis()
                t = dt.date(2001, today.month, today.day)
                ax.axvline(t, color="k", ls="--", lw=1)
                ax.annotate("today", (t, -0.6), fontsize=7, ha="center")
                ax.set_xlim(dt.date(2001, 9, 20), dt.date(2001, 11, 15))
                ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=(1, 15)))
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
                ax.set_title("Typical best-viewing windows (median of past "
                             "seasons)", fontsize=9)
                fig.tight_layout()
                st.pyplot(fig)
                st.caption("Windows are historical medians per destination — "
                           "not this year's forecast. As 2026 observations "
                           "accumulate, expect them to shift a few days.")
            else:
                st.info("No destinations with enough seasons yet — fetches "
                        "may still be running.")

    # ---------- forecast ----------
    with tab_fc:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt

        fcl, fcr = st.columns([1, 2], gap="large")
        with fcl:
            fc_want = colour_range_slider(st, "fc_want")
        ens = foliage.forecast_ensemble(meta, tuple(fc_want))
        fc_win = foliage.best_window(meta, tuple(fc_want))
        if not ens:
            st.info("Not enough past-season data here to say how the next "
                    "weeks usually unfold.")
        else:
            fdates, trajs, anchor, anchor_cov = ens
            arr = np.array(trajs) * 100
            med, lo, hi = (np.median(arr, 0), arr.min(0), arr.max(0))
            typical_peak = (fc_win[3] * 100) if fc_win else 55.0

            def milestone(th):
                ds = sorted(fdates[int(np.argmax(t >= th))]
                            for t in arr if (t >= th).any())
                return ds

            with fcl:
                for emoji, label, th in [
                        ("🍂", "Colour arriving", 0.4 * typical_peak),
                        ("🏔️", "Near its best", 0.8 * typical_peak)]:
                    ds = milestone(th)
                    if len(ds) >= max(1, len(arr) // 2 + len(arr) % 2):
                        mid = ds[len(ds) // 2]
                        spread = (f"anywhere {ds[0]:%b %d} – {ds[-1]:%b %d}, "
                                  "year to year" if ds[0] != ds[-1]
                                  else "consistent across years")
                        st.metric(f"{emoji} {label}", f"around {mid:%b %d}",
                                  delta=spread, delta_color="off")
                    else:
                        st.metric(f"{emoji} {label}",
                                  "more than 3 weeks away",
                                  delta="in most past years", delta_color="off")
            with fcr:
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.fill_between(fdates, lo, hi, alpha=0.25, color="#ff8c00",
                                label="how the last falls played out")
                ax.plot(fdates, med, color="#cc4400", lw=2.5,
                        label="typical year")
                ax.plot([fdates[0]], [anchor_cov * 100], "ko", ms=7,
                        label="where things stand now")
                ax.set_ylim(0, 100)
                ax.set_ylabel("how colourful (% of leaves in your colours)")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
                ax.legend(fontsize=8, loc="upper left")
                fig.tight_layout()
                st.pyplot(fig)
            st.caption(f"An estimate, not a promise: this replays how the "
                       f"last {len(arr)} falls unfolded at this exact spot, "
                       f"starting from the latest satellite photo ({anchor}). "
                       "Weather can shift timing by about a week either way.")
            ground_strip(st, bbox, dist=meta["distributions"][anchor])

    # ---------- seasons compared ----------
    with tab_season:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        years = meta["years"]
        fig, axes = plt.subplots(len(years), 1, figsize=(10, 2.2 * len(years)),
                                 sharex=True, squeeze=False)
        for ax, year in zip(axes[:, 0], years):
            ydates = [d for d in dates if d.startswith(str(year))]
            if not ydates:
                continue
            vals = [[meta["distributions"][d][c] * 100 for d in ydates]
                    for c in foliage.CLASSES]
            # align all years on one calendar axis (month/day in a reference year)
            xs = [dt.date(2001, int(d[5:7]), int(d[8:10])) for d in ydates]
            start, end = dt.date(2001, 9, 1), dt.date(2001, 11, 15)
            # faded season-edge assumptions: steady before the first observation,
            # everything brown/bare by Nov 15 after the last one
            if xs[0] > start:
                ax.stackplot([start, xs[0]], [[v[0], v[0]] for v in vals],
                             colors=foliage.PALETTE, alpha=0.3)
            if xs[-1] < end:
                fallen = [0, 0, 0, 0, 0, 100]
                ax.stackplot([xs[-1], end],
                             [[v[-1], f] for v, f in zip(vals, fallen)],
                             colors=foliage.PALETTE, alpha=0.3)
            ax.stackplot(xs, vals, colors=foliage.PALETTE, alpha=0.9)
            ax.plot(xs, [2] * len(xs), "k|", markersize=8)  # observation ticks
            ax.set_ylabel(str(year))
            ax.set_xlim(start, end)
            ax.set_ylim(0, 100)
            ax.xaxis.set_major_locator(mdates.DayLocator(bymonthday=(1, 15)))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        fig.suptitle(f"Foliage colour progression by season — {meta['place']}",
                     y=0.995)
        fig.tight_layout()
        st.pyplot(fig)
        st.caption("Solid = between real observations (black ticks). Faded = "
                   "assumption, not data: steady before the first observation, "
                   "leaves fallen by Nov 15 after the last one. Sparse years = "
                   "cloudy falls. This is the climatology the forecast leans on.")

    # ---------- ground evidence ----------
    with tab_ground:
        import matplotlib.pyplot as plt

        st.caption("Independent, cloud-proof evidence of colour change near "
                   "Milton — used to validate and (later) calibrate the "
                   "satellite estimates.")
        gcol, pcol = st.columns(2, gap="large")

        with gcol:
            lat0, lon0 = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
            try:
                site, km, roi = ground.nearest_phenocam(lat0, lon0)
            except Exception:
                site, km, roi = ground.PHENOCAM_SITE, None, "DB_1000"
            st.subheader(f"Nearest forest camera — `{site}`" +
                         (f" ({km} km away)" if km is not None else ""))
            st.caption("Closest PhenoCam-network camera with a deciduous-"
                       "forest view — a proxy for regional colour timing, "
                       "not an in-park measurement.")
            try:
                gcc = ground.phenocam_gcc(site, roi)
                fall = gcc[(gcc["date"] >= gcc["date"].max() -
                            pd.Timedelta(days=90))]
                fig, ax = plt.subplots(figsize=(7, 3.2))
                ax.plot(fall["date"], fall["gcc"], color="#2d7d2d",
                        label="greenness (GCC)")
                ax.plot(fall["date"], fall["rcc"], color="#cc2200",
                        label="redness (RCC)")
                ax.set_ylabel("chromatic coordinate (camera)")
                # this park's own satellite observations — varies per park
                ydates_cur = [d for d in dates if d.startswith(str(today.year))]
                handles, labels = ax.get_legend_handles_labels()
                if ydates_cur:
                    ax2 = ax.twinx()
                    xs = [pd.Timestamp(d) for d in ydates_cur]
                    ys = [(1 - meta["distributions"][d]["green"]) * 100
                          for d in ydates_cur]
                    sat, = ax2.plot(xs, ys, "o--", color="#7a4dbf", ms=7,
                                    label="this park: satellite non-green %")
                    ax2.set_ylabel("% non-green (satellite, this park)")
                    ax2.set_ylim(0, 100)
                    handles.append(sat)
                    labels.append(sat.get_label())
                ax.legend(handles, labels, fontsize=8, loc="upper left")
                fig.autofmt_xdate()
                fig.tight_layout()
                st.pyplot(fig)
                st.caption("The camera curve is regional (it is the only "
                           "deciduous-forest camera within 150 km, shared by "
                           "all these destinations); the purple points are "
                           "this park's own satellite observations.")
                last = fall.dropna().iloc[-1]
                trend = ("🍁 redness has overtaken greenness — colour change "
                         "underway" if last["rcc"] > last["gcc"] else
                         "🌳 canopy still predominantly green")
                st.markdown(f"**Latest ({last['date'].date()}):** {trend}")
                st.caption(f"Data: PhenoCam Network (phenocam.nau.edu), site "
                           f"`{site}`, CC-BY 4.0. Daily values; updates ~1 "
                           "day behind the camera.")
            except Exception as e:
                st.error(f"PhenoCam fetch failed: {e}")

        with pcol:
            st.subheader("Human observer reports, nearest first")
            try:
                reps = ground.ontario_parks_reports()
                lat0, lon0 = (bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2
                near = ground.parks_by_distance(reps, lat0, lon0)
                for r in near[:4]:
                    with st.container(border=True):
                        c1, c2 = st.columns([2, 1])
                        c1.markdown(f"**{r['park']}** · {r['distance_km']} km "
                                    f"away\n\n{r['dominant_colour']} · "
                                    f"reported {r['report_date']}")
                        c2.metric("changed", f"{r['colour_change_pct']:.0f}%",
                                  delta=f"{r['leaf_fall_pct']:.0f}% fallen",
                                  delta_color="off")
                with st.expander(f"All {len(reps)} Ontario Parks reports"):
                    all_df = pd.DataFrame(reps)[
                        ["park", "report_date", "dominant_colour",
                         "colour_change_pct", "leaf_fall_pct"]]
                    st.dataframe(all_df, hide_index=True, width="stretch")
                st.caption("Source: ontarioparks.ca/fallcolour, © King's "
                           "Printer for Ontario (non-commercial, attributed). "
                           "Kelso itself is Conservation Halton land — no "
                           "official reports; nearest is Bronte Creek.")
            except Exception as e:
                st.error(f"Ontario Parks fetch failed: {e}")



if __name__ == "__main__":
    from streamlit import runtime
    if runtime.exists():
        main()
    else:
        bootstrap()
