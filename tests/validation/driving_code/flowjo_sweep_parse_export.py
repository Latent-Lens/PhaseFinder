#!/usr/bin/env python3
"""Parse FlowJo Table Editor batch-export CSV(s) from the sweep in
flowjo_sweep_RUNBOOK.md into a normalized, PhaseFinder-comparable JSON.

FlowJo's own docs do not specify -batchTable's exact CSV column-naming
convention (confirmed absent from
https://flowjo.com/docs/flowjo10/advanced-features/fj-commandline), so this
parser does not hardcode column names. Instead, for every column header it
looks for the gate-variant name (Ungated / Singlets / Singlets/Live), the
Cell-Cycle node name (DJF_free / DJF_ratio1.95 / WatsonPragmatic_free -- the
exact names flowjo_sweep_RUNBOOK.md step 3 asks you to use), and a
statistic-name fragment (see FIELD_PATTERNS below) as substrings, and reports
every column it could NOT confidently map rather than silently dropping or
mis-assigning it. If FlowJo's actual headers don't match, edit
FIELD_PATTERNS / GATE_NAMES / MODEL_NAMES below and rerun -- this is meant to
be tuned against one real export, not guessed right on the first try.

Usage:
  python3 tests/validation/driving_code/flowjo_sweep_parse_export.py \
      --exports-dir <path to the exports/ folder copied back from Windows>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = (REPO_ROOT / "tests/validation/validation_test_data/external_fcs/datasets"
           / "flowjo_async_djf" / "flowjo_sweep")
OUTPUT = OUT_DIR / "flowjo_sweep_reference.json"

# Must match the population names flowjo_sweep_RUNBOOK.md step 2 asks you to draw.
GATE_NAMES = ["Ungated", "Singlets/Live", "Singlets"]  # longer/more-specific names first
# Must match the Cell Cycle node names flowjo_sweep_RUNBOOK.md step 3 asks you to create.
MODEL_NAMES = ["DJF_ratio1.95", "DJF_free", "WatsonPragmatic_free"]

# statistic key -> regexes to search for in a column header (case-insensitive,
# checked in order; first match wins). Regex, not plain substring, so e.g. a
# header ending exactly "...: %S" (no trailing space -- FlowJo's own typical
# formatting) still matches without also matching unrelated text containing
# "s%" (word-boundaried). Extend/edit this once you see a real FlowJo export
# -- these are best-guess fragments based on FlowJo's documented statistic
# names (docs.flowjo.com Cell Cycle: Univariate Platform), not a verified
# schema.
FIELD_PATTERNS = {
    "g1_fraction": [r"%\s*g1\b", r"\bg1\s*%"],
    "s_fraction": [r"%\s*s\b", r"\bs\s*%", r"\bs\s*phase\b"],
    "g2_fraction": [r"%\s*g2\b", r"\bg2\s*%"],
    "g1_mean": [r"\bg1\s*mean\b"],
    "g1_cv_percent": [r"\bg1\s*cv\b"],
    "g2_mean": [r"\bg2\s*mean\b"],
    "g2_cv_percent": [r"\bg2\s*cv\b"],
    "g2_g1_ratio": [r"g2\s*[:/]\s*g1", r"\bratio\b"],
    "rms": [r"\brms\b"],
    "count": [r"\bcount\b", r"#\s*events", r"\bn\s*events\b"],
}

STRAIN_RE = re.compile(r"async_([^_]+)__")


def strain_from_text(text: str) -> str | None:
    match = STRAIN_RE.search(text)
    return match.group(1) if match else None


def sniff_dialect(sample_text: str):
    try:
        return csv.Sniffer().sniff(sample_text, delimiters=",;\t")
    except csv.Error:
        class _Fallback(csv.Dialect):
            delimiter = ","
            quotechar = '"'
            doublequote = True
            skipinitialspace = False
            lineterminator = "\r\n"
            quoting = csv.QUOTE_MINIMAL
        return _Fallback


def classify_column(header: str):
    """header -> (gate_name, model_name, stat_key) or None if unmapped."""
    lower = header.lower()
    gate = next((g for g in GATE_NAMES if g.lower() in lower), None)
    model = next((m for m in MODEL_NAMES if m.lower() in lower), None)
    stat = None
    for key, patterns in FIELD_PATTERNS.items():
        if any(re.search(pat, lower) for pat in patterns):
            stat = key
            break
    if gate and model and stat:
        return gate, model, stat
    return None


def find_sample_column(header_row: list[str]) -> int | None:
    for i, h in enumerate(header_row):
        if h.strip().lower() in ("sample", "sample name", "file", "filename", "$fil", "fcs file"):
            return i
    # Fall back to the first column that contains an async_<strain>__ token
    # anywhere in a couple of sample rows -- checked by the caller instead,
    # since that needs row data, not just the header.
    return None


def parse_csv(path: Path):
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    dialect = sniff_dialect(raw[:4096])
    reader = csv.reader(raw.splitlines(), dialect=dialect)
    rows = list(reader)
    if not rows:
        return [], [], []
    header = rows[0]
    body = [r for r in rows[1:] if any(cell.strip() for cell in r)]

    sample_col = find_sample_column(header)
    if sample_col is None:
        # Look for the column whose values contain the async_<strain>__ token.
        for i in range(len(header)):
            if body and strain_from_text(body[0][i] if i < len(body[0]) else "") :
                sample_col = i
                break
    if sample_col is None:
        sample_col = 0  # last resort: assume first column identifies the sample

    mapped = {}     # header -> (gate, model, stat)
    unmapped = []
    for i, h in enumerate(header):
        if i == sample_col:
            continue
        cls = classify_column(h)
        if cls:
            mapped[i] = cls
        else:
            unmapped.append(h)

    return header, body, {"sample_col": sample_col, "mapped": mapped, "unmapped": unmapped}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.exports_dir.is_dir():
        print(f"ERROR: exports dir not found: {args.exports_dir}")
        return 2

    csv_files = sorted(args.exports_dir.rglob("*.csv"))
    if not csv_files:
        print(f"ERROR: no .csv files under {args.exports_dir}")
        return 2

    # strain -> gate -> model -> {stat: value}
    results: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    all_unmapped = []
    total_rows_used = 0

    for path in csv_files:
        header, body, info = parse_csv(path)
        if not header:
            print(f"  {path.name}: empty, skipped")
            continue
        print(f"{path.name}: {len(header)} columns, {len(body)} rows, "
              f"{len(info['mapped'])} mapped, {len(info['unmapped'])} unmapped")
        all_unmapped.extend((path.name, h) for h in info["unmapped"])

        for row in body:
            sample_text = row[info["sample_col"]] if info["sample_col"] < len(row) else ""
            strain = strain_from_text(sample_text) or sample_text.strip()
            if not strain:
                continue
            for col_idx, (gate, model, stat) in info["mapped"].items():
                if col_idx >= len(row):
                    continue
                raw_val = row[col_idx].strip().rstrip("%")
                if not raw_val:
                    continue
                try:
                    value = float(raw_val)
                except ValueError:
                    continue
                results.setdefault(strain, {}).setdefault(gate, {}).setdefault(model, {})[stat] = value
                total_rows_used += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_by": "tests/validation/driving_code/flowjo_sweep_parse_export.py",
        "source_dir": str(args.exports_dir.resolve()),
        "gate_names": GATE_NAMES,
        "model_names": MODEL_NAMES,
        "strains_found": sorted(results),
        "value_cells_parsed": total_rows_used,
        "unmapped_columns": [{"file": f, "header": h} for f, h in all_unmapped],
        "results": results,
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")

    print()
    print(f"Strains found: {len(results)} / 30 expected")
    if all_unmapped:
        print(f"WARNING: {len(all_unmapped)} column(s) could not be mapped to a "
              f"(gate, model, statistic) triple -- see 'unmapped_columns' in the output "
              f"JSON, or edit GATE_NAMES/MODEL_NAMES/FIELD_PATTERNS at the top of this "
              f"script and rerun. Unmapped columns are NOT silently included as data.")
    if len(results) < 30:
        missing = set()  # can't know real strain names without the reference JSON; just flag the count
        print(f"WARNING: expected 30 strains, found {len(results)}. Check the sample-column "
              f"detection and the async_<strain>__ token in the exported sample names.")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
