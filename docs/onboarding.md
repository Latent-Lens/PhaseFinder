# PhaseFinder — Architectural Onboarding Map

Scope of this map: the current `js/` tree (117 modules across `fcs/`,
`data_structs/`, `io/`, `ui/`, `analysis/{cell_cycle,gating,math,pipeline,qc}/`,
`plotting/`, `session/`, `state/`, `util/`) plus `index.html`'s module entry
point. This revision replaces the pre-reorg (pre-2026-08-17), pre-ES-module
snapshot: the classic-`<script>`, 31-file, `window.*`-global architecture it
described no longer exists. CSS and the rest of `docs/*` were not inspected in
depth and are not relied on for any claim here.

**Product scope:** PhaseFinder targets desktop and laptop windows at least
1080 px wide; narrower windows scroll horizontally. Phone and tablet layouts
are unsupported. Accessibility work is outside the current product scope
beyond existing image alt text and icon-button labels (see [README](../README.md#scope)).

---

## 1. Entry point, build, and module graph

`index.html` loads exactly one first-party script:

```html
<script type="module" src="./js/main.js"></script>
```

`main.js` is a real ES module — it `import`s every layer it needs (no global
script-order contract to maintain) and, at the bottom of the file, runs an
explicit, ordered `init_*()` sequence that is the load-order contract now:

```
init_tooltips();            // ui/hover_text.js tooltip runtime
init_app_bootstrap();       // main.js event wiring + initial render
init_plot_listeners();      // plotting/axis_modal.js listener block
init_plot_toolbar();        // plotting/plot_toolbar.js pan/zoom/export icon strip
init_analysis_listeners();  // analysis/pipeline/start.js listener block
init_pipeline_ui();         // analysis/pipeline/pipeline_ui.js manual pipeline controls
init_peak_review_ui();      // analysis/cell_cycle/peak_review_ui.js Identify Peaks panel
init_modeling_ui();         // analysis/cell_cycle/modeling_ui.js Model & Fit panel
init_bin_settings_sync();   // analysis/cell_cycle/bin_settings_sync.js Bins-change invalidation + hint
init_cell_cycle_columns();  // ui/cell_cycle_columns.js per-model G1/S/G2-M metadata columns
init_stats();               // ui/table_summary_stats.js modal + auto-compute
init_panel_resize();        // ui/panel_resize.js drag handlers
init_remove_columns();      // ui/column_remove.js remove-columns mode
init_session();             // session/core.js wiring + deferred try_autoload
init_unload_guard();        // session/unload_guard.js beforeunload wiring
init_draggable_modals();    // ui/draggable_modal.js drag-to-move for every modal card
init_modal_focus();         // ui/modal_focus.js focus trap, background inertness, focus return
init_compatibility();       // ui/compatibility.js required/optional startup capability report
```

Each `init_*` is imported from the module named in its comment, which
double-owns the ordering: the import statement makes the dependency explicit
and the comment names the effect. Ordering still matters for the same reason
it always did (top-level statements that run immediately need their
dependency already evaluated), but it is now enforced by the module graph
itself — a circular or missing import is a build/runtime error, not a silent
race — instead of by document position in `index.html`.

**Do not hand-maintain a dependency list here.** The exhaustive, per-module
`import`/`export` graph is generated straight from source by
`scripts/check_import_graph.py --update` into
[`docs/module-import-graph.md`](module-import-graph.md), and `npm run
check:imports` fails CI if that file drifts from the live tree (currently
**117 modules, 406 edges, 0 cycles**). Anything below is a human-level summary
for orientation; treat `module-import-graph.md` as the source of truth for
"what imports what."

**Build**: production builds go through Vite (`npm run build`). The source
tree also runs unbuilt (opening `index.html` directly / `npm run dev`) because
every `js/` import is a real relative ES-module specifier — no import map is
needed at dev time, and none ships in the production build (REL-03 strips the
dev-only `<script type="importmap">` that used to shim bare-specifier CDN
imports; see `docs/release-and-privacy.md`). D3 is bundled from
`js/vendor/d3.min.js` rather than loaded from a CDN `<script>` tag.

**Workers**: four Web Workers exist as separate module entry points bundled by
Vite — `js/fcs/data_worker.js` (FCS DATA column reads), `js/session/copy_worker.js`
(background OPFS writes), `js/analysis/cell_cycle/fit_worker.js` (per-sample
model fits), and `js/analysis/cell_cycle/cloccs_worker.js` (joint CLOCCS fits).
Workers cannot `import` the app's `window.*`-free module graph directly across
the worker boundary in the old `importScripts` sense; each worker's own file
imports what it needs as an ES module (Vite handles the worker bundle), and
`js/util/worker_protocol.js` defines the shared request/response message
shape used to talk to all four from the main thread.

**Debug/automation hook**: the one remaining intentional global is
`window.PhaseFinder` (`main.js`, assigned after the `init_*()` calls) —
`{ app, pipeline, plot, session, time_qc, ... }`, documented inline at the
assignment site. `djf` is kept as a compatibility alias for `pipeline` (a
getter). This is the single sanctioned window global; everything else is a
real module export.

---

## 2. Directory map

Descriptions below are drawn from each module's own header comment plus a
spot check of its exports, not an exhaustive re-audit of every function; for
line-level detail, read the file. `module-import-graph.md` has the precise
dependency edges for every entry named here.

### `js/main.js`
Entry module and application bootstrap. Imports every layer, wires top-level
DOM events (file selection, drag/drop, channel changes, table edits, metadata
workflows, sidebar toggle, hard restart), owns the session table bridge
(`get_session_table_state`/`apply_session_state`), and assigns
`window.PhaseFinder`.

### `js/fcs/` — FCS parsing and per-file cleanup
- **`parser.js`** — low-level FCS parser shared by the main thread and the
  data worker: fixed-HEADER reader, TEXT-segment parser, byte-order/data-type
  handling, full-row and header-only parsing, and a selected-column-only
  reader to avoid loading unused channels.
- **`metadata_processing.js`** — builds a loaded-file entry from a file's
  HEADER+TEXT bytes only (DATA is not read at this stage).
- **`channel_cleaning.js`** — normalizes FCS parameter names so area/height/width
  companion channels can be matched across naming conventions, and filters
  loaded columns to finite-positive DNA-area events.
- **`data_worker.js`** — the Web Worker (module entry point) that slices the
  DATA segment and returns selected columns as transferable `Float64Array`s.

### `js/data_structs/` — shared tabular/cache primitives
- **`metadata_frame.js`** — `PhaseFinderFrame`, the column-oriented store, plus
  frame-building/merging helpers and session/import row-matching by filename.
- **`table_state.js`** — cross-render-persistent table state (columns,
  selection, filters, sort) and `sync_file_annotations()`.
- **`metadata_columns.js`** — column-naming/normalization helpers.
- **`metadata_column_schema.js`** — column-schema definitions consumed by the
  above.
- **`channel_cache.js`** — per-row, per-channel loaded-event-array cache.
- **`derived_columns.js`** — shared definitions for the pipeline's derived
  metadata-table columns (which the pipeline UI writes and the table renderer
  groups under).

### `js/io/` — FCS DATA loading and metadata table import/export
- **`parameter_map.js`** — maps a parsed FCS summary into parameter records
  (index/label/name/description) for selected-channel loading.
- **`channel_loading.js`** — creates the shared FCS data worker, falls back to
  main-thread parsing on worker failure, and orchestrates batched/background
  channel-data loads.
- **`metadata_io.js`** — `load_files(files)` (the file-drop/select
  orchestrator: reads headers, rejects duplicates, extends the table frame,
  auto-applies the saved filename-metadata template, dispatches
  `pf-files-loaded`, queues OPFS caching, sorts/re-renders, triggers
  downstream plot refresh), plus delimited-metadata import/export.

### `js/ui/` — DOM/table/tooltip/panel/modal plumbing
- **`dom.js`** — leaf module: captures shared DOM references and layout
  constants once.
- **`hover_text.js`** — tooltip text registry and tooltip runtime.
- **`status_channels.js`** — status/progress-overlay helpers, file-id creation,
  channel-select population.
- **`metadata_wizard.js`** — filename→metadata-column wizard with
  localStorage-persisted template.
- **`table_support.js`** — sidebar collapse, selection-change dispatch,
  filter/sort pipeline, header-control builders.
- **`table_render.js`** — table markup rendering and delegated table event
  handling.
- **`table_summary_stats.js`** — the Calculate Statistics modal and per-file
  metric computation/persistence.
- **`cell_cycle_columns.js`** — writes each plotted sample's active fit
  fractions into read-only metadata-table columns, one group per model.
- **`column_remove.js`** — remove-columns mode (draggable panel,
  click-to-select column headers/cells).
- **`panels.js`** — analysis/modeling button and plot/metadata panel-shell DOM
  refs plus collapse/expand.
- **`panel_resize.js`** — drag-resize for the sidebar and workspace panels.
- **`draggable_modal.js`** — generic drag-to-move for modal dialog cards.
- **`modal_focus.js`** — focus trap, background inertness, and focus
  restoration for modals.
- **`compatibility.js`** — required/optional startup capability report (shown
  via `init_compatibility()`).

### `js/analysis/pipeline/` — the live QC + modeling pipeline orchestration
- **`start.js`** — user-facing orchestration: Plot/Start-Modeling button state,
  channel-change handling, and the top-level listener wiring.
- **`pipeline_ui.js`** — pre-modeling QC gate toggles (Structural, Time, Cell
  Gate, Singlet Gate) applied to every plotted sample.
- **`pipeline_loader.js`** — lazy loader that keeps the numeric cell-cycle
  modules off the initial application graph until first use.
- **`pipeline_state.js`** — per-sample state and mask composition, keyed by
  filename.
- **`cell_cycle_pipeline.js`** — orchestrator whose `apply_*()` entry points
  each run exactly one pipeline stage.
- **`dna_histogram.js`** — builds the masked, linear DNA-content histogram
  every model fits against.
- **`qc_matrix.js`** — the batch QC matrix: one durable per-file/per-stage
  record of what each QC stage did.

### `js/analysis/qc/` — optional QC filters
`structural_qc.js`/`structural_qc_modal.js`/`structural_qc_settings.js`
(structural validity + saturation-ceiling checks), `acquisition_time_qc.js`
(robust-summary Time QC) and `peak_tracking_time_qc.js` (the second Time QC
method) with their shared `time_qc_modal.js`/`time_qc_settings.js` and
`time_qc_diagnostic_plot.js`.

### `js/analysis/gating/` — optional scatter-based gates
`scatter_gmm_gate.js` (FSC/SSC Cell Gate via a 2-component Gaussian mixture),
`pulse_geometry_gate.js` (DNA area-vs-H/W singlet gate via a robust PCA
ridge), `scatter_modal.js` (the interactive Cell Gate ellipse editor).

### `js/analysis/cell_cycle/` — the model-neutral modeling layer
- **`model_registry.js`** — registry for selectable cell-cycle models; each
  entry declares id/fit-scope/capabilities and its fit functions. Currently
  registers `dean_jett`, `dean_jett_fox`, `watson_pragmatic`, `watson_classic`,
  and `cloccs` — see the note on the retired `auto_dj_djf` "Automatic" entry
  in §3.
- **`models/`** — one file per generative model (`dean_jett.js`,
  `dean_jett_fox.js`, `watson_classic.js`, `watson_pragmatic.js`,
  `cloccs.js`, `cloccs_synthetic.js`) plus `shared.js` for common G1/G2
  component builders.
- **`modeling_state.js`** — peak-region and model-fit state transitions for
  the modeling workflow.
- **`modeling_ui.js`** — the sidebar "Model & Fit" panel.
- **`peak_detection.js`** — multi-scale G1/G2 peak-pair detection and
  automatic region proposal.
- **`peak_regions.js`** — peak-region validation and region-local peak
  estimation.
- **`peak_review_ui.js`** — the sidebar "Identify Peaks" panel.
- **`fit_engine.js`** — model-agnostic Poisson-count histogram fit engine.
- **`fit_client.js`**/**`fit_worker.js`** — main-thread pool client and worker
  body for off-main-thread per-sample fits.
- **`cloccs_client.js`**/**`cloccs_worker.js`** — the joint CLOCCS fit's
  client/worker pair.
- **`result_contract.js`** — the authoritative validity contract every model
  entry point and result consumer shares.
- **`diagnostics.js`** — model-neutral Poisson fit diagnostics.
- **`uncertainty.js`** — identifiability/uncertainty evidence for a converged
  fit (UNC-01).
- **`resampling.js`** — resampling-based uncertainty, a second layer on top of
  `uncertainty.js`.
- **`domain_sensitivity.js`** — treats the analysis domain/bin grid as
  scientific inputs (DOMAIN-01).
- **`constraint_audit.js`** — turns a fitted model's declared bounds/joint
  feasibility into numeric evidence (STAT-01).
- **`qc_review_ui.js`** — the acknowledgement flow for critical QC event loss
  (QC-01).
- **`export.js`** — versioned, machine-readable fit export (FEAT-02).
- **`bin_settings_sync.js`** — keeps modeling in sync with the plot's Bins
  slider.

### `js/analysis/math/` — dependency-free numeric primitives
`stats.js`, `gaussian.js`, `gaussian_bin_mass.js`, `poisson.js`,
`quadrature.js`, `integrate.js`, `linalg2d.js`, `lm_solver.js`,
`nelder_mead.js` — shared building blocks consumed across `cell_cycle/` and
`gating/`.

### `js/plotting/` — D3 rendering pipeline
- **`data.js`** — shared plot state, DOM refs, layout constants, histogram
  helpers; the data-preparation layer between loaded channel arrays and the
  renderer.
- **`render.js`** — the main D3 render pass: gathers checked/loaded rows,
  reads pipeline masks/fits, builds histograms, draws curves/legend/axes.
- **`histogram_prep.js`** — per-sample data prep shared by `render.js` and
  `ridge_review.js`.
- **`modeling.js`** — plot title and cell-cycle fit-summary presentation.
- **`ridge_review.js`** — stacked per-sample small-multiples view plus the
  single-sample manual-review blow-up.
- **`axis_modal.js`** — the manual X/Y range modal and plot-control listener
  wiring; exposes `window.PhaseFinderPlot`... — see the correction below.
- **`plot_viewport.js`** — interactive pan/zoom (display-only).
- **`plot_toolbar.js`** — the floating pan/zoom/export icon strip.
- **`peak_region_overlay.js`** — draggable G1/G2 peak-region handles for the
  sample the Identify Peaks panel is reviewing.
- **`peak_focus_range.js`** — computes a display x-range framing the
  G1/S/G2-M region.
- **`curve_tooltip.js`** — hover tooltip for sample curves (replaces the old
  fixed per-sample legend).
- **`plot_export.js`** — "Download plot image" (SVG/PDF vector or
  PNG/JPEG raster).
- **`svg_to_pdf.js`** — dependency-free SVG→single-page vector PDF converter
  written specifically for `render.js`'s output shape.

**Correction to a stale claim in the prior revision of this document:**
`window.PhaseFinderPlot` no longer exists; plot inspection is exposed through
`window.PhaseFinder.plot` (see §1's debug hook).

### `js/session/` — OPFS-backed session persistence
- **`core.js`** — top-level session orchestration: restore, collect/apply,
  TOML file IO, Save/Load/Reset button handlers, reconnect-modal wiring,
  deferred `try_autoload`.
- **`opfs_fs.js`** — low-level OPFS filesystem wrapper (feature detection,
  directory creation, read/delete).
- **`file_cache.js`** — the session file registry, app-private OPFS paths, and
  background caching.
- **`file_digest.js`** — bounded-memory SHA-256 content identity for cached
  files.
- **`copy_worker.js`** — the background-OPFS-write worker.
- **`reconnect.js`** — OPFS restore, manual reconnect matching, reconnect
  modal behavior.
- **`table_session.js`** — session↔metadata-table bridge.
- **`modeling_session.js`** — collects/restores per-sample modeling
  configuration (recompute-on-reload design: only inputs are persisted).
- **`toml_io.js`** — the session TOML serializer/parser.
- **`session_schema.js`** — session document shape/validation.
- **`session_transaction.js`** — transactional session write helpers.
- **`cache_manager.js`** — the cache-manager modal's backing logic (browsing
  and releasing cached OPFS copies).
- **`unload_guard.js`** — the shared `beforeunload` "unsaved data" guard.

### `js/state/` — the two base per-file representations
- **`app_state.js`** — owns `file_map` (heavy, non-tabular per-file objects)
  and `file_table_frame` (the tabular view), each behind accessors; imports
  nothing, so it sits at the base of the dependency graph.
- **`files.js`** — selection queries (`get_file_by_id`, `get_parsed_files`,
  `get_selected_files`) over that shared state.

### `js/util/` — leaf helpers
`clone.js`, `html.js`, `names.js`, `worker_protocol.js` (shared
request/response message shape for all four workers), `build_info.js` (Vite
replaces its constants at build time; source-tree serving uses explicit
development markers instead).

---

## 3. What changed since the last revision of this document

The previous revision of this file (pre-2026-08-17) described a 31-file,
classic-`<script>`, `window.*`-global architecture. None of that remains
accurate:

- **Module system**: every app file is now a real ES module with `import`/
  `export`; there is no shared classic-script scope, and no manually-ordered
  `<script src>` list to reason about.
- **`js/analysis/djf.js`**, **`js/session/store.js`**, **`js/io/cache.js`**
  no longer exist. `djf.js`'s numeric core and orchestration were superseded
  by the model-neutral `js/analysis/cell_cycle/` + `js/analysis/pipeline/`
  layers listed in §2 (the unreachable 21-file `js/analysis/djf/` staged
  duplicate — a different, later dead-code directory with similarly-named
  files — was deleted separately in `5ac4956`; see CLEAN-01/LEGACY-01 in
  `docs/audits/master_checklist.md`). `session/store.js`'s low-level OPFS
  wrapper is now `session/opfs_fs.js`; `io/cache.js`'s parameter-map helpers
  are now `io/parameter_map.js`.
- **No "Automatic" model**: `model_registry.js` registers five models
  (`dean_jett`, `dean_jett_fox`, `watson_pragmatic`, `watson_classic`,
  `cloccs`); there is no `auto_dj_djf`/"Automatic" entry. One existed and was
  deliberately removed — it chose between DJ and DJF by an information
  criterion that turned out to be unidentifiable while peaks are frozen (see
  `docs/plans/phasefinder_design.md`'s "There is no 'Automatic' model" note
  and MODEL-07 in the master checklist for the retained rationale and the
  tracked return work). `docs/plans/cell_cycle_modeling_plan.md` §1.1 still
  describes `auto_dj_djf` as part of the planned dropdown — that document is
  an implementation *plan*, not a live-state description; treat its model
  table as historical/aspirational and the registry above as current.
- **Real exports replace `window.*` globals**: the only intentional global is
  `window.PhaseFinder` (§1). The old table (`window.PhaseFinderApp`,
  `window.PhaseFinderDJF`, `window.PhaseFinderPlot`, `window.PhaseFinderOPFS`,
  `window.PhaseFinderSessionFiles`, `window.PhaseFinderReconnect`,
  `window.PhaseFinderSummaryStats`, `window.PhaseFinderHoverText`/
  `window.PhaseFinderTooltips`) no longer exists as such — the same
  functionality is reached through ordinary module imports, or through
  `window.PhaseFinder`'s sub-objects for the parts still exposed for
  automation/tests.
- **D3 and the fit libraries are bundled, not CDN-loaded**: `js/vendor/d3.min.js`
  is imported directly; there is no blocking `<head>` CDN script and no
  dynamic-import shim for a Levenberg-Marquardt/peak-detection library — the
  cell-cycle fit math now lives in `js/analysis/math/lm_solver.js` and
  `js/analysis/cell_cycle/peak_detection.js`.
- **Module count**: 31 → 117 (406 import edges), reflecting the QC/gating/
  pipeline/cell-cycle reorganization landed across the 2026-08 refactors.

---

## 4. Event flow traces (high-level; verify line numbers against source before citing them)

### A. FCS file drop/select → parsing → table population
1. `#drop_zone`/`#collapsed_upload_target` drop or `#file_input` change →
   `load_files(files)` in `js/io/metadata_io.js`.
2. For each file: `read_fcs_header(file)` (`js/fcs/metadata_processing.js`,
   via `js/fcs/parser.js`) reads HEADER+TEXT only; the entry is stored in
   `file_map` (`js/state/app_state.js`) and linked to an existing unlinked
   metadata row by filename if one matches.
3. After the loop: the table frame is extended (`data_structs/metadata_frame.js`),
   the saved filename-metadata template auto-applies if compatible, otherwise
   `sync_file_annotations()` runs; `pf-files-loaded` is dispatched and
   `register_loaded_files()` (`js/session/file_cache.js`) queues background
   OPFS caching.
4. The table sorts/re-renders (`js/ui/table_render.js`,
   `js/ui/status_channels.js`'s channel-control population), and if a plot
   already exists, downstream refresh loads event data for newly-added
   selected rows and redraws.

### B. "Cell Cycle Modeling" click → fit → render
1. Precondition: a channel plot exists (`js/analysis/pipeline/start.js`'s
   `start_analysis()` loads DNA-area/H/W channel data via
   `js/io/channel_loading.js`, which uses the `js/fcs/data_worker.js` Worker
   or a main-thread fallback).
2. The QC gate toggles (`js/analysis/pipeline/pipeline_ui.js`) and peak-review
   panel (`js/analysis/cell_cycle/peak_review_ui.js`) prepare the masked
   histogram (`js/analysis/pipeline/dna_histogram.js`) and peak regions.
3. Selecting and fitting a model (`js/analysis/cell_cycle/modeling_ui.js`)
   runs the registered model's fit through `fit_client.js`/`fit_worker.js`
   (or `cloccs_client.js`/`cloccs_worker.js` for the joint CLOCCS path) off
   the main thread.
4. `js/plotting/render.js` draws the histogram, fitted components, and
   overlays; `js/plotting/modeling.js` renders the fit-summary presentation.

### C. Session save / load (brief trace)
- **Save**: `js/session/core.js` collects state (table via
  `session/table_session.js`, modeling config via
  `session/modeling_session.js`) and serializes it with
  `session/toml_io.js`, then writes it via the File System Access API (or a
  download fallback).
- **Load**: `session/toml_io.js` parses the TOML, `session/core.js` applies
  table/UI/plot state, and `session/reconnect.js` recovers cached FCS files
  from OPFS (`session/file_cache.js`) or opens the reconnect modal for
  anything still missing — recovered files re-enter through the same
  `load_files()` path as flow A.

---

## 5. Data flow — core data structures

Two parallel per-file representations still exist and must stay in sync, now
owned by `js/state/app_state.js` behind accessors rather than as bare globals:

1. **`file_map`** — `Map<id, entry>` of non-tabular "heavy" per-file objects:
   `File`, FCS `summary`, `annotations`, the active-channel `data` payload,
   and the `channel_cache.js`-backed `analysis_data_by_channel` cache.
2. **`file_table_frame`** — a `PhaseFinderFrame` (`data_structs/metadata_frame.js`):
   the tabular, "light" view — `id`, `name`, user/filename/import metadata
   columns, plus computed `"CHANNEL:metric"` stat columns. Single source of
   truth for annotation edits, filters, sort, and export;
   `data_structs/table_state.js`'s `sync_file_annotations()` is still the
   one-way bridge that copies frame values back onto `file_map` entries'
   `.annotations`.

Layer responsibilities are unchanged in spirit from the pre-reorg tree:
`fcs/` produces raw parsed data and knows nothing of `file_map`/the frame;
`io/` is the bridge that populates both; `analysis/` consumes `file_map`
entries' `.data` and never touches the frame directly; `plotting/` reads both
only through `js/state/files.js` accessors; `ui/` reads/writes the frame
directly for rendering; `session/` serializes a third, independent TOML shape
built from both and, on load, reconstitutes them independently of re-parsing
FCS bytes (cached OPFS copies feed back through the same `load_files()` path
as a fresh drop).

---

## Files referenced for this revision

Grounded in a full `find js -name "*.js"` listing (117 files), each file's
header comment, `index.html`, `js/main.js` in full, and targeted export/grep
checks of `js/io/metadata_io.js`, `js/state/app_state.js`,
`js/state/files.js`, and `js/analysis/cell_cycle/model_registry.js`. This is
an orientation map, not a line-by-line audit of all 117 modules — for exact
dependency edges see `docs/module-import-graph.md` (auto-generated, CI-checked);
for exact line numbers, read the cited file.

**Not inspected**: `css/*.css`, the rest of `docs/*`, `tests/*`, `README.md`.
No claim above relies on those files.
