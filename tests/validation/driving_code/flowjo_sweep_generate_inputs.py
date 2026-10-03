#!/usr/bin/env python3
"""Build the local-only input files for the FlowJo 11.2 comparison sweep (MODEL-01/MODEL-02).

This is step 1 of the FlowJo automation pipeline described in
flowjo_sweep_RUNBOOK.md. It runs entirely on this machine (no FlowJo needed):
it verifies the 30 async-yeast FCS files share one identical parameter panel
(refusing to proceed if not -- a mixed panel would make one shared FlowJo
workspace/gate set invalid for some files), then writes:

  datasets/flowjo_async_djf/flowjo_sweep/samples.txt        -- one absolute
      FCS path per line, for FJ Commandline's ".txt sample list" input mode.
  datasets/flowjo_async_djf/flowjo_sweep/panel_inventory.json -- the shared
      parameter panel (PnN/PnS/PnR) plus per-file byte size + SHA-256, so a
      change in the source FCS set is detectable later.

Both outputs are local-only: they land under the gitignored
datasets/flowjo_async_djf/ directory next to flowjo_djf_reference.json, never
committed, consistent with how that reference is already handled (see
generate_flowjo_djf_reference.py).

Usage:
  python3 tests/validation/driving_code/flowjo_sweep_generate_inputs.py
      [--fcs-dir DIR] [--no-hash]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FLOW_PLOTTER = REPO_ROOT.parent
DEFAULT_FCS_DIR = FLOW_PLOTTER / "test_flow_data" / "Asynchronous_UsedAsFloJoDFJSampleDataset"
OUT_DIR = (REPO_ROOT / "tests/validation/validation_test_data/external_fcs/datasets"
           / "flowjo_async_djf" / "flowjo_sweep")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_fcs_text_segment(path: Path) -> dict:
    with path.open("rb") as f:
        header = f.read(58)
        text_start = int(header[10:18].decode().strip())
        text_end = int(header[18:26].decode().strip())
        f.seek(text_start)
        raw = f.read(text_end - text_start + 1)
    delim = raw[0:1]
    parts = raw[1:].split(delim)
    kv = {}
    it = iter(parts)
    for k, v in zip(it, it):
        kv[k.decode("latin-1")] = v.decode("latin-1")
    return kv


def panel_of(kv: dict) -> tuple:
    # Compares PnN/PnS (channel identity) only, not PnR: $P1R (Time) legitimately
    # varies per file -- it is each acquisition's run duration in seconds, not a
    # panel difference -- and every other channel's PnR is a constant 1000 on
    # this dataset, so including it would only mask the one case that matters.
    par = int(kv.get("$PAR", 0))
    return tuple(
        (kv.get(f"$P{i}N", ""), kv.get(f"$P{i}S", ""))
        for i in range(1, par + 1)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fcs-dir", type=Path, default=DEFAULT_FCS_DIR)
    parser.add_argument("--no-hash", action="store_true", help="skip SHA-256 (faster; sizes only)")
    args = parser.parse_args()

    if not args.fcs_dir.is_dir():
        print(f"ERROR: FCS directory not found: {args.fcs_dir}")
        return 2

    files = sorted(args.fcs_dir.glob("*.fcs"))
    if not files:
        print(f"ERROR: no .fcs files in {args.fcs_dir}")
        return 2

    panels = {}
    per_file = []
    for path in files:
        kv = read_fcs_text_segment(path)
        panel = panel_of(kv)
        panels.setdefault(panel, []).append(path.name)
        per_file.append({
            "filename": path.name,
            "byte_size": path.stat().st_size,
            "sha256": None if args.no_hash else sha256_of(path),
            "total_events": kv.get("$TOT"),
            "byte_order": kv.get("$BYTEORD"),
            "datatype": kv.get("$DATATYPE"),
        })

    if len(panels) != 1:
        print(f"ERROR: {len(panels)} distinct parameter panels found across {len(files)} files; "
              "a single shared FlowJo workspace/gate set assumes one panel. Panels:")
        for panel, names in panels.items():
            print(f"  {len(names)} files: {[n[0] for n in panel]}")
            for n in names[:5]:
                print(f"    {n}")
        return 1

    (panel,) = panels.keys()
    channel_names = [p[0] for p in panel]
    print(f"OK: {len(files)} files share one panel ({len(panel)} parameters).")
    for role, hint in (("Time", "Time"), ("scatter", "FSC-A/FSC-H/SSC-A"), ("DNA", "FL7-A")):
        present = [n for n in channel_names if hint.split("/")[0].split("-")[0] in n or n == hint]
        print(f"  {role} candidates near {hint!r}: {present}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    samples_txt = OUT_DIR / "samples.txt"
    samples_txt.write_text("\n".join(str(p.resolve()) for p in files) + "\n")

    inventory = {
        "generated_by": "tests/validation/driving_code/flowjo_sweep_generate_inputs.py",
        "fcs_dir": str(args.fcs_dir.resolve()),
        "file_count": len(files),
        "panel": [{"pnn": n, "pns": s} for n, s in panel],
        "panel_note": "Compared on PnN/PnS only; $P1R (Time) legitimately varies per file "
                       "(acquisition run duration) and is not part of the identity check.",
        "dna_channel_pnn": "FL7-A",
        "dna_channel_pns": "GFP",
        "dna_channel_note": "Confirmed in tests/validation/validation_test_data/external_fcs/manifest.json "
                             "(flowjo_async_djf.format): FL7-A percentiles bracket FlowJo's reported G1/G2 "
                             "means; FL8-A (PI) reads far too low. Do not use FL8-A.",
        "scatter_channels": {"fsc_a": "FSC-A", "fsc_h": "FSC-H", "fsc_w": "FSC-W",
                              "ssc_a": "SSC-A", "ssc_h": "SSC-H", "ssc_w": "SSC-W"},
        "time_channel": "Time",
        "files": per_file,
    }
    (OUT_DIR / "panel_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")

    print(f"Wrote {samples_txt.relative_to(REPO_ROOT)} ({len(files)} paths)")
    print(f"Wrote {(OUT_DIR / 'panel_inventory.json').relative_to(REPO_ROOT)}")
    print("Next: follow flowjo_sweep_RUNBOOK.md to build the FlowJo workspace, "
          "then run flowjo_sweep_run.bat / .ps1 on the Windows machine.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
