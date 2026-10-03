# FlowJo reference settings for the 30-sample async set — evidence for HI-REFERENCE

**Date:** 2026-09-23
**Scope:** satisfies `HI-REFERENCE` except for one residual definition question (§6). Bears directly
on `MODEL-02`, and therefore on `MODEL-07`.
**Evidence:** `docs/audits/evidence/flowjo_reference_2026_09_23/` — the FlowJo workspaces themselves.
**Produced by:** recovery of the originating workspaces plus reconciliation against the reference
spreadsheets and the raw FCS. No new FlowJo run was performed.

## Summary

The matched FlowJo workspace has been **recovered**, and it reproduces the published reference
values exactly. Both halves of the ask are now on the record:

| Half of the ask | Status |
|---|---|
| **Exact pre-fit gates** | **Supplied.** None. Confirmed two independent ways (§1). |
| **Matched workspace/model configuration** | **Supplied.** `djf_seed.wsp`, settings in §3. |
| Documented width convention | **Partial.** The CV was *free-fitted*, not constrained (§5). FlowJo's internal CV definition remains undocumented. |

`HI-REFERENCE` can be marked satisfied for the workspace-and-gates requirement. Read §6 before
closing `MODEL-02` on it.

## 1. There were no pre-fit gates — confirmed twice

**Count reconciliation.** The `Count` column in `DJF Model_DataCompilation_Flojo_3_26_2026.xlsx`
was reconciled against `$TOT` read from each source FCS TEXT segment. **30 of 30 match exactly;
16,492,824 events on both sides, zero discrepancy.** A gate of any kind would have to remove zero
events from all thirty files, which no real gate does.

**Workspace attributes.** Independently, the recovered workspace carries
`autoGate="0" gateG1="0" gateG2="0" gateS="0"` on the profile — no auto-gating, no per-phase gates.

Two independent lines of evidence, same conclusion: the fit consumed every recorded event. No QC,
no margin removal, no doublet gate, no scatter trim, no debris gate.

## 2. The recovered workspace reproduces the reference

`djf_seed.wsp`, sample `EDS2026-03-26_async_1468f__A6.0001` (A6), 460,415 events.

| Statistic | Published reference | `djf_seed.wsp` | |
|---|---|---|---|
| PercentG1 | 21.6 | 21.61 | ✓ |
| PercentS | 26.7 | 26.74 | ✓ |
| PercentG2 | 46.0 | 45.99 | ✓ |
| G1 Mean | 175 | 174.7 | ✓ |
| **G1 CV** | **9.74** | **9.740** | **exact** |
| G2 Mean | 350 | 350.5 | ✓ |
| G2 CV | 9.44 | 9.438 | ✓ |
| Count | 460,415 | 460,415 | ✓ |

The spreadsheet is rounded; the workspace is full precision. G1 CV agreeing to the published
precision identifies this as the same run, not merely a similar one.

RMSD 90.33.

## 3. The settings, on the record

```xml
<profile model="DeanJettFox" parameter="FL7-A" syncPeak="0"
         autoGate="0" gateG1="0" gateG2="0" gateS="0">
  <Constraints>
    <Peak id="1"><Mean><Range min="146.8110709988" max="212.9963898917"/></Mean><Cv/></Peak>
    <Peak id="2"><Mean><Range min="300.8423586041" max="398.3152827918"/></Mean><Cv/></Peak>
  </Constraints>
</profile>
```

- **Model:** Dean-Jett-Fox. **`syncPeak="0"` — synchronisation was OFF.** This had been an open
  question; the published `G2:G1` ratios spanning 1.940–2.292 are consistent with it.
- **DNA channel:** `FL7-A` (GFP/SYTOX Green), `$P29R = 1000`, linear — consistent with the
  `format.dna_channel_evidence` authority already recorded under MODEL-02.
- **Mean constraints:** present, but the values are machine-generated, not typed. They are centred
  on the true peaks (G1 window centre ≈ 180, G2 ≈ 350) and are *narrow* — roughly ±18% around G1.
- **`<Cv/>` is empty on both peaks — no CV constraint was applied.** See §5; this is the finding
  that matters most for MODEL-02.

## 4. A FlowJo Watson reference now exists — correcting an earlier statement

An earlier draft of this document stated that no FlowJo Watson reference exists for this set. That
was true of the *spreadsheets* and is **no longer true overall**: `watson_seed.wsp` is a FlowJo
Watson fit of the same sample under the same settings.

| Statistic | FlowJo DJF | FlowJo Watson | Flowreader Watson (spreadsheet) |
|---|---|---|---|
| PercentG1 | 21.61 | 22.23 | 22.01 |
| PercentS | 26.74 | **32.55** | **41.0** |
| PercentG2 | 45.99 | 38.96 | 36.98 |
| G1 Mean | 174.7 | 175.5 | — |
| G1 CV | 9.740 | 9.232 | — |
| G2 Mean | 350.5 | 353.5 | — |

This separates two effects that were previously conflated. Watson-vs-DJF *within FlowJo* moves S%
from 26.74 to 32.55. Flowreader's Watson reports 41.0 — so Flowreader differs from FlowJo's own
Watson by more than FlowJo's two models differ from each other.

**Flowreader (Flowreada) has no relationship to PhaseFinder** — confirmed by the project owner,
2026-09-23. Unrelated third-party tool; not a predecessor, fork or shared codebase. Its column
carries no validation weight here.

For MODEL-02, compare against **FlowJo DJF** (the 30-sample published reference) or **FlowJo
Watson** (one sample, `watson_seed.wsp`) — both are now available, and both are FlowJo. Do not
compare against the Flowreader column.

### Watson S-phase interface parameters (MODEL-12, checked 2026-09-24)

[FlowJo's Univariate Cell Cycle documentation](https://docs.flowjo.com/flowjo/experiment-based-platforms/cell-cycle-univariate/)
calls its implementation **Watson Pragmatic** and explicitly identifies Watson,
Chambers & Smith (1987) as its method. The recovered FlowJo Watson workspace
serializes `<SPhase id="Watson" kg1="-1.05" kg2="-1.1"/>`. In the cited primary
paper (`docs/references/watson_1987.pdf`, pp. 2–3, equations 1–2), `kG1` and
`kG2` shift the leading and trailing S-phase probability interfaces relative
to the G1 and G2 means in units of each peak's standard deviation. The shifts
are solved from the S/G1 and S/G2 envelope frequency ratios; they are not CV
constraints or a global linear S-phase slope. FlowJo's public page does not
define the workspace attribute names separately, so the direct mapping from
serialized values to internal solver state remains an inference from the
matching names and model citation, not a controlled FlowJo perturbation test.

PhaseFinder's `watson_classic` uses an integrated, broadened trapezoid with a
single slope and has no `kG1`/`kG2` interface shifts. Its
`watson_pragmatic` instead subtracts locally fitted peaks and has fixed
asymmetric fit windows, not the paper's iterative error-function interface
solve. Neither model has a parameter equivalent to the workspace values. No
new parameter was added without a documented FlowJo mapping and independent
synthetic/reference validation.

## 5. What this settles for MODEL-02

MODEL-02 records that PhaseFinder's G1 CV runs ~0.68× FlowJo's, that the offset is a width
disagreement rather than a location error, and asks whether PhaseFinder's sigma is too narrow or
FlowJo's is too wide. Two hypotheses are now eliminated:

**Different event populations — eliminated.** Gates are absent (§1, two ways). Both tools fitted
every event in the file. The width difference is not a population artefact.

**An imposed FlowJo CV — eliminated.** `<Cv/>` is empty on both peaks, so FlowJo's CV was **not
constrained**; 9.740 is a free-fit result under DJF on ungated data. The 0.68× ratio is therefore
two free fits disagreeing about width, not one tool honouring a wider imposed convention.

That sharpens the question to its irreducible form: two estimators, the same events, no width
constraint on either, and a persistent ~1.5× disagreement in fitted sigma.

**One further observation, offered as a lead rather than a finding.** FlowJo's mean-constraint
windows are machine-generated and narrow — G1 confined to 146.81–213.00 around a true peak of ~175.
A search window that tight can influence a fitted width, because it bounds where the peak may sit
while the tails are fitted. Whether PhaseFinder applies a comparable bound is worth checking before
concluding the disagreement is purely in the peak-shape family. This is a hypothesis, not a result.

## 6. The residual question

What is **not** supplied is FlowJo's *definition* of the CV it reports — specifically whether it is a
whole-distribution standard deviation or a clean-flank sigma. That distinction is the one
MODEL-02's `verify_peak_width.mjs` control was built around, and a workspace records the value, not
the convention that produced it. It is a FlowJo documentation question, not a settings question, and
this evidence does not close it.

## 7. What was tried and did not work — do not reuse

A parameter sweep over the same 30 files (1,065 QC × 84 filter combinations against a 195-node
Watson/DJF template) was run to find the configuration reproducing these numbers. **It did not.**
Within its no-QC/no-filter condition — the reference's own ungated dataset — the closest fit was:

| Model | Requested | Serialized | Usable | Best distance to reference |
|---|---|---|---|---|
| Watson | 1,950 | 252 | 2 | 301.3 |
| DJF sync off | 1,950 | 195 | 10 | 157.6 |
| DJF sync on | 1,950 | 161 | 16 | 144.2 |

Distance sums absolute error in G1/S/G2 percent plus half the absolute error in each mean; 0 is exact.

The likely cause is now visible: that sweep imposes **fixed, sample-independent** constraint boxes
(0–1000, 100–350 and so on), while the reference used a **per-sample machine-generated window**
roughly ±18% around the detected peak. None of the sweep's 23 G1 ranges approximates 146.81–213.00.
The sweep additionally returns a usable fit for only 0.58% of requested models, with most results
degenerate (Gaussians pinned to constraint boundaries, `stddev="inf"`, negative S fractions).

**Do not treat that sweep's output as a FlowJo reference.** The workspaces in
`evidence/flowjo_reference_2026_09_23/` and the 30 spreadsheet rows are the trustworthy values.

## Provenance

- **Workspaces:** `evidence/flowjo_reference_2026_09_23/` — `djf_seed.wsp`, `watson_seed.wsp`,
  `cellcycle_seed.wsp`, `EngineInfo.xml`, `one_sample.txt`. Recovered from
  `Downloads\archivedwl-991\FlowJo_Seed\`, dated 2026-09-19. FlowJo 10.10.2.
- **Reference values:** `DJF Model_DataCompilation_Flojo_3_26_2026.xlsx` (`Async ALL DATA`) and
  `DJF Model v. Watson Model.xlsx`, dated 2026-04-02.
- **Event counts:** `$TOT` parsed from each FCS TEXT segment; 30/30 exact.
- **Caveat on scope:** the workspaces demonstrate the configuration on **one** sample (A6/`1468f`).
  That the remaining 29 were run identically is inferred from the 30/30 count reconciliation and
  the internal consistency of the published table, not separately demonstrated.
- **Caveat on origin:** these workspaces are dated 2026-09-19, months after the 2026-04-02
  spreadsheets. They reproduce the published values exactly, so they were produced under the same
  settings — but whether they *are* the original analysis or a faithful re-run is worth one
  confirmation from whoever created them.
- **Licensing note:** the audit records this dataset (`flowjo_async_djf`) as local-only and not
  redistributable. Resolve that before these values become load-bearing for a publication claim.

## Per-sample reference values

From `DJF Model_DataCompilation_Flojo_3_26_2026.xlsx`, sheet `Async ALL DATA`. Means in FL7-A
channel units; CVs as published.

| Strain | G1% | S% | G2% | G1 mean | G1 CV | G2 mean | G2 CV | G2:G1 |
|---|---|---|---|---|---|---|---|---|
| 191f | 0.160 | 0.266 | 0.477 | 169 | 9.35 | 343 | 9.49 | 2.030 |
| 191g | 0.156 | 0.263 | 0.495 | 167 | 8.11 | 338 | 8.79 | 2.024 |
| 191h | 0.159 | 0.247 | 0.510 | 172 | 8.55 | 344 | 9.19 | 2.000 |
| 191i | 0.191 | 0.270 | 0.468 | 169 | 8.92 | 341 | 9.09 | 2.018 |
| 191j | 0.211 | 0.256 | 0.463 | 174 | 9.93 | 348 | 9.30 | 2.000 |
| 1468f | 0.216 | 0.267 | 0.460 | 175 | 9.74 | 350 | 9.44 | 2.000 |
| 1468g | 0.203 | 0.231 | 0.502 | 173 | 9.88 | 350 | 10.40 | 2.023 |
| 1468h | 0.236 | 0.188 | 0.524 | 172 | 12.90 | 346 | 11.20 | 2.012 |
| 1468i | 0.202 | 0.235 | 0.511 | 172 | 11.80 | 355 | 10.60 | 2.064 |
| 1468j | 0.194 | 0.181 | 0.546 | 175 | 9.58 | 355 | 10.20 | 2.029 |
| 1691f | 0.174 | 0.262 | 0.492 | 169 | 7.38 | 339 | 7.57 | 2.006 |
| 1691g | 0.207 | 0.254 | 0.472 | 173 | 8.66 | 345 | 8.04 | 1.994 |
| 1691h | 0.163 | 0.244 | 0.524 | 171 | 8.44 | 344 | 8.27 | 2.012 |
| 1691i | 0.213 | 0.232 | 0.497 | 177 | 11.10 | 354 | 9.64 | 2.000 |
| 1691j | 0.136 | 0.309 | 0.453 | 167 | 7.38 | 338 | 8.16 | 2.024 |
| 1693f | 0.203 | 0.249 | 0.497 | 165 | 9.95 | 343 | 10.10 | 2.079 |
| 1693g | 0.101 | 0.368 | 0.464 | 151 | 7.73 | 340 | 13.80 | 2.252 |
| 1693h | 0.191 | 0.320 | 0.438 | 159 | 12.00 | 339 | 13.30 | 2.132 |
| 1693i | 0.196 | 0.378 | 0.371 | 158 | 11.00 | 333 | 12.20 | 2.108 |
| 1693j | 0.126 | 0.331 | 0.474 | 158 | 7.14 | 362 | 12.90 | 2.291 |
| 1981f | 0.176 | 0.266 | 0.476 | 171 | 8.75 | 340 | 8.53 | 1.988 |
| 1981g | 0.196 | 0.286 | 0.453 | 165 | 8.13 | 331 | 7.76 | 2.006 |
| 1981h | 0.221 | 0.245 | 0.460 | 171 | 10.60 | 340 | 8.90 | 1.988 |
| 1981i | 0.217 | 0.251 | 0.464 | 171 | 9.95 | 339 | 8.13 | 1.982 |
| 1981j | 0.202 | 0.256 | 0.450 | 170 | 9.46 | 339 | 8.48 | 1.994 |
| 1982f | 0.191 | 0.120 | 0.636 | 184 | 8.85 | 361 | 10.40 | 1.962 |
| 1982g | 0.190 | 0.124 | 0.633 | 183 | 7.86 | 355 | 9.19 | 1.940 |
| 1982h | 0.171 | 0.109 | 0.644 | 185 | 8.95 | 365 | 10.70 | 1.973 |
| 1982i | 0.170 | 0.116 | 0.662 | 186 | 8.99 | 365 | 10.70 | 1.962 |
| 1982j | 0.158 | 0.141 | 0.643 | 180 | 11.00 | 369 | 11.50 | 2.050 |

G1 CV range 7.14–12.90; G2 CV range 7.57–13.80.
