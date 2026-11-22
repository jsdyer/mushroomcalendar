# Mushroom Calendar

A static field notebook of public iNaturalist fungi observations around Langley, British Columbia and Halifax, Nova Scotia. Compare the seasonal rhythm of three complete years, inspect identification quality and licences, and follow individual records back to their contributors.

<!-- coolcode:guide -->
Start with research-grade observations, compare the monthly share on each coast, then select a month or taxon to inspect its records. The 2023–2025 calendar describes observation activity, not abundance, edibility or a forecast; obscured records have month-only dates and never appear on the map.
<!-- /coolcode:guide -->

## Coverage and interpretation

The public `/v1/observations` endpoint is queried for kingdom Fungi (`taxon_id=47170`), observation dates **2023-01-01 through 2025-12-31**, and observation licences **CC0, CC BY or CC BY-NC**. All quality grades are collected. The default UI selects research grade and excludes captive/cultivated records. Unlicensed and other-licensed observations are outside coverage. Fungi includes lichens and other fungi, not only mushrooms.

| Area | South | West | North | East |
|---|---:|---:|---:|---:|
| Langley, BC | 49.02 | −122.80 | 49.20 | −122.52 |
| Halifax, NS | 44.56 | −63.70 | 44.74 | −63.45 |

These are fixed regional rectangles including neighbouring communities, not administrative boundaries. Bounding-box searches use publicly available coordinates; obscured locations may be assigned to a neighbouring area. Private and locationless records cannot be represented by this geographic query. Each snapshot includes exact request URLs, initial source totals, returned/included counts, skipped invalid counts, page receipts and SHA-256 response hashes. Full-query completeness concerns those filters only. The API does not provide a transactional snapshot, so edits during collection can affect counts; mismatches fail validation checks before deployment.

Monthly charts use the recorded month, weekly charts ISO week 1–53; the year filter uses calendar year, so week 1/53 may span year boundaries. Month selection leaves the seasonal overview intact while filtering summary, map and records. Each region's share uses its own selected-record total, so equal percentages do not mean equal numbers of observations. Search, year, quality, licence, accuracy and taxon filters affect both comparison series. Map-cell selection filters the detailed records but leaves the geographic and seasonal context visible.

Counts reflect observer effort, accessible trails, weather, identification interest and repeat observations as well as fungi. They are not estimates of abundance, a randomized survey or evidence of absence. Taxa may be identified above species level. Research grade is a community assessment that can change; it is not a food-safety guarantee. This app is not an identification or edibility guide.

## Source and reuse

- [iNaturalist API documentation](https://api.inaturalist.org/v1/docs/)
- [Official API recommended practices](https://www.inaturalist.org/pages/api+recommended+practices)
- [Official data quality explanation](https://help.inaturalist.org/en/support/solutions/articles/151000169936)
- [Official geoprivacy explanation](https://help.inaturalist.org/en/support/solutions/articles/151000169938)

Every record retains the observation ID, contributor login and source licence. The UI links the original observation, where full context and licence terms can be reviewed. Photos are not collected. Individual observation licences govern reuse, including attribution and noncommercial conditions where applicable. The MIT software licence does not relicense source records.

Open coordinates are rounded to a **0.02° geographic grid before persistence**. The grid is roughly 1.5–2 km at these latitudes; source accuracy is retained separately and may be larger. All obscured or private records have coordinates removed and exact observation days reduced to month precision; their weekly fields are removed too. Never add authenticated API access, private coordinates, raw API response archives or more precise geolocation to this collector. Aggregate geographic circles use the grid, not an external map tile service. No browser filters are sent to iNaturalist or retained in browser storage. External source/map links visit the named service; aggregate CoolCode page metrics omit filter values.

## Collection and retained history

`python3 scripts/collect.py` is the explicit online refresh. It uses unauthenticated HTTPS with a named User-Agent, a maximum of 200 results per page, ascending ID cursors, at least 1.1 seconds between requests, bounded response sizes and retries, and at most **50 pages / 10,000 records per region**. An oversized or incomplete query fails rather than silently publishing a truncated seasonal sample. Validation rejects duplicate IDs, unsafe privacy fields and incomplete coverage. New source responses are normalized in memory; exact coordinates and protected days are never saved. Future expansion should use official exports, not unlimited API pagination.

The data window intentionally remains 2023–2025. Weekly rechecks incorporate late uploads, reidentifications and deletions. Changing the window requires an explicit code and documentation update. `captured_at` identifies the newest changed record set; `checked_at` identifies the last successful recheck. When facts change, a content-addressed compressed snapshot is appended under `archive/YYYY-MM/`; the manifest records its integrity hash and added/changed/removed counts. Unchanged checks update freshness without inventing new history. The initial baseline is labelled as such. Old captures remain selectable in the app and downloadable in the repository. These are historical views of API records, not new observations of biological change.

GitHub Actions runs **Sundays at 08:23 UTC**, on manual dispatch, and for source changes. Scheduled/manual main-branch runs collect; pushes and pull requests validate/build saved data offline. Node, Python and CI Chromium checks run before committing a new capture or publishing Pages. Failed collections or checks leave the deployed site unchanged. Optional `HEALTHCHECKS_PING_URL` provides start/success/failure pings if configured. GitHub may suspend schedules after repository inactivity; the app's dates remain visible. No API key is needed.

## Development

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The default builder is offline, validates current and retained data, verifies archive hashes, and publishes only `web/`, `data/` and `archive/` to `dist/`. It preserves the last output when validation fails. `data/index.json` is a small freshness/coverage probe for the CoolCode hub. CI runs `tests/browser_smoke.py` at a project subpath, checking filters, weekly charts, archive loading, CSV, safe text and mobile overflow. No runtime or build dependencies beyond Python standard library and browser JavaScript are required. Playwright is test-only. Never commit `dist/`.

Related: [Museum Drawer](https://coolcode.ca/museumdrawer/) · [Fossil Neighbours](https://coolcode.ca/fossilneighbours/).
