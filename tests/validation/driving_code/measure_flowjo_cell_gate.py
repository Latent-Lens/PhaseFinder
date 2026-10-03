#!/usr/bin/env python3
"""Measure Cell Gate's proposed and effective retention on the local FlowJo set."""

import argparse
import json
from datetime import datetime

from playwright.sync_api import sync_playwright

from validation_tests import (REPO_ROOT, EXTERNAL_ROOT, apply_qc_flowjo,
                              discover_flowjo_watson, load_and_plot,
                              start_test_server, wait_for_overlay_hidden)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    bundle = discover_flowjo_watson()
    if not bundle:
        raise SystemExit("Local FlowJo reference is unavailable")
    records = []
    port, server = start_test_server(REPO_ROOT)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="domcontentloaded")
            page.wait_for_selector("#drop_zone")
            for record in bundle["records"][:args.limit]:
                name, _, _ = load_and_plot(page, record)
                before = page.evaluate("""name => {
                  const s = window.PhaseFinder.pipeline.get_state(name);
                  return { events: s.histogram.retainedCount,
                    bins: s.histogram.counts.length,
                    range: [s.histogram.edges[0], s.histogram.edges.at(-1)] };
                }""", name)
                apply_qc_flowjo(page, ("qc_cellgate",), None)
                wait_for_overlay_hidden(page, timeout_ms=120000)
                after = page.evaluate("""async name => {
                  const { plottable_rows } = await import('/js/plotting/data.js');
                  const s = window.PhaseFinder.pipeline.get_state(name);
                  const row = plottable_rows().find(r => r.name === name);
                  const gate = s.scatterGate;
                  return { eventsIn: row.data.eventCount,
                    proposedRetained: gate.retainedEventCount,
                    proposedFitted: gate.fittedEventCount,
                    reviewRequired: gate.reviewRequired,
                    reviewReasons: gate.reviewReasons,
                    maskInstalled: row.data.masks.scatter !== null,
                    effectiveRetained: row.data.filtered.eventCount,
                    histogramRetained: s.histogram.retainedCount,
                    histogramBins: s.histogram.counts.length,
                    histogramRange: [s.histogram.edges[0], s.histogram.edges.at(-1)] };
                }""", name)
                after["strain"] = record["strain"]
                after["histogramEventCountUnchanged"] = before["events"] == after["histogramRetained"]
                after["beforeHistogramRetained"] = before["events"]
                after["beforeHistogramBins"] = before["bins"]
                after["beforeHistogramRange"] = before["range"]
                records.append(after)
                print(f'{record["strain"]}: {after["proposedRetained"]}/{after["eventsIn"]} proposed, '
                      f'{after["effectiveRetained"]} effective, review={after["reviewRequired"]}', flush=True)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    suffix = f"_{args.limit}" if args.limit else ""
    output = EXTERNAL_ROOT / "datasets" / "flowjo_async_djf" / f"cell_gate_retention{suffix}.json"
    output.write_text(json.dumps({"measured": datetime.now().astimezone().isoformat(),
                                  "records": records}, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
