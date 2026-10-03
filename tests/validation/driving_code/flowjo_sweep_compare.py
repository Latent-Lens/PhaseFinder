#!/usr/bin/env python3
"""Cross-reference the FlowJo comparison sweep against PhaseFinder's own QC
sweep, to help resolve MODEL-01 (G2:G1 ratio convention) and MODEL-02
(pre-fit gating / G1 CV disagreement) in docs/audits/master_checklist.md.

Inputs (both already produced by other scripts in this directory, both
local-only/gitignored):

  1. flowjo_sweep_reference.json -- written by flowjo_sweep_parse_export.py
     from the real FlowJo 11.2 export (3 gate variants x 3 Cell Cycle model
     configs, per strain).
  2. The most recent comparison_*.json -- written by
     validation_tests.py --flowjo-only (write_flowjo_watson_report), which
     already fits PhaseFinder's own DJF/Watson under 8 QC configs per strain.

This script does NOT invoke Playwright / validation_tests.py itself -- it
only reads JSON both scripts already produced, so it has no browser
dependency and can be re-run cheaply after either input changes.

Output: a combined grid (every PhaseFinder QC config x every FlowJo
gate/model config), written as JSON + Markdown into the same gitignored
dataset directory as its inputs.

Usage:
  python3 tests/validation/driving_code/flowjo_sweep_compare.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = REPO_ROOT / "tests/validation/validation_test_data/external_fcs/datasets/flowjo_async_djf"
SWEEP_JSON = DATASET_DIR / "flowjo_sweep" / "flowjo_sweep_reference.json"

# PhaseFinder model_id (from comparison_*.json) -> substring to find the
# matching FlowJo Cell Cycle node name (from flowjo_sweep_reference.json).
# dean_jett_fox has two FlowJo variants (free-fit vs. ratio-constrained) --
# both are compared, since the free-vs-constrained split IS the MODEL-01 test.
MODEL_MATCH = {
    "dean_jett_fox": ["DJF"],
    "watson_classic": ["Watson"],
}

FRACTION_STATS = ("g1_fraction", "s_fraction", "g2_fraction")


def normalize_percent(value: float) -> float:
    # FlowJo may export %G1 as "45.23" or "45.23%" (parser already strips a
    # trailing %) or, less commonly for a Table Editor stat, as a 0-1
    # fraction. Treat anything <= 1.5 as a fraction and rescale to percent --
    # documented here rather than silently guessed, since the real header/
    # format wasn't available to verify against at write time.
    return value * 100 if value <= 1.5 else value


def find_latest_comparison_json() -> Path | None:
    candidates = sorted(DATASET_DIR.glob("comparison_*.json"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_flowjo_sweep():
    if not SWEEP_JSON.is_file():
        return None
    data = json.loads(SWEEP_JSON.read_text())
    # strain -> gate -> model -> {stat: percent}
    normalized = {}
    for strain, gates in data.get("results", {}).items():
        normalized[strain] = {}
        for gate, models in gates.items():
            normalized[strain][gate] = {}
            for model, stats in models.items():
                out = dict(stats)
                for key in FRACTION_STATS:
                    if key in out:
                        out[key] = normalize_percent(out[key])
                normalized[strain][gate][model] = out
    return normalized


def load_phasefinder_sweep(path: Path):
    data = json.loads(path.read_text())
    # strain -> qc_label -> model_id -> {g1_fraction, s_fraction, g2_fraction, g2_g1_ratio}
    out = {}
    for sample in data.get("results", []):
        strain = sample["strain"]
        out[strain] = {}
        for cfg in sample.get("configs", []):
            if cfg["status"] != "PASS":
                continue
            label = cfg["label"]
            out[strain][label] = {}
            for model_id, score in cfg.get("scores", {}).items():
                phases = score.get("phases", {})
                cell = {}
                for phase, key in (("g1", "g1_fraction"), ("s", "s_fraction"), ("g2", "g2_fraction")):
                    if phase in phases and phases[phase].get("ours") is not None:
                        cell[key] = phases[phase]["ours"] * 100
                ratio_check = score.get("checks", {}).get("g2_g1_ratio")
                if ratio_check and ratio_check.get("ours") is not None:
                    cell["g2_g1_ratio"] = ratio_check["ours"]
                out[strain][label][model_id] = cell
    return out


def flowjo_models_for(model_id: str, flowjo_models: list[str]) -> list[str]:
    fragments = MODEL_MATCH.get(model_id, [])
    return [m for m in flowjo_models if any(frag.lower() in m.lower() for frag in fragments)]


def build_grid(pf_sweep, fj_sweep):
    strains = sorted(set(pf_sweep) & set(fj_sweep))
    if not strains:
        return [], strains

    rows = []
    for strain in strains:
        pf_configs = pf_sweep[strain]
        fj_gates = fj_sweep[strain]
        for pf_label, pf_models in pf_configs.items():
            for model_id, pf_cell in pf_models.items():
                for gate_name, fj_models in fj_gates.items():
                    matches = flowjo_models_for(model_id, list(fj_models))
                    for fj_model_name in matches:
                        fj_cell = fj_models[fj_model_name]
                        deltas = {}
                        for stat in ("g1_fraction", "s_fraction", "g2_fraction", "g2_g1_ratio"):
                            if stat in pf_cell and stat in fj_cell:
                                deltas[stat] = abs(pf_cell[stat] - fj_cell[stat])
                        if not deltas:
                            continue
                        rows.append({
                            "strain": strain,
                            "pf_qc_config": pf_label,
                            "pf_model": model_id,
                            "fj_gate": gate_name,
                            "fj_model": fj_model_name,
                            "pf": pf_cell,
                            "fj": fj_cell,
                            "abs_delta": deltas,
                        })
    return rows, strains


def summarize(rows):
    # (pf_qc_config, fj_gate, fj_model) -> list of g1_fraction abs deltas, for
    # the DJF-only view (the model this project fits for every sample).
    from collections import defaultdict
    buckets = defaultdict(list)
    for row in rows:
        if row["pf_model"] != "dean_jett_fox":
            continue
        if "g1_fraction" not in row["abs_delta"]:
            continue
        key = (row["pf_qc_config"], row["fj_gate"], row["fj_model"])
        buckets[key].append(row["abs_delta"]["g1_fraction"])
    summary = []
    for key, deltas in buckets.items():
        summary.append({
            "pf_qc_config": key[0], "fj_gate": key[1], "fj_model": key[2],
            "n": len(deltas), "mean_abs_delta_g1_pp": sum(deltas) / len(deltas),
            "max_abs_delta_g1_pp": max(deltas),
        })
    summary.sort(key=lambda s: s["mean_abs_delta_g1_pp"])
    return summary


def write_report(rows, summary, strains, pf_source: Path):
    out_json = DATASET_DIR / "flowjo_sweep_comparison.json"
    out_json.write_text(json.dumps({
        "phasefinder_source": str(pf_source.relative_to(REPO_ROOT)),
        "flowjo_sweep_source": str(SWEEP_JSON.relative_to(REPO_ROOT)),
        "strains_compared": strains,
        "cell_count": len(rows),
        "summary_dean_jett_fox_g1": summary,
        "rows": rows,
    }, indent=2) + "\n")

    lines = [
        "# FlowJo sweep vs. PhaseFinder QC sweep -- combined comparison", "",
        f"PhaseFinder source: `{pf_source.relative_to(REPO_ROOT)}`  ",
        f"FlowJo sweep source: `{SWEEP_JSON.relative_to(REPO_ROOT)}`  ",
        f"Strains compared: {len(strains)}", "",
        "This ranks every (PhaseFinder QC config) x (FlowJo gate variant x model) "
        "combination by mean |Δ %G1| across strains, for PhaseFinder's Dean-Jett-Fox "
        "fit -- the model PhaseFinder fits on every sample. A ratio-constrained FlowJo "
        "model (`DJF_ratio1.95`) scoring closer than its free-fit sibling "
        "(`DJF_free`) at the same gate is direct evidence for MODEL-01; a gated "
        "FlowJo variant (`Singlets`/`Singlets/Live`) scoring closer than `Ungated` "
        "at the same PhaseFinder QC config is evidence for MODEL-02. See "
        "docs/scientific-result-contract.md before treating either as a defect to "
        "fix rather than a documented convention difference.", "",
        "## Ranked: PhaseFinder QC config x FlowJo gate/model (DJF, %G1)", "",
        "| PF QC config | FlowJo gate | FlowJo model | n strains | mean \\|Δ %G1\\| | max \\|Δ %G1\\| |",
        "|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(f'| {s["pf_qc_config"]} | {s["fj_gate"]} | {s["fj_model"]} | {s["n"]} '
                     f'| {s["mean_abs_delta_g1_pp"]:.2f} | {s["max_abs_delta_g1_pp"]:.2f} |')
    lines.append("")

    lines += ["## Per-strain detail", "",
              "| strain | PF QC config | PF model | FJ gate | FJ model | Δ %G1 | Δ %S | Δ %G2 | Δ ratio |",
              "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        d = row["abs_delta"]
        def fmt(k):
            return f'{d[k]:.2f}' if k in d else "—"
        lines.append(f'| {row["strain"]} | {row["pf_qc_config"]} | {row["pf_model"]} | {row["fj_gate"]} '
                     f'| {row["fj_model"]} | {fmt("g1_fraction")} | {fmt("s_fraction")} '
                     f'| {fmt("g2_fraction")} | {fmt("g2_g1_ratio")} |')

    out_md = DATASET_DIR / "flowjo_sweep_comparison.md"
    out_md.write_text("\n".join(lines) + "\n")
    return out_json, out_md


def main() -> int:
    fj_sweep = load_flowjo_sweep()
    if fj_sweep is None:
        print(f"ERROR: {SWEEP_JSON} not found. Run flowjo_sweep_parse_export.py first.")
        return 2

    pf_source = find_latest_comparison_json()
    if pf_source is None:
        print(f"ERROR: no comparison_*.json found under {DATASET_DIR}. "
              "Run validation_tests.py --flowjo-only first.")
        return 2
    print(f"Using PhaseFinder sweep: {pf_source.relative_to(REPO_ROOT)}")
    pf_sweep = load_phasefinder_sweep(pf_source)

    rows, strains = build_grid(pf_sweep, fj_sweep)
    if not rows:
        print("ERROR: no overlapping strains/models between the two sweeps -- "
              "check that flowjo_sweep_reference.json's strain keys match the "
              "'async_<strain>__' tokens used elsewhere in this project.")
        return 1

    summary = summarize(rows)
    out_json, out_md = write_report(rows, summary, strains, pf_source)

    print(f"Compared {len(strains)} strains, {len(rows)} cells.")
    if summary:
        best = summary[0]
        print(f"Best-matching combo (DJF, %G1): {best['pf_qc_config']!r} x "
              f"{best['fj_gate']!r} x {best['fj_model']!r} "
              f"(mean |Δ %G1| = {best['mean_abs_delta_g1_pp']:.2f}pp, n={best['n']})")
    print(f"Wrote {out_json.relative_to(REPO_ROOT)}")
    print(f"Wrote {out_md.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
