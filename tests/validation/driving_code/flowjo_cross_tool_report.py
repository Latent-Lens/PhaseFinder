#!/usr/bin/env python3
"""Render local FlowJo comparison JSONs to a private HTML table."""

import argparse
import html
import json
from pathlib import Path


DATASET_DIR = (Path(__file__).resolve().parents[1] / "validation_test_data" /
               "external_fcs" / "datasets" / "flowjo_async_djf")


def render(paths):
    rows = []
    seen = set()
    for path in paths:
        for sample in json.loads(path.read_text())["results"]:
            for config in sample["configs"]:
                key = (sample["strain"], config["label"])
                if key in seen:
                    raise ValueError(f"duplicate comparison row: {key}")
                seen.add(key)
                if config["status"] != "PASS":
                    rows.append((*key, "—", f"{config['status']} at {config.get('stage')}",
                                 "—", "—", "—", "—", "—", "—", config.get("error")))
                    continue
                for model, score in config["scores"].items():
                    audit = config["fitAudit"][model]
                    fractions = " / ".join(
                        f"{score['phases'][phase]['ours'] * 100:.1f} / "
                        f"{score['phases'][phase]['ref'] * 100:.1f}"
                        for phase in ("g1", "s", "g2"))
                    warnings = ", ".join(sorted({
                        f"{w.get('code', w.get('id'))} ({w['severity']})"
                        for w in audit.get("warnings", [])}))
                    peak = config.get("peakDetection") or {}
                    bounds = ", ".join(f"{flag['parameter']}: {flag['side']}"
                                       for flag in audit.get("boundFlags", []))
                    rescaled = ("pass" if score["rescaledAllPass"] else "review") if "rescaledAllPass" in score else "—"
                    rows.append((*key, model, config.get("mode"), fractions,
                                 "pass" if score["all_pass"] else "review", rescaled,
                                 config.get("eventsRetained"), peak.get("status", "—"), bounds, warnings))
    headings = ("Sample", "QC / comparison", "Model", "Mode / status", "G1 / S / G2: ours / reference (%)",
                "Raw tolerance", "Rescaled tolerance", "Events retained", "Peak status", "Bound flags", "Warnings")
    head = "".join(f"<th scope='col'>{html.escape(h)}</th>" for h in headings)
    body = "\n".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in row) + "</tr>"
                     for row in rows)
    return ("<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<title>Private FlowJo comparison</title><style>body{font:14px system-ui;margin:2rem}"
            "table{border-collapse:collapse}th,td{border:1px solid #aaa;padding:.35rem;text-align:left}"
            "tr:nth-child(even){background:#eee}</style><h1>Private FlowJo comparison</h1>"
            "<p>DJF pass/fail uses raw FlowJo fractions. Rescaled-to-100% scoring is diagnostic. "
            "The FlowJo seed mean windows are documented for 1468f only.</p>"
            f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></html>\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path, help="Comparison JSON shard reports")
    args = parser.parse_args()
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    output = DATASET_DIR / "cross_tool_report.html"
    output.write_text(render(args.reports))
    print(output)
