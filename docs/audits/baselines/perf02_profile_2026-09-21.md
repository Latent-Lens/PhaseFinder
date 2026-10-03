# PERF-02 end-to-end profile

Runs used the existing `tests/e2e/driving_code/perf_profile.py` unchanged, with
the repository Playwright venv and a local Chromium browser. The first run was
the pre-change baseline; the final run followed the keyed-row/header update in
`js/ui/table_render.js`.

## Acceptance evidence

- Fixtures: 40 files at 6,000 events plus 5 files at 60,000 events; 45 files,
  540,000 total events, five filename-derived metadata columns, 45 overlaid
  series, ridge view, and repeated model-overlay redraws.
- Measurements: initial load/decode-to-rows, incremental load, table sort and
  filter, plot render/redraw, ridge switches, pan/zoom frames, fit, export, and
  JS heap were measured by real Playwright actions.
- Conditional table update: the table sort was the dominant table interaction
  (882.2 ms versus 25.8/33.4 ms filter apply/clear). Keyed rows and in-place
  sort/filter header state landed without breaking the existing table E2E
  checks, but the committed before/after sort measurement was unchanged at
  882.2 ms. This is an honest safety/structure result, not a claimed speedup;
  larger tables or virtualization need a separate measured decision.
- Observed local ceiling: 45 files / 540,000 events / 45 rendered overlays.
  This is a measured operating point, not a product maximum.

## Before and after

| Metric | Before | After |
| --- | ---: | ---: |
| Initial load/decode-to-rows | 59.5 ms | 63.9 ms |
| Remaining-file load/decode-to-rows | 890.5 ms | 889.5 ms |
| Table sort, 45 rows | 882.2 ms | 882.2 ms |
| Filter apply / clear | 25.8 / 33.4 ms | 26.7 / 33.1 ms |
| Initial plot render | 774.6 ms | 774.9 ms |
| Plot redraw ×10 | 85.9 ms | 115.5 ms |
| Pan/zoom mean / max frame interval | 16.7 / 16.8 ms | 16.7 / 16.8 ms |
| Single Dean–Jett fit / LM solve | 1,263.6 / 295.3 ms | 1,283.8 / 298.9 ms |
| Bulk fit, 45 samples | 109.8 ms | 113.3 ms |
| PNG export | 316.0 ms | 310.6 ms |
| JS heap after load / after bulk fit / end | 5.33 / 41.19 / 23.12 MB | 5.84 / 12.26 / 25.81 MB |

The heap values vary with browser garbage collection; they are reported as
observed, not treated as a hard memory limit. The parser's `parse_ms`, plot
counters, and scatter-preview cap remain instrumentation rather than the
ceiling claim.

