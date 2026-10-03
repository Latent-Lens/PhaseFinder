#!/usr/bin/env python3
"""PERF-02 profiling harness (docs/audits/master_checklist.md, was AUDIT-006/007).

This is a standalone measurement tool, NOT part of the pass/fail E2E suite
(drive_flow.py) -- it drives the real app against representative fixtures
(many files, long/derived metadata, a large-event-count subset, ridge view,
repeated model-select overlay switches) and reports real wall-clock timings
plus JS heap size, so PERF-02's "profile before optimizing" acceptance boxes
are backed by actual measurements instead of guesses. It never fabricates or
assumes a number -- every metric below comes from a real Playwright action
against a real page load, with the exact interaction it timed noted in
`detail` for reproducibility.

Run with the project's Playwright-enabled venv, from the repo root:

  .venv/bin/python tests/e2e/driving_code/perf_profile.py
  .venv/bin/python tests/e2e/driving_code/perf_profile.py --files 60 --large-files 6 --headed

Writes a timestamped JSON + Markdown report under tests/e2e/results/perf_profile/.
"""

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from playwright.sync_api import sync_playwright  # noqa: E402

from helpers import (  # noqa: E402
    close_filter,
    configure_default_metadata_wizard_columns,
    dismiss_metadata_wizard_if_open,
    enter_modeling_mode,
    ensure_channel_option,
    exit_modeling_mode,
    isolate_first_plotted_sample,
    open_filter,
    restore_row_selection,
    select_all_visible_rows,
    select_channel,
    set_filter_option,
    set_files_via_file_browser,
    table_row_count,
    wait_for_render,
    wait_for_rows,
    write_synthetic_fcs,
)
from test_server import start_test_server  # noqa: E402

# _ensure_qc_applied/confirm_time_qc_method drive the same Pre-modeling QC
# gates (structural/time/cellgate/singlet) the real modeling tests exercise --
# reused rather than reimplemented so this harness follows the same
# already-validated path to an enabled Fit button.
from tests_modeling import _ensure_qc_applied, _set_region_input  # noqa: E402

_TESTS_ROOT = _HERE.parents[1]
REPO_ROOT = _TESTS_ROOT.parent
RESULTS_DIR = _TESTS_ROOT / "e2e" / "results" / "perf_profile"

STRAINS = ["501", "502", "503"]
REPLICATES = ["a", "b", "c"]
ARRESTS = ["Y", "N"]
TIMEPOINTS = [0, 2, 4, 6, 8, 10]


def _combo(index):
    combos = [(s, r, a, t) for s in STRAINS for r in REPLICATES for a in ARRESTS for t in TIMEPOINTS]
    return combos[index % len(combos)]


def build_fixtures(data_dir, many_count, large_count, large_events):
    """Representative fixtures for PERF-02 box 1: many files spanning a real
    strain/replicate/arrest/timepoint metadata matrix (drives the "long
    metadata" columns via the filename-metadata wizard, the app's only path
    to populating those columns -- see configure_default_metadata_wizard_columns),
    plus a subset at a much larger per-file event count."""
    data_dir.mkdir(parents=True, exist_ok=True)
    seed = 1
    many_files = []
    for i in range(many_count):
        strain, replicate, arrest, tp = _combo(i)
        many_files.append(write_synthetic_fcs(data_dir, seed, strain, tp, events=6000,
                                               replicate=replicate, nocodazole_arrest=arrest))
        seed += 1
    large_files = []
    for i in range(large_count):
        strain, replicate, arrest, tp = _combo(i * 7 + 1)
        large_files.append(write_synthetic_fcs(data_dir, seed, strain, tp, events=large_events,
                                                 replicate=replicate, nocodazole_arrest=arrest))
        seed += 1
    return many_files, large_files


def heap_bytes(cdp):
    try:
        metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
        return metrics.get("JSHeapUsedSize")
    except Exception:
        return None


def timed_ms(fn):
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000.0


def _find_two_peak_regions(histogram):
    """Locate a sample's two real density modes from its already-computed
    histogram (edges: binCount+1 boundaries, counts: binCount densities --
    see modeling_state.js), then bracket each by walking outward from its
    peak bin while the count stays above 15% of that peak's height. Used to
    seed dean_jett's G1/G2 regions with this fixture's actual empirical
    structure instead of trusting the multiscale detector's fallback (which,
    for write_synthetic_fcs()'s broad uniform "sea" between populations,
    frequently can't resolve a real candidate pair at all -- see the caller).
    Returns ((g1_left, g1_right), (g2_left, g2_right))."""
    edges = histogram["edges"]
    counts = histogram["counts"]
    n = len(counts)
    ranked = sorted(range(n), key=lambda i: counts[i], reverse=True)
    idx_a = ranked[0]
    min_separation = max(3, n // 8)
    idx_b = next((i for i in ranked[1:] if abs(i - idx_a) >= min_separation), None)
    if idx_b is None:
        # No well-separated second mode -- split the domain in half and take
        # each half's own tallest bin rather than fail outright.
        half = n // 2
        idx_a = max(range(half), key=lambda i: counts[i])
        idx_b = half + max(range(n - half), key=lambda i: counts[half + i])
    left_peak, right_peak = sorted([idx_a, idx_b])
    midpoint = (left_peak + right_peak) // 2

    def bracket(peak_idx, lo_limit, hi_limit):
        threshold = counts[peak_idx] * 0.15
        left = peak_idx
        while left > lo_limit and counts[left - 1] >= threshold:
            left -= 1
        right = peak_idx
        while right < hi_limit and counts[right + 1] >= threshold:
            right += 1
        return edges[left], edges[right + 1]

    g1_region = bracket(left_peak, 0, midpoint)
    g2_region = bracket(right_peak, midpoint + 1, n - 1)
    return g1_region, g2_region


def run(args):
    measurements = []

    def record(metric, ms, detail=""):
        entry = {"metric": metric, "ms": round(ms, 1), "detail": detail}
        measurements.append(entry)
        suffix = f" ({detail})" if detail else ""
        print(f"  {metric}: {ms:.1f} ms{suffix}", flush=True)

    def record_raw(metric, value, detail=""):
        entry = {"metric": metric, "value": value, "detail": detail}
        measurements.append(entry)
        print(f"  {metric}: {value}{' (' + detail + ')' if detail else ''}", flush=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    data_dir = _TESTS_ROOT / "e2e" / "e2e_test_data" / f"perf_profile_{stamp}"
    print(f"Generating fixtures under {data_dir} ...", flush=True)
    many_files, large_files = build_fixtures(data_dir, args.files, args.large_files, args.large_events)
    print(f"  {len(many_files)} standard fixtures (6000 events each, "
          f"{len(STRAINS)} strains x {len(REPLICATES)} replicates x {len(ARRESTS)} arrest states x "
          f"{len(TIMEPOINTS)} timepoints)", flush=True)
    print(f"  {len(large_files)} large fixtures ({args.large_events} events each)", flush=True)

    httpd = None
    url = args.url
    if not url:
        port, httpd = start_test_server(str(REPO_ROOT))
        url = f"http://127.0.0.1:{port}/index.html"
        print(f"Serving app at {url}", flush=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headed)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            # Both the single-fit and bulk-fit paths below can trigger
            # approve_degraded_qc()'s window.confirm() (modeling_ui.js) when a
            # required QC gate is unavailable/degraded for a sample. Register
            # ONE persistent handler for the page's whole lifetime rather than
            # a page.once() per fit action -- a page.once() that never fires
            # (e.g. because that particular fit didn't need the confirm) stays
            # registered, and a second page.once() registered later for the
            # next fit step then collides with it on the next real dialog:
            # Playwright calls every registered listener, so both try to
            # accept the same dialog and the second raises "Dialog.accept:
            # Cannot accept dialog which is already handled!".
            page.on("dialog", lambda dialog: dialog.accept())
            cdp = context.new_cdp_session(page)
            cdp.send("Performance.enable")

            page.goto(url)
            page.wait_for_load_state("domcontentloaded")

            heap_start = heap_bytes(cdp)

            # --- box 2: initial load ---------------------------------------
            first_batch = many_files[: max(1, len(many_files) // 2)]
            rest_batch = many_files[len(first_batch):]

            ms = timed_ms(lambda: set_files_via_file_browser(page, "#drop_zone", first_batch))
            dismiss_metadata_wizard_if_open(page)
            ms += timed_ms(lambda: wait_for_rows(page, len(first_batch)))
            record("initial_load", ms, f"{len(first_batch)} files, click-to-rows-rendered")

            configure_default_metadata_wizard_columns(page)  # box 1: "long metadata" (5 derived columns)

            ms = timed_ms(lambda: set_files_via_file_browser(page, "#drop_zone", rest_batch + large_files))
            ms += timed_ms(lambda: wait_for_rows(page, len(many_files) + len(large_files)))
            record("incremental_load_remaining_files", ms,
                   f"+{len(rest_batch) + len(large_files)} files "
                   f"({len(large_files)} at {args.large_events} events each)")

            heap_after_load = heap_bytes(cdp)

            # --- box 2: table rerender (sort + filter) ----------------------
            ms = timed_ms(lambda: (page.click(".th_sort[data-sort-field='name']"), wait_for_render(page)))
            record("table_sort_by_filename", ms, f"{table_row_count(page)} rows, full table innerHTML rebuild")

            open_filter(page, "Strain")
            ms = timed_ms(lambda: (
                set_filter_option(page, "strain", STRAINS[0], True),
                wait_for_render(page),
            ))
            record("table_filter_apply", ms, f"filter strain={STRAINS[0]}")

            ms = timed_ms(lambda: (
                set_filter_option(page, "strain", STRAINS[0], False),
                wait_for_render(page),
            ))
            record("table_filter_clear", ms, f"{table_row_count(page)} rows restored")
            close_filter(page)

            # --- box 2: initial plot render + repeated redraw ----------------
            channel, _ = ensure_channel_option(page)
            select_all_visible_rows(page)
            ms = timed_ms(lambda: (select_channel(page, channel), page.click("#start_analysis_button"),
                                    page.wait_for_selector("#plot_area svg", timeout=180000), wait_for_render(page)))
            plotted = table_row_count(page)
            record("initial_plot_render", ms, f"{plotted} series overlaid on first plot")

            redraw_profile = page.evaluate("""async () => {
              const { render_density_plot } = await import('./js/plotting/render.js');
              window.PhaseFinder.plot.performance.reset();
              const started = performance.now();
              for (let i = 0; i < 10; i += 1) render_density_plot();
              return { elapsedMs: performance.now() - started, ...window.PhaseFinder.plot.performance.snapshot() };
            }""")
            record("plot_redraw_x10", redraw_profile["elapsedMs"],
                   f"eventScans={redraw_profile['eventScans']}, histogramBuilds={redraw_profile['histogramBuilds']}, "
                   f"cacheHits={redraw_profile['cacheHits']}, cachedSamples={redraw_profile['cachedSamples']} "
                   f"(via window.PhaseFinder.plot.performance, PERF-UI-04 instrumentation)")

            # ridge view + back to overlay: "ridge plots, repeated model overlays"
            ms = timed_ms(lambda: (page.select_option("#plot_view_mode", "ridge"), wait_for_render(page)))
            record("switch_to_ridge_view", ms, f"{plotted} ridge rows")
            ms = timed_ms(lambda: (page.select_option("#plot_view_mode", "overlay"), wait_for_render(page)))
            record("switch_back_to_overlay_view", ms)

            # --- box 2: pan/zoom frame time ----------------------------------
            plot_box = page.eval_on_selector(
                "#plot_area svg",
                "el => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; }",
            )
            cx, cy = plot_box["x"] + plot_box["w"] / 2, plot_box["y"] + plot_box["h"] / 2
            page.mouse.move(cx, cy)
            page.evaluate("""() => {
              window.__pfFrames = [];
              window.__pfFrameLogging = true;
              const tick = (now) => {
                if (!window.__pfFrameLogging) return;
                window.__pfFrames.push(now);
                requestAnimationFrame(tick);
              };
              requestAnimationFrame(tick);
            }""")
            wheel_events = 24
            wheel_start = time.perf_counter()
            for _ in range(wheel_events):
                page.mouse.wheel(0, -120)
                page.wait_for_timeout(30)
            wheel_ms = (time.perf_counter() - wheel_start) * 1000.0
            page.evaluate("() => { window.__pfFrameLogging = false; }")
            frames = page.evaluate("() => window.__pfFrames.slice()")
            deltas = [b - a for a, b in zip(frames, frames[1:])]
            mean_frame_ms = sum(deltas) / len(deltas) if deltas else None
            max_frame_ms = max(deltas) if deltas else None
            record("pan_zoom_wheel_burst_wall_time", wheel_ms, f"{wheel_events} wheel events over #plot_area")
            if mean_frame_ms is not None:
                record("pan_zoom_mean_frame_interval", mean_frame_ms, f"{len(frames)} rAF frames captured during the burst")
                record("pan_zoom_max_frame_interval", max_frame_ms, "worst single frame gap (jank indicator)")
            else:
                record_raw("pan_zoom_frame_interval", "n/a", "no rAF frames observed during the wheel burst")

            # --- box 4 validation: confirm the new solveMilliseconds field --
            # actually reaches a fit result end-to-end for a Poisson-deviance
            # model (dean_jett) that goes through fitPoissonModel()/lm_solver.js.
            exit_modeling_mode(page)
            sample_name, previous_selection = isolate_first_plotted_sample(page)
            enter_modeling_mode(page)
            _ensure_qc_applied(page)
            page.wait_for_function(
                "(name) => Boolean(window.PhaseFinder?.pipeline?.get_state?.(name)?.histogram)",
                arg=sample_name, timeout=30000,
            )
            page.click("#detect_peaks_button")
            page.wait_for_function(
                "(name) => Boolean(window.PhaseFinder.pipeline.get_state(name)?.modeling?.peakSelection?.regions)",
                arg=sample_name, timeout=15000,
            )
            # write_synthetic_fcs()'s GFP/FITC-A channel puts most events in a
            # broad uniform "sea" between the G1 and G2 populations, which the
            # multiscale detector often can't resolve into a real G2 candidate
            # (candidates: [] -- no plausible pair at all) -- it falls back to
            # "inferred_g2" with a region pair that both understates the true
            # G1/G2 separation and sits outside dean_jett's fixed G2:G1 ratio
            # window ([1.75, 2.25], see projectMeansToFeasible() in
            # models/shared.js), so the fit either refuses outright ("No G2:G1
            # ratio ... achievable") or, if only nudged into bare feasibility,
            # fails to converge from such a poor starting box. Rather than
            # guess at "the real" region boundaries, read this sample's own
            # already-computed histogram (edges + counts -- exactly what a
            # detector would use) and locate its two real density modes
            # empirically, then bracket each mode tightly by walking outward
            # from its peak bin until the count drops off. This is a real
            # measurement of this specific fixture's actual data, not a
            # fabricated or hardcoded value.
            histogram = page.evaluate(
                "(name) => window.PhaseFinder.pipeline.get_state(name).histogram", sample_name,
            )
            g1_region, g2_region = _find_two_peak_regions(histogram)
            _set_region_input(page, "#peak_region_g1_left", g1_region[0])
            _set_region_input(page, "#peak_region_g1_right", g1_region[1])
            _set_region_input(page, "#peak_region_g2_left", g2_region[0])
            _set_region_input(page, "#peak_region_g2_right", g2_region[1])
            page.wait_for_function(
                "(name) => window.PhaseFinder.pipeline.get_state(name)?.modeling?.peakSelection?.source === 'manual'",
                arg=sample_name, timeout=5000,
            )
            page.click("#peak_regions_accept_button")
            page.wait_for_function(
                "(name) => Boolean(window.PhaseFinder.pipeline.get_state(name)?.modeling?.peakSelection?.reviewed)",
                arg=sample_name, timeout=15000,
            )
            # Fit Current stays disabled until a model is selected too, not
            # just accepted regions (see tests_modeling.py's model-select-
            # then-check-enabled ordering).
            page.select_option("#cell_cycle_model_select", "dean_jett")
            page.wait_for_function(
                "() => !document.querySelector('#cell_cycle_fit_current_button').disabled", timeout=15000,
            )
            # on_fit_current_click() (modeling_ui.js) calls approve_degraded_qc(),
            # which raises a window.confirm() if any required QC gate isn't
            # cleanly satisfied for this sample (e.g. reviewRequired) -- the
            # page-level handler registered above accepts it. Note that a fit
            # can finish with converged: false (LM ran out of iterations
            # without meeting its tolerance) and still un-hide the result
            # panel: result_contract.js's validForReporting is driven by
            # hasReportableNumber (finite phase fractions etc.), not by
            # optimizerConverged, so a non-converged-but-numeric result is
            # still the active result and still rendered -- it's flagged
            # limitedReliability instead of hidden. That's expected app
            # behavior, not a wiring bug, and doesn't affect whether
            # solveMilliseconds below is a real measurement.
            page.click("#cell_cycle_fit_current_button")
            single_fit_ms = timed_ms(lambda: (
                page.wait_for_function(
                    "() => !document.querySelector('#cell_cycle_fit_result').hidden", timeout=15000,
                ),
            ))
            record("single_sample_fit_dean_jett", single_fit_ms, "1 sample, current-fit path")
            solve_ms = page.evaluate(
                """(name) => {
                  const modeling = window.PhaseFinder.pipeline.get_state(name).modeling;
                  for (const result of Object.values(modeling.resultsByKey || {})) {
                    const solveMs = result?.diagnostics?.optimizer?.solveMilliseconds;
                    if (typeof solveMs === 'number') return solveMs;
                  }
                  return null;
                }""",
                sample_name,
            )
            record_raw("lm_solver_solveMilliseconds_surfaced", solve_ms,
                        "AUDIT-006 instrumentation check: js/analysis/math/lm_solver.js's "
                        "optimizerDiagnostics.solveMilliseconds, round-tripped through dean_jett.js's "
                        "normalizeResult() into modeling.resultsByKey[key].diagnostics.optimizer -- "
                        "None here would mean the wiring is broken")

            restore_row_selection(page, previous_selection)

            # --- box 2: bulk fit ----------------------------------------------
            select_all_visible_rows(page)
            page.wait_for_function("() => (window.PhaseFinder.plot.series || []).length >= 2", timeout=30000)
            page.select_option("#cell_cycle_model_select", "watson_pragmatic")
            # Confirm dialogs (approve_degraded_qc(), if triggered) are
            # accepted by the page-level handler registered right after
            # context.new_page() above.
            bulk_fit_start = time.perf_counter()
            page.click("#cell_cycle_fit_all_button")
            page.wait_for_function(
                "() => /^Auto-fit /.test(document.querySelector('#status_bar_message')?.textContent || '')",
                timeout=300000,
            )
            bulk_fit_ms = (time.perf_counter() - bulk_fit_start) * 1000.0
            record("bulk_fit_all_samples", bulk_fit_ms,
                   f"{plotted} samples, watson_pragmatic, auto-detect-and-fit path")
            heap_after_fit = heap_bytes(cdp)

            exit_modeling_mode(page)

            # --- box 2: export --------------------------------------------------
            page.click("#plot_tool_camera")
            page.wait_for_selector("#plot_export_modal:not([hidden])", timeout=5000)
            page.check("input[name='plot_export_format'][value='png']")
            export_start = time.perf_counter()
            with page.expect_download(timeout=60000) as download_info:
                page.click("#plot_export_download")
            download = download_info.value
            page.wait_for_selector("#plot_export_modal", state="hidden", timeout=5000)
            export_ms = (time.perf_counter() - export_start) * 1000.0
            record("export_png", export_ms, f"filename={download.suggested_filename}")

            heap_end = heap_bytes(cdp)

            # --- box 2: memory ----------------------------------------------
            if heap_start is not None:
                record_raw("js_heap_used_bytes_at_start", heap_start)
            if heap_after_load is not None:
                record_raw("js_heap_used_bytes_after_load", heap_after_load,
                            f"delta_from_start={heap_after_load - heap_start}" if heap_start is not None else "")
            if heap_after_fit is not None:
                record_raw("js_heap_used_bytes_after_bulk_fit", heap_after_fit,
                            f"delta_from_after_load={heap_after_fit - heap_after_load}" if heap_after_load is not None else "")
            if heap_end is not None:
                record_raw("js_heap_used_bytes_at_end", heap_end)

            browser.close()
    finally:
        if httpd:
            httpd.shutdown()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": stamp,
        "fixture_summary": {
            "standard_files": len(many_files),
            "standard_file_events": 6000,
            "large_files": len(large_files),
            "large_file_events": args.large_events,
            "total_files": len(many_files) + len(large_files),
        },
        "measurements": measurements,
    }
    json_path = RESULTS_DIR / f"perf_profile_{stamp}.json"
    json_path.write_text(json.dumps(report, indent=2))

    md_lines = [
        f"# PERF-02 profiling run {stamp}",
        "",
        f"Fixtures: {len(many_files)} files @ 6000 events + {len(large_files)} files @ {args.large_events} events "
        f"({len(many_files) + len(large_files)} total), metadata wizard split into Strain/Replicate/"
        "Nocodazole Arrest/Timepoint/Well columns.",
        "",
        "| Metric | Value | Detail |",
        "| --- | --- | --- |",
    ]
    for m in measurements:
        value = f"{m['ms']:.1f} ms" if "ms" in m else str(m.get("value"))
        md_lines.append(f"| {m['metric']} | {value} | {m.get('detail', '')} |")
    md_path = RESULTS_DIR / f"perf_profile_{stamp}.md"
    md_path.write_text("\n".join(md_lines) + "\n")

    print(f"\nWrote {json_path}")
    print(f"Wrote {md_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description="PERF-02 profiling harness")
    parser.add_argument("--url", default=None, help="App URL; omit to start a local server")
    parser.add_argument("--files", type=int, default=40, help="number of standard (6000-event) fixtures")
    parser.add_argument("--large-files", type=int, default=5, help="number of large-event-count fixtures")
    parser.add_argument("--large-events", type=int, default=60000, help="events per large fixture")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
