# Data Sources: Licences, Access Terms, and Our Obligations

**Verified 2026-09-29.** The *code* in this repository is MIT-licensed. The *data* it
fetches at runtime is governed by each provider's terms below. No fetched data is
committed to the repository (`output/` is gitignored) — every user fetches from the
sources directly, under these terms.

## Sentinel-2 imagery (via Element84 Earth Search / AWS Open Data)

- **Licence:** Copernicus Sentinel Data Legal Notice — free, full and open access;
  commercial use permitted.
- **Obligation:** attribution. We display *"Contains modified Copernicus Sentinel
  data (2022–2026)"* in the app.
- **Access path:** public STAC API + public S3 bucket (`sentinel-cogs`), the
  provider's intended programmatic route. No key, no quota.

## PhenoCam Network (site `turkeypointurban`)

- **Licence:** CC BY 4.0. Their Fair Use Data Policy (updated 2026-03-03,
  phenocam.nau.edu/webcam/fairuse_statement/) states data are "publicly available,
  without restriction" and explicitly *encourages* downloads.
- **Obligations:** attribute the PhenoCam Network; for any publication, include
  their acknowledgment text plus the site-specific acknowledgment from the site's
  metadata file.
- **robots.txt note:** `/data/` is disallowed to generic crawlers — that is crawl
  control for search engines, superseded for data users by the fair-use policy
  above. We are not crawling: we fetch **one known CSV, at most once per day**,
  with an identifying User-Agent. Bulk work (e.g. multi-site image harvesting)
  should use their published dataset releases instead of the live archive.

## Ontario Parks fall colour report (ontarioparks.ca/fallcolour)

- **Licence:** Crown copyright, © King's Printer for Ontario. **Non-commercial**
  reproduction permitted with attribution; commercial reuse requires a King's
  Printer licence.
- **Obligations:** we display the attribution in-app. The accumulated report
  history (`prototype/output/ground/onparks_history.csv`) is kept in the repo
  as **non-commercial reproduction with attribution**, which the King's
  Printer terms permit — it exists for scientific validation. **A commercial
  deployment must drop this source/data or obtain a licence.**
- **Access:** robots.txt allows everything except `/admin` (crawl-delay 1 s). We
  fetch one page at most twice a day with an identifying User-Agent — compliant.

## OSM Nominatim geocoding (postal code / place lookup)

- **Terms:** free public API; max 1 request/second, identifying User-Agent
  required (we send one), attribution required ("Search by OpenStreetMap
  Nominatim" shown in-app). Results are ODbL.
- Usage is on-demand (one lookup per user search) — well within policy. A
  high-traffic deployment should self-host Nominatim or use a commercial
  geocoder.

## OpenStreetMap basemap tiles

- **Licence:** map data ODbL; tile service subject to the OSMF Tile Usage Policy.
- **Obligations:** attribution (rendered automatically on every map). Light
  prototype use is fine; a public production deployment must switch to a
  commercial tile provider or self-hosted tiles.

## Summary of red lines

1. Never commit fetched data to git — licences differ from the repo's MIT.
2. Keep attributions visible in the UI and in any publication.
3. Going commercial requires: dropping/licensing Ontario Parks data, switching
   map tile provider, and reviewing Open-Meteo if added later (its free tier is
   non-commercial too). Sentinel-2, HLS/VIIRS (NASA), ECCC GeoMet, and PhenoCam
   remain fine commercially with attribution.
