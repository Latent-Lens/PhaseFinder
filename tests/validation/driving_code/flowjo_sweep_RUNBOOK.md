# FlowJo 11.2 comparison sweep — runbook

Goal: produce FlowJo Cell Cycle Platform results for the same 30 async-yeast
FCS files already referenced by `flowjo_djf_reference.json`, across a small
grid of gating and model settings, so PhaseFinder's own QC/model sweep
(`validation_tests.py --flowjo-only`, `FLOWJO_QC_MATRIX`) can be compared
against more than one static reference number per sample. This directly
targets two open, human-intervention-tagged items in
`docs/audits/master_checklist.md`:

- **MODEL-01**: does constraining FlowJo's G2:G1 ratio (vs. fitting it freely,
  which is what PhaseFinder does) explain the ratio disagreement?
- **MODEL-02**: does FlowJo's *exact pre-fit gating* (debris/singlet/live-cell
  gates, never captured in the original analyst workbook) explain the G1
  width/mean disagreement?

## What is and isn't automated here, and why

FlowJo 11.2 has no scripting hook for the two things this sweep most needs to
vary: drawing gate boundaries, and configuring the Cell Cycle Platform's model
+ constraints. That's not a gap in this tooling — it's confirmed by FlowJo's
own docs:

- [Script Editor](https://docs.flowjo.com/flowjo/advanced-features/script-editor/)
  exposes gating-tree traversal, keyword read/write, and statistic-tethered
  *gate creation*, but nothing about the Biology Band / Cell Cycle Platform.
- [Cell Cycle: Univariate Platform docs](https://docs.flowjo.com/flowjo/experiment-based-platforms/cell-cycle-univariate/)
  state plainly that you "click on the population of interest... then select
  the Cell Cycle task from the Biology Band" and set constraints in a GUI
  panel — no scripting/API path is mentioned anywhere in that page.

What FlowJo *does* support, and what this runbook automates around, is
**[FJ Commandline](https://flowjo.com/docs/flowjo10/advanced-features/fj-commandline)**:
once a workspace has the gates + Cell Cycle nodes + a Table Editor built (a
one-time GUI setup, below), you can re-open that same workspace against the
same or updated data, headlessly, and re-export every statistic with one
command — no re-clicking. That's the piece `flowjo_sweep_run.bat`/`.ps1`
does.

So the division of labor is:

| Step | Who/what does it | Repeated how many times |
|---|---|---|
| Draw 3 gate variants | You, in the FlowJo GUI, on **one** representative sample | 3 (then group-copied) |
| Attach Cell Cycle Platform nodes (model + constraints) | You, in the FlowJo GUI, on that same sample | 9 (3 gates × 3 models) |
| Propagate gates/nodes to all 30 samples | FlowJo's native "copy to group" drag | automatic |
| Build one Table Editor table of every node's stats | You, once | 1 |
| Mark it for command-line batch export | You, once (a checkbox) | 1 |
| Recompute + export all 30×9 results | `flowjo_sweep_run.bat`/`.ps1` (FJ Commandline) | automatic, repeatable |
| Parse exported CSV → JSON, score vs. PhaseFinder | `flowjo_sweep_parse_export.py` + `flowjo_sweep_compare.py` | automatic |

Total manual GUI work is on the order of 20-30 minutes, once. Everything
after that is scripted and reproducible.

## Prerequisites

- FlowJo 11.2 installed on the Windows machine.
- The 30 FCS files, copied from this repo's
  `../test_flow_data/Asynchronous_UsedAsFloJoDFJSampleDataset/` to the Windows
  machine (FlowJo cannot read them over a network mount from this Linux box).
- On this Linux box, first run:
  ```
  python3 tests/validation/driving_code/flowjo_sweep_generate_inputs.py
  ```
  This verifies all 30 files share one identical parameter panel (it will
  refuse to proceed otherwise — a mismatched panel would make gates drawn on
  one sample invalid for others) and writes `panel_inventory.json` /
  `samples.txt` under
  `tests/validation/validation_test_data/external_fcs/datasets/flowjo_async_djf/flowjo_sweep/`
  (gitignored, local-only — same handling as `flowjo_djf_reference.json`).
  Confirmed panel facts you'll need below: DNA channel `FL7-A` (GFP/SYTOX
  Green — do **not** use `FL8-A`/PI, it reads too low, see
  `manifest.json`'s `flowjo_async_djf.format.dna_channel_evidence`), scatter
  channels `FSC-A`/`FSC-H`/`FSC-W`/`SSC-A`/`SSC-H`/`SSC-W`, time channel
  `Time`.

## Step 1 — load the 30 samples into a new workspace

Use FlowJo's normal multi-select (drag the whole folder of 30 FCS files into
a new workspace, or File > Open Samples). Do **not** try `samples.txt` /
`.txt sample list` for this first load — the exact format FJ Commandline
expects for that mode isn't documented publicly and this repo has no way to
verify it against a real FlowJo install; drag-and-drop is the well-documented
path. (`samples.txt` is still useful later, converted to Windows paths, if
you want to experiment with `.txt`-driven headless re-loads — see the
Commandline section below.)

Put all 30 in one Group (e.g. name it `async_yeast_30`) so gates/Cell Cycle
nodes can be group-copied in one drag, as FlowJo's own docs describe.

## Step 2 — draw the 3 gate variants (on one sample, then group-copy)

Pick **`EDS2026-03-26_async_1468f__A6.0001.fcs`** (strain `1468f`) as the
representative sample — it's the sample already cited elsewhere in this
project's FlowJo comparison work (`manifest.json`'s
`dna_channel_evidence`), so its numbers are a known anchor.

Draw these three populations under "All Events," using standard flow-
cytometry judgment (this project has no numeric gate boundaries to hand you —
that judgment call *is* the human-intervention input MODEL-02 is asking for):

1. **`Ungated`** — just "All Events" itself; no drawing needed. This is the
   baseline, comparable to PhaseFinder's "No QC" row.
2. **`Singlets`** — a polygon/interval gate on `FSC-A` vs `FSC-H`, excluding
   the doublet population above the main diagonal.
3. **`Singlets/Live`** — under `Singlets`, an `FSC-A` vs `SSC-A` gate
   excluding the low-FSC debris cluster. This is the closest FlowJo-side
   approximation to PhaseFinder's "All QC" row; it is **not** identical to
   PhaseFinder's algorithmic structural/time/cell/singlet QC gates, and that
   difference should be treated as a documented limitation of this
   comparison, not silently assumed away.

Once drawn on `1468f`, select all three population nodes and drag them onto
the `async_yeast_30` Group node (or right-click > "Apply to Group") to
propagate identical boundaries to all 30 samples.

Skip a separate Time-QC-equivalent gate. PhaseFinder's Time QC
(`robust-summary`/`peak-tracking`) is an algorithmic per-sample computation,
not a fixed visual boundary — there is no faithful one-shot FlowJo gate
equivalent, and fabricating one would misrepresent what's being compared.

## Step 3 — attach Cell Cycle Platform nodes (9 total: 3 gates × 3 models)

For **each** of the 3 populations from Step 2, on sample `1468f`: click the
population, open the Cell Cycle task from the Biology Band, set the DNA
parameter to `FL7-A`, and create three variants:

- **`DJF_free`** — Dean-Jett-Fox, no ratio/CV constraint (matches
  PhaseFinder's default fitting behavior).
- **`DJF_ratio1.95`** — Dean-Jett-Fox, G2:G1 mean-ratio constraint set to
  `= G1 x 1.95` (FlowJo's own docs suggest 1.95 as the initial guess). This
  is the direct MODEL-01 test: if this variant's G1/G2 means move markedly
  from `DJF_free`, the free-vs-constrained ratio convention is a real driver
  of the reference disagreement PhaseFinder already documented in
  `docs/scientific-result-contract.md`.
- **`WatsonPragmatic_free`** — Watson Pragmatic, no constraint.

Name each node exactly as above (the parser below matches on these names).
For each node, once configured on `1468f`, drag it onto the Group node to
copy the same model/constraints (not independently re-fit constraints) to
all 30 samples — per the Cell Cycle Platform docs, an *unconstrained*
original still fits independently per sample when copied; a *constrained*
original propagates the same constraint to every sample. That is exactly
the behavior wanted here.

You'll have 9 Cell Cycle nodes total (3 gate populations × 3 model variants).

## Step 4 — build the Table Editor and mark it for command-line batch export

Drag each of the 9 Cell Cycle nodes into the Table Editor, selecting **all**
statistics that node offers (don't hand-pick — the parser below is written
to find columns by matching known name fragments like `G1`, `CV`, `Mean`,
`Ratio`, `RMS`, so extra columns are harmless, missing ones aren't). Batch
the table across the `async_yeast_30` group.

Enable the table's command-line/batch export option (the equivalent, for
Table Editor, of the Layout Editor's documented "Batch to: PDF" + "Command
Line" checkboxes — look for the analogous toggle in the Table Editor's batch
settings; FlowJo's public docs don't spell out its exact label for tables,
so this is the one place you'll need to find it by inspection).

Save the workspace as `flowjo_sweep_template.wsp`, e.g. next to the 30 FCS
files on the Windows machine.

## Step 5 — headless recompute + export via FJ Commandline

From `flowjo_sweep_run.bat` (or `.ps1`) in this directory, edit the three
paths at the top (FlowJo executable, workspace, data folder, output folder),
then run it. It calls FJ Commandline roughly as:

```
"C:\Program Files\FlowJo vXX\FlowJo64.exe" "flowjo_sweep_template.wsp" "<FCS folder>" -save "flowjo_sweep_output.wsp" -batchTable -outputFolder "exports" -verbose
```

This re-opens the saved workspace, recomputes every gate/Cell Cycle node
against the data folder, and exports the Table Editor's batched table(s) into
`exports/` — per FJ Commandline's docs, using whatever "settings assigned to
[the table] in the table editor" (i.e. exactly what Step 4 configured). You
can re-run this any time (e.g. after tweaking a constraint) without touching
the GUI again.

Copy the `exports/` folder back to this repo (or any path you'll pass to the
parser below).

## Step 6 — parse + compare

```
python3 tests/validation/driving_code/flowjo_sweep_parse_export.py --exports-dir <path to exports/>
python3 tests/validation/driving_code/flowjo_sweep_compare.py
```

The parser is self-describing: it prints every column it found in the
exported CSV(s) and how it mapped each one, so a labeling mismatch (FlowJo's
exact header text isn't guaranteed to match the guesses above) is visible
immediately rather than silently producing wrong numbers. Adjust the
`FIELD_PATTERNS` dict near the top of `flowjo_sweep_parse_export.py` if a
statistic isn't recognized, then re-run.

The comparator cross-references this multi-config FlowJo result set against
PhaseFinder's own QC-matrix sweep output (the
`comparison_*.json` files `validation_tests.py --flowjo-only` already
produces in the same gitignored dataset directory) and writes a combined
report grid: every PhaseFinder QC config × every FlowJo gate/model config.
