# Policy threshold and magic-constant inventory

**Status:** audit snapshot, current as of 2026-09-08 (MAINT-02, box 1 and box 3).
**Scope:** every numeric threshold/constant found via a repo-wide grep across the
six domains MAINT-02 names — model selection/fitting, S-profile repair (the
constraint audit that runs on Watson/DJF/DJ fits), QC, peak detection,
memory/concurrency, and UI timing. This document is the inventory and
algorithmic/user-adjustable classification (boxes 1 and 3). It intentionally
does **not** move any of these values into a new configuration system, wire
them into session/result provenance, or add boundary tests — see
"What this document does not do" at the bottom, and the corresponding
checklist entry (`MAINT-02` in `docs/audits/master_checklist.md`) for why.

Grounding: values below were read directly from the cited `js/` source files
on 2026-09-08, not inferred. Where a constant's rationale is documented in a
code comment, that comment is quoted or paraphrased; where none exists, this
document says so explicitly rather than inventing one.

## How to read the "Class" column

- **Algorithmic** — a numeric-method or statistical constant (epsilon,
  quadrature node count, a fixed default for reproducibility). Changing it
  changes what the model/algorithm computes, not a user preference. No UI
  exposes it.
- **Policy** — a scientifically-motivated pass/fail or warn/reject line (a QC
  cutoff, an event-count floor). Chosen by domain judgment rather than derived
  from pure numerics, but still not currently user-editable through any UI.
- **User-adjustable (wired)** — genuinely exposed in the UI today, with a
  validated range, and persisted in session provenance. Confirmed by finding a
  live importer outside the defining module (a settings dialog, a session
  writer) via `grep -rl`.
- **User-adjustable (named, unwired)** — named `DEFAULT_*` as if a future
  settings surface will read/override it, but grep found no importer outside
  its own defining module — i.e. nothing in the UI or session layer currently
  lets a user change it despite the naming convention. Called out explicitly
  because this is the one non-obvious finding of this audit: the `DEFAULT_`
  prefix does not currently mean "user-overridable" anywhere except Time QC.

## Model selection / fitting

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `TRANSFORM_EPSILON` | `1e-12` | `js/analysis/cell_cycle/fit_engine.js:12` | none | Algorithmic |
| `EPS` (per-model) | `1e-12` | `models/{shared,dean_jett_fox,cloccs,watson_pragmatic}.js` | none (numeric-stability floor, inferred from name/usage, not stated) | Algorithmic |
| `DEFAULT_S_QUADRATURE_NODES` | `64` | `models/shared.js:22` | none | Algorithmic |
| `PROFILE_WEIGHT_SUM` | `3` | `models/shared.js:52` | none | Algorithmic |
| `PROFILE_SHAPE_LIMIT` | `30` | `models/shared.js:61` | none | Algorithmic |
| `SLOPE_MIN` / `SLOPE_MAX` | `-2` / `2` | `models/watson_classic.js:68-69` | inline: "trapezoid slope in [-2, 2]" | Algorithmic |
| `PARAMETER_COUNT` | `8`/`9` per model | each model file | structural (parameter vector length), not a policy | Algorithmic |
| `POOL_FRACTION` | `0.5` | `fit_client.js:21` | inline: fraction of logical cores for the worker pool, "always leaving at [least one core free]" | Algorithmic (perf tuning) |
| `ASSUMED_CORES` | `4` | `fit_client.js:25` | inline: fallback when `navigator.hardwareConcurrency` is unavailable | Algorithmic |
| `SHARED_REGION_MIN_CONFIDENCE` | `0.65` | `modeling_ui.js:87` | none | Policy |
| `SHARED_CENTER_TOLERANCE` | `0.25` | `modeling_ui.js:163` | inline: "relative deviation from the median allowed" | Policy |
| `SPLIT_MINIMUM_COUNT` | `2` | `modeling_ui.js:170` | none | Policy |
| `SPLIT_MINIMUM_SHARE` | `0.25` | `modeling_ui.js:171` | none | Policy |
| `MIN_EVENTS_PER_BIN` | `20` | `bin_settings_sync.js:65` | none | Policy |
| `COMFORTABLE_EVENTS_PER_BIN` | `50` | `bin_settings_sync.js:66` | none | Policy |
| `COARSE_BIN_COUNT` | `128` | `bin_settings_sync.js:67` | none | Algorithmic |
| `BRIDGE_SIGMA_OFFSET` | `2` | `models/dean_jett_fox.js:426` | none | Algorithmic |
| `MINIMUM_MEAN_STEP_SCALE` | `1e-6` | `models/dean_jett_fox.js:430` | none | Algorithmic |
| `WAVE_NOTICE_FRACTION` | `0.2` | `models/dean_jett_fox.js:436` | none | Policy |

## S-profile repair / constraint audit

(The constraint audit — `constraint_audit.js` — is what runs against a
completed Watson/DJF/DJ fit to find and characterize bound/joint-constraint
violations; this is the closest live module to "S-profile repair" as named in
the checklist. `resampling.js`, which produces the bootstrap-based confidence
intervals reported alongside a fit, is included here too since it's the other
half of what MAINT-02's authors likely meant by this domain.)

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `ACTIVE_BOUND_EPSILON` | `1e-3` | `constraint_audit.js:24` | none | Algorithmic |
| `JOINT_CONSTRAINT_TOLERANCE` | `1e-9` | `constraint_audit.js:29` | none | Algorithmic |
| `DEFAULT_REPLICATES` | `200` | `resampling.js:82` | none directly on the constant, but used by `fit_client.js`/`fit_worker.js` | User-adjustable (wired) — passed through from the fit request, not a UI form field, but genuinely overridable by the caller |
| `MINIMUM_USABLE_REPLICATES` | `40` | `resampling.js:83` | none | Policy |
| `DEFAULT_SEED` | `20260819` | `resampling.js:89` | inline: "not `Date.now()`... two runs of the same analysis... measurement. The seed is published on the bundle so a different one is a [detectable] deviation" | Algorithmic, deliberately fixed for reproducibility |
| `DEFAULT_INTERVAL_LEVEL` | `0.95` | `resampling.js:91` | none | Policy |
| `DEFAULT_REGION_JITTER_FRACTION` | `0.10` | `resampling.js:98` | none | Algorithmic |
| `BIN_COUNT_NEIGHBOURHOOD_FACTOR` | `2` | `resampling.js:105` | none | Algorithmic |
| `SELECTION_STABILITY_THRESHOLD` | `0.8` | `resampling.js:112` | none | Policy |
| `FAILURE_RATE_WARNING` | `0.05` | `resampling.js:118` | none | Policy |
| `FAILURE_RATE_CRITICAL` | `0.20` | `resampling.js:119` | none | Policy |
| `MAX_RECORDED_FAILURES` | `20` | `resampling.js:123` | none (diagnostic cap, not a science threshold) | Algorithmic |

Of these, only `resampling.js`'s bundle (method, seed, replicate counts,
failures — see `resampling.js:400-435`) is actually captured in
result/session provenance today; `constraint_audit.js`'s two constants are
not referenced anywhere outside their own file (confirmed by
`grep -rn "ACTIVE_BOUND_EPSILON\|JOINT_CONSTRAINT_TOLERANCE" js -r`), so a
constraint audit's pass/fail line is not currently traceable to the tolerance
that produced it.

## QC

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `DEFAULT_TIMER_RANGE` | `32.6824` | `acquisition_time_qc.js:20` | none inline (instrument-specific timer wraparound value) | Algorithmic |
| `DEFAULT_TIME_QC_THRESHOLD` | `4` | `acquisition_time_qc.js:21` | none directly, but is the seed for `DEFAULT_ROBUST_SUMMARY_OPTIONS.threshold` | User-adjustable (wired) — via `time_qc_settings.js`'s dialog, validated to `[1, 20]`, persisted in `get_time_qc_session_config()` |
| `MIN_EVALUABLE_TIME_QC_BINS` | `3` | `acquisition_time_qc.js:40` | none | Policy |
| `ROBUST_SCALE_EPSILON` | `1e-12` | `acquisition_time_qc.js:41` | none | Algorithmic |
| `DENSITY_GRID_SIZE` | `256` | `peak_tracking_time_qc.js:49` | none | Algorithmic |
| `KERNEL_RADIUS_SIGMA` | `4` | `peak_tracking_time_qc.js:52` | none | Algorithmic |
| `MINIMUM_DENSITY_VALUES` | `20` | `peak_tracking_time_qc.js:54` | none | Policy |
| `MINIMUM_FINAL_BIN_FRACTION` | `0.5` | `peak_tracking_time_qc.js:57` | none | Policy |
| `PEAK_MERGE_GRID_INTERVALS` | `2` | `peak_tracking_time_qc.js:60` | none | Algorithmic |
| `MINIMUM_RELATIVE_PEAK_SPREAD` | `1e-3` | `peak_tracking_time_qc.js:76` | none | Policy |
| `MINIMUM_RELATIVE_RATE_SPREAD` | `1e-2` | `peak_tracking_time_qc.js:77` | comment nearby references the SCI-12 unbiased-estimator correction staying "below the existing 1% rate-spread floor" | Policy |
| `MISSING_TRACK_WARNING_FRACTION` | `0.1` | `peak_tracking_time_qc.js:93` | none | Policy |
| `MISSING_TRACK_REJECT_RUN` | `3` | `peak_tracking_time_qc.js:94` | none | Policy |
| `MINIMUM_MODELING_EVENTS` | `100` | `result_contract.js:98` | section comment: "QC-00 mandatory model-boundary thresholds... too few eligible events cannot support peak detection or a stable fit" | Policy |
| `MINIMUM_NONEMPTY_BINS` | `5` | `result_contract.js:99` | same section comment | Policy |
| `MINIMUM_PEAK_SUPPORT_EVENTS` | `10` | `result_contract.js:100` | same section comment | Policy |
| `MAX_INELIGIBLE_DNA_FRACTION` | `0.25` | `result_contract.js:101` | same section comment | Policy |
| `QC_CRITICAL_REMOVAL_PERCENT` | `50` | `result_contract.js:109` | section comment: "QC-01 fail-closed policy... Removing more than this fraction... is a critical event loss that must be acknowledged" | Policy |

The Time QC dialog's other user-facing fields (peak-tracking's
`minimumEventsPerBin`, `maximumBins`, `overlapFraction`,
`minimumRelativePeakHeight`, `isolationTreeGainThreshold`, `madMultiplier`,
`minimumGoodRunBins`) are **User-adjustable (wired)**: validated in
`time_qc_settings.js`'s `validate_time_qc_state()` and persisted per-session
via `get_time_qc_session_config()`/`apply_time_qc_session_config()` with an
`algorithm_version` field. This module is the one place in the codebase where
boxes 3 and 4 are already substantially done, and is the template the rest of
this inventory should follow if/when boxes 2, 4, 5 are picked up.

## Gating (scatter/pulse-geometry — feeds into the DNA channel QC upstream of modeling)

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `MAX_SCATTER_POINTS` | `10000` | `scatter_modal.js:18` | none (render/perf cap, not scientific) | Algorithmic |
| `DEFAULT_SCATTER_THRESHOLD` | `5.991` | `scatter_gmm_gate.js:33` | none inline (this is the chi-square 0.95 quantile for 2 d.o.f. by value, but the file doesn't say so) | Policy |
| `MINIMUM_SCATTER_EVENTS` | `10` | `scatter_gmm_gate.js:44` | none | Policy |
| `RELIABLE_SCATTER_EVENTS` | `100` | `scatter_gmm_gate.js:49` | none | Policy |
| `MINIMUM_COMPONENT_EVENTS` | `25` | `scatter_gmm_gate.js:50` | none | Policy |
| `MAXIMUM_COMPONENT_CONDITION` | `1e4` | `scatter_gmm_gate.js:55` | none | Algorithmic |
| `MINIMUM_PLAUSIBLE_COVERAGE` | `0.01` | `scatter_gmm_gate.js:60` | none | Policy |
| `DEFAULT_MINIMUM_POINTS` | `20` | `pulse_geometry_gate.js:32` | none | Policy |
| `RELIABLE_PULSE_GEOMETRY_EVENTS` | `50` | `pulse_geometry_gate.js:33` | none | Policy |
| `MINIMUM_RIDGE_IDENTIFICATION_RATIO` | `4` | `pulse_geometry_gate.js:38` | none | Policy |
| `MINIMUM_PLAUSIBLE_SINGLET_COVERAGE` | `0.05` | `pulse_geometry_gate.js:42` | none | Policy |
| `MINIMUM_RIDGE_OFF_AXIS_EIGENVALUE` | `1e-6` | `pulse_geometry_gate.js:50` | none | Algorithmic |

None of this domain's `export const` values have any importer outside their
own defining module (confirmed by grep), so despite the `DEFAULT_`/policy-like
naming, none are wired to a UI control or session provenance today.

## Peak detection

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `UNRESOLVED_SIGMA_BINS` | `0.5` | `peak_regions.js:36` | none | Algorithmic |
| `PEDESTAL_DISTANCE_SIGMAS` | `3` | `peak_regions.js:206` | none | Algorithmic |
| `PEDESTAL_WINDOW_BINS` | `2` | `peak_regions.js:207` | none | Algorithmic |
| `PEDESTAL_EDGE_WINDOW_BINS` | `2` | `models/watson_pragmatic.js:169` | none | Algorithmic |
| `MAX_REGION_SIGMA` | `4` | `peak_detection.js:601` | none | Policy |
| `MAX_REGION_PEAK_CV` | `0.15` | `peak_detection.js:609` | none | Policy |

## Memory / concurrency

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `POOL_FRACTION`, `ASSUMED_CORES` | `0.5`, `4` | `fit_client.js:21,25` | see Model selection above (same constants, cross-listed since they're literally the worker-pool sizing policy) | Algorithmic |
| `FILE_CONCURRENCY` | `Math.max(1, Math.min(4, navigator.hardwareConcurrency \|\| 2))` | `table_summary_stats.js:29` | none, but self-documenting cap of 4 concurrent file reads | Algorithmic |
| `FILE_DIGEST_CHUNK_BYTES` | `1024 * 1024` (1 MiB) | `session/file_digest.js:2` | none (streaming chunk size for bounded-memory digest computation) | Algorithmic |
| `MAX_SESSION_BYTES` | `2 * 1024 * 1024` (2 MiB) | `session/toml_io.js:248` | none | Policy |

## UI timing

| Constant | Value | File | Rationale in comment? | Class |
|---|---|---|---|---|
| `TABLE_PANEL_TRANSITION_MS` | `220` | `ui/panels.js:31` | none (matches a CSS transition duration) | Algorithmic (cosmetic) |
| `SIDEBAR_MODE_FADE_MS` | `150` | `ui/panels.js:35` | none | Algorithmic (cosmetic) |
| `SIDEBAR_TRANSITION_MS` | (defined in `panels.js`, imported by `table_support.js:18`) | `ui/panels.js` | none | Algorithmic (cosmetic) |
| `DELAY` (hover tooltip) | `80` | `ui/hover_text.js:105` | inline: "ms before showing (skipped when already visible)" | Algorithmic (cosmetic) |
| plot-resize debounce | `100` (default arg) | `plotting/axis_modal.js:303` | none | Algorithmic (cosmetic) |
| revoke-object-URL delay | `1000` | `plotting/plot_export.js:285` | none (gives the download time to start before the blob URL is revoked) | Algorithmic |
| autoload probe delay | `0` | `session/core.js:984` | none (yields a tick, not a real delay) | Algorithmic |

No `debounce()` utility exists anywhere in the codebase (`grep -rn "function debounce"` returns nothing); every UI timing value above is a raw `setTimeout`/default-argument literal local to its own module.

## What this document does not do

This is an inventory and classification only (MAINT-02 boxes 1 and 3). It
deliberately does not attempt boxes 2, 4, or 5, because — as this audit itself
demonstrates — doing so honestly is a materially larger effort than a single
documentation pass:

- **Box 2** (move into named, versioned configuration) would mean relocating
  ~50 constants across 15+ production files into a new `config/` module (or
  modules) and updating every import site, for a codebase whose only existing
  config-directory precedent (`config/artifact-budgets.json`,
  `config/import-cycle-allowlist.json`) is consumed by build/test tooling, not
  runtime analysis code — there is no existing pattern to extend, only one to
  invent, review, and migrate onto without changing any numeric fit/QC
  outcome (a scientific-analysis codebase where an accidental value change
  during a mechanical refactor would silently change results).
- **Box 4** (session/result provenance) is confirmed *partially* done today:
  `time_qc_settings.js`'s `get_time_qc_session_config()` and
  `resampling.js`'s bundle both already capture the values that produced a
  result, with an `algorithm_version` field. But this audit also confirmed by
  grep that `constraint_audit.js`'s two tolerances, `bin_settings_sync.js`'s
  three constants, both gating files' eleven constants, and
  `peak_detection.js`'s two region thresholds have **no** external reference
  anywhere — they are not surfaced in `result_contract.js`'s
  `RESULT_CONTRACT_VERSION` (currently `2`) or any session write path. Closing
  this gap means extending the result contract schema (a version bump) and
  updating every producer/consumer that reads it.
- **Box 5** (boundary tests around every policy threshold) needs new test
  cases for each "Policy" row above (~35 of them) — at, just-below, and
  just-above the boundary — which is real, valuable but substantial test
  authoring, not something to rush alongside a schema change in the same
  pass.

Recommendation if this is picked up as follow-on work: do it in the order
above (config extraction, then provenance/schema, then boundary tests), one
domain at a time (QC first, since it already has the `time_qc_settings.js`
precedent to generalize from), each as its own reviewable change — not as one
sweeping edit across every domain simultaneously.
