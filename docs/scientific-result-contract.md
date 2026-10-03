# Scientific result contract

A fitted curve is not, by itself, an authoritative scientific result. Every
per-sample fit routed through `fit_cell_cycle_model()` receives the following
independent fields from `result_contract.js`:

- `computed`: numerical work completed rather than being cancelled.
- `optimizerConverged`: `true`/`false` for optimized models and `null` when no
  optimizer exists (Watson's closed-form decomposition).
- `scientificallyValid`: expected counts, diagnostics and phase fractions are finite
  and coherent, an optimizer (when present) converged, no peak has degenerated
  at its upper CV bound, and no critical/error/nonreportable quality warning exists.
  This is a numerical/diagnostic verdict, not independent scientific validation.
- `limitedReliability`: nonconvergence or a material quality warning is present.
- `validForReporting`: coherent finite numbers are available for qualified
  display after the fit entry point has passed input preflight; the domain audit
  may still disallow publication when coverage is invalid.
- `cancelled`: the caller cancelled the operation.
- `invalid`: the logical inverse of an acceptable input/result combination.
- `validityReasons`: structured `{code, message, detail}` evidence.

Only a result with `validForReporting === true` may become
`modeling.activeResultKey`, and the canonical accessor also requires the current
contract version (2). Cancelled, non-finite, invalid-fraction and invalid-domain
results remain diagnostic-only. Nonconvergence and reliability warnings do not
hide coherent numbers: table/sidebar/TSV/report percentages carry a warning
marker and plot descriptions carry the shared textual caveat. Informational
notes alone do not qualify percentages. The producer’s `nonreportable` flag is
preserved as a stricter scientific/uncertainty warning; it does not override the
application’s explicit policy permitting qualified numerical display.

`result_reporting_summary()` calls these results “Reportable with warnings.”
Warning severity and `nonreportable` survive model normalization and JSON
export. Version 1.1 exports use the canonical histogram/component counts and
snapshot accepted regions and applied settings. CSV appends `qualification` and
`warnings` columns to each bin row; residuals are observed minus fitted counts.
Actual TOML refitting reproduces JSON/CSV and report/plot percentages in the
SCI-05 regression. Broader implementation-identity tracking remains STATE-02.

The result key includes the model/version, canonical applied configuration,
DNA-content digest, row and channel identity, all QC masks, histogram
edges/counts, peak-region revision/review state, and fit domain. Changing a
stored model setting deactivates the current result immediately; the exact
configuration sent to the model is retained as `appliedConfiguration`.

## Input preflight and QC provenance

The shared preflight binds a fit to the histogram fingerprint and peak-region
revision, requires reviewed/non-stale regions and eligible finite DNA data,
checks retained event sufficiency, and records structural, time, scatter, and
singlet QC as one of `not_run`, `unavailable`, `failed`, `waived`, or `passed`.
A waiver must be supplied explicitly and is retained verbatim in the result's
preflight provenance; it never turns a failed QC outcome into a pass.

Model configuration must be an object. Model-specific constraint validation
continues to be performed by each registered model before numerical fitting;
moving those validators behind the common preflight is still outstanding.

## Peak and S-phase plausibility warnings (GATE-03)

These checks qualify a fit; they do not establish its true phase fractions.
`regions_ploidy_mismatch` warns when fitted G1 lies more than 1.5 times above
the lowest substantial detected peak. A candidate is substantial when its
prominence is at least 25% of the maximum and its detector quality is at least
75% of the maximum; the quality requirement avoids treating a narrow sub-G1
debris spike as G1. `regions_possible_doublet` retains the detector's
`POSSIBLE_G2_4N_DOUBLET_REVIEW_PEAKS` warning after a human accepts the lower
pair. Both remain material warnings even if the fitted means are plausible.

`s_phase_collapse` warns when fitted S is below 1%, at least 2% of observed
events lie in the central 30–70% of the interval between fitted peak means,
and those observed counts exceed the fitted S component there by more than
fivefold. This central interval avoids testing the peak centers themselves.
The rule is a conservative plausibility flag for visibly occupied inter-peak
bins, not a replacement for a calibrated Watson fit. Missing histogram or
component counts leave the check unevaluated rather than inventing evidence.
Optimizer weak-identification warnings use the last evaluated Jacobian condition;
the worst condition seen during early iterations remains in diagnostics but
does not by itself describe the fitted optimum.

The FlowJo comparison checks phase fractions and peak means, not histogram
shape. In the 2026-09-23 358-fit snapshot, 54 DJF fits met all reference
tolerances and all 54 still carried `limitedReliability`. For example, three
No-QC reference-tolerance fits (`1982f`, `1982h`, `1982i`) had reduced
deviance 645.4, 1365.5 and 665.8, respectively. Overdispersion and
structured-residual warnings remain material at those values; reference
agreement alone is not evidence that their fitted curves explain the events.
In a 2026-09-24 No-QC rerun, all 45 available DJF/Watson fits emitted
`weak_optimizer_identifiability`, `overdispersed_fit`,
`residual_autocorrelation` and `residual_runs` as warnings. Reduced deviance
ranged from 494.1 to 4940.8 for DJF (median 1294.5) and 96.3 to 236.2 for
Watson (median 172.7), far beyond the existing threshold of 2.

## Pulse-geometry and scatter-gate operating envelopes (QC-CAL-01)

No real, independently-labelled acquisition data exists in this project against
which the singlet (`gateByPulseGeometry`, QC-06) and main-biological-cloud
(`gateMainBiologicalCloud`, QC-05) gates could be calibrated. A synthetic,
honestly-labelled fixture corpus was built instead
(`tests/validation/validation_test_data/synthetic_fcs/generate_qc_calibration_fixtures.py`,
verified against the real detectors by `verify_qc_calibration_fixtures.mjs`) to at
least characterize how the existing, uncalibrated default thresholds actually
behave. Two operating-envelope limits came out of that exercise as genuine
detector-behavior findings, not fixture artifacts, confirmed by reading the
gates' own source rather than inferred from the numbers alone:

- **`gateByPulseGeometry` degrades once doublets exceed roughly 8-10% of
  events.** Recall holds near 1.0 below that point and falls off progressively
  above it (~0.62 at 10%, ~0.55 at 12%, ~0.49 at 15%, ~0.09-0.12 by 35% in the
  synthetic sweep). This matches `fitRobustRidge2D`'s own documented design
  assumption (`js/analysis/gating/pulse_geometry_gate.js`) that off-ridge
  doublets/aggregates are a **minority** population; a sample with a heavier
  doublet burden than that is outside the gate's designed operating range, not
  merely harder for it.
- **`gateMainBiologicalCloud` selects its "main" component purely by
  population weight** (`selectionScore = quality.weight + 1e-6*mean[0]` in
  `js/analysis/gating/scatter_gmm_gate.js`), with scatter position only a
  negligible tie-break. Once a contaminant (e.g. debris) exceeds ~50% of
  events, the gate selects the contaminant as "main" and rejects the true
  biological population instead — an inversion, not a degraded pass rate. This
  is now a locked-in regression assertion in the synthetic corpus rather than
  a hedge, so a future change to the selection rule (a fix or a regression) is
  caught rather than silently passing.

Neither finding changed a threshold constant; they characterize the existing
defaults. Real calibration of these thresholds still needs the same two things
QC-CAL-01 was already blocked on: real labelled acquisitions, and a predefined
acceptable false-positive/detection/retention rate policy.

## Session and API behavior

UI fits, bulk fits, bin-change refits, ridge edits, and session restoration all
call `fit_cell_cycle_model()`, so they share the same checks. Calling a model
module's low-level `fit()` function directly produces a raw diagnostic object,
not an authoritative result, and cannot populate application state.

## G2:G1 mean ratio — do not tune toward the FlowJo reference (MODEL-01)

`g2_mean` sits below the 30-sample FlowJo reference on every sample (median
−3.2%). Decomposing the error shows it is **two independent components**, and
only one of them is a defect in this codebase:

```
reference g2:g1 ratio   median 2.0088   (Q1 1.9927 .. Q3 2.0347)
our fitted ratio        median 1.9766           -> ratio deficit  -1.55%
observed g2_mean error  -3.19%
        g1_mean error   -1.61%
        ratio error     -1.55%
              sum       -3.15%    <- matches observed
```

(Re-derived 2026-08-19 on all 30 samples with MODEL-03 and MODEL-04 in place;
the identity is unchanged from the 2026-08-14 measurement.)

The ratio component (our 1.9766 vs. reference ~2.0088) is **not treated as
error and must not be tuned away**. Chromatin condenses during G2/M, which
restricts intercalating-dye accessibility, so G2/M DNA content genuinely
fluoresces at slightly less than twice the G1 signal — a documented,
biologically real cause of a true peak ratio below 2.0 (Darzynkiewicz et al.,
<https://pmc.ncbi.nlm.nih.gov/articles/PMC2967208/>). Our free (unconstrained)
fit lands almost exactly where that mechanism predicts. FlowJo's reference
values cluster tightly around 2.0 (not hard-locked: the observed range is
1.94-2.29) because FlowJo's cell-cycle platform supports *constraining* the
mean-peak ratio during fitting
(<https://docs.flowjo.com/flowjo/experiment-based-platforms/cell-cycle-univariate/>)
and every stored reference mean is an integer, adding its own quantization
(~0.29% on G1).

In other words: the reference values look like they came from a
ratio-constrained fit against integer-rounded peak channels, and our
unconstrained fit reproduces the underlying biology instead of that
convention. Pulling `g2_mean` toward the reference would trade a correct,
mechanistically-grounded free fit for agreement with a different, more
constrained fitting convention — it would not make the estimate more
accurate. **If a future maintainer sees this as a fit-quality gap, the fix
is not to bias `g2_mean` toward 2x G1.** The remaining component is the G1
offset described in the next section, which propagates unchanged into
`g2_mean`. See `docs/audits/master_checklist.md` (MODEL-01, MODEL-02) for
the live investigation and status.

One further piece of evidence, added 2026-08-19: the same ratio deficit
(-1.48%) appears in the **modes of the fit-free gated histograms**, with no
model, no optimizer and no peak estimator involved. The deficit therefore
cannot be an artifact of how we fit; it is in the stained cells.

## G1 mean sits ~1.6% low, and it is a width difference (MODEL-02)

`g1_mean` sits below the same 30-sample FlowJo reference on essentially
every sample (median -1.61%). This is well inside the +-3% validation
tolerance, but it is systematic, and because MODEL-01 shows it propagates
into `g2_mean` at full strength it is worth stating precisely what it is.

**It is not a location error, and not a binning or range effect.** Measured
by re-running all 30 samples through the application's own modules:

* The **mode of the gated histogram** -- a fit-free statistic, computed in a
  window centred on the reference so it cannot depend on our peak detector
  -- is already -1.66% low. The fitted mean is -1.61%. The estimator
  contributes ~0.05 pp of the 1.6%.
* Holding **bin width** constant while growing the histogram range by 50%
  moves `g1Mean` by 0.014 channels. Sweeping bin count 128 -> 2048 leaves
  the offset flat at ~-1.2 channels. The offset is constant in channel
  units and does not scale with the range, so the structural `$PnR`
  saturation ceiling is not the cause.
* Structural QC does not create the offset; it reveals it. Without QC the
  median error is +0.55% but the spread is -3.6%..+4.9% with two >90%
  detector failures. With structural QC the median is -1.61% and the spread
  is -2.2%..+0.5%. QC removes the junk that was masking a consistent
  underlying difference and tightens the spread ~8x.

**What differs is peak width.** FlowJo reports G1 CVs about 1.47x ours
(median 9.17 vs 6.20; against a fit-free FWHM-derived CV of 6.98 it is
still 1.31x), and real G1 peaks in this set are right-skewed -- median
right-arm/left-arm ratio 1.321 at half maximum. A wider Gaussian fitted to
a right-skewed peak is pulled up the heavy side and necessarily centres
higher than a narrower one.

Confirmed by pinning it: refitting each G1 peak with free amplitude, free
mean and **sigma pinned** -- first at our fitted CV, then at FlowJo's
reported CV, with nothing else changed -- moves the median error from
-0.97% to **-0.09%**, closing ~74% of the gap on width alone. The two
samples whose fit already sits *above* the reference (`1468i`, `1693i`) are
exactly the two peaks that are not right-skewed.

**Do not widen sigma to close this.** Which width is correct is not
established: our sigma may be too small (residual over-deconvolution from
MODEL-03, or a smoothing/pedestal artifact) or FlowJo's may be too large
(its own smoothing, or a Gaussian absorbing skew the real peak genuinely
has). Tuning sigma toward the reference before that is answered would be
the MODEL-01 mistake moved one step earlier in the chain. Until it is
settled, the ~1.6% G1 offset is **characterised and expected**, not a
defect, and is reported as such rather than closed numerically.

Practical consequence for users comparing against FlowJo: peak *channels*
run ~1.6% low at G1 and ~3.2% low at G2. Phase *fractions* are far less
affected, because both peaks move in the same direction.

## G1/S fraction difference against FlowJo (MODEL-11)

On 30 No-QC samples, PhaseFinder's DJF G1 fraction is a median 3.775 percentage
points above FlowJo's fractions rescaled to 100%, while S is 4.040 points below.
This difference is not explained by PhaseFinder assigning FlowJo's unassigned
cells to the left tail of G1. Using each sample's FlowJo G1 mean minus 2.5
FlowJo standard deviations as the left-foot cutoff, the fitted PhaseFinder G1
Gaussian below it is a median 0.035% of biological area (maximum 0.841%).
FlowJo's unassigned share is a median 6.75% (range 5.1–10.2%); the two shares
have Pearson correlation −0.10 across the 30 samples. The per-sample values
remain in the local-only `model11_left_foot_analysis_20260924.json` beside the
private FlowJo reference.

As a sensitivity check, a DJF refit starting at the next histogram edge above
that left foot changed the median G1 difference from +3.775 to +3.160 points
and the S difference from −4.040 to −2.406 points. It improved absolute G1
error on 12/30 samples and S error on 15/30, while 12/30 cropped refits did
not converge (the original fits all converged). This diagnostic is not a safe
fit-range default. It also changes both the data range and the peak-flank
estimate, so it cannot by itself identify which part of the G1/S boundary
causes the remaining difference. The FlowJo unassigned population and its
pre-fit gates are still undocumented (VALID-02/VALID-03); no phase-width or
S-profile tuning was made from this comparison.

## Validated scope, unsupported inputs, and remaining differences (VALID-01 box 8)

This section is the index, not a restatement — each claim below links to the
document or test that is the actual evidence. It exists because the pieces
were previously scattered across separate audits with no single place that
says, plainly, what "validated" does and does not mean for this codebase
today.

**What has been checked, and against what:**

- FlowJo agreement on peaks/fractions/means/CVs/ratio: one dataset, 30
  asynchronous yeast samples, single instrument and encoding
  (`../test_flow_data/Asynchronous_UsedAsFloJoDFJSampleDataset/`, outside the
  repo). See the two sections above (MODEL-01, MODEL-02) for the measured
  differences and why the ratio gap is not tuned away. Deviance, model
  choice, and QC-mask agreement are **not** checked against FlowJo — FlowJo
  does not report them.
- Optimizer conditioning: DJF's dimensionless parameterization vs. the
  engine's own no-transform fallback, 30 synthetic known-truth fixtures,
  convergence 30/30 vs 16/30 (`docs/audits/master_checklist.md`, SCI-07).
- DJ/DJF component-level equivalence: G1/S/G2 curves, not just combined
  totals, over a parameter grid — not only the FlowJo-comparison dataset
  (`docs/audits/master_checklist.md`, VALID-01 box 2;
  `tests/unit/driving_code/unit_tests_cell_cycle_dean_jett_fox.py`).
- Interval coverage under resampling: 12 method/perturbation combinations x
  60 known-truth datasets x 80 replicates. `watson_classic` holds nominal
  coverage near nominal on clean/low-count/weak-S, but boundary S coverage
  is 88.3%; `dean_jett` also under-covers on difficult peaks. On contaminated
  data, **G1/G2 coverage falls to 0–13.3%**; S coverage is 13.3% for
  Watson Classic and 78.3% for Dean–Jett. Wider perturbations do not repair
  the underlying model bias
  (`docs/audits/master_checklist.md`, UNC-01).
- File-format-level input support (versions, datatypes, byte orders,
  transform/compensation policy, allocation limits) is its own matrix, not
  restated here: [`fcs-analysis-compatibility.md`](./fcs-analysis-compatibility.md)
  and [`fcs-compatibility.json`](./fcs-compatibility.json).

**What has not been checked, stated plainly rather than left implicit:**

- Redistributable MACSQuant parser, Rodighiero fluorescence/negative-control,
  and Amouzgar CyTOF fixtures provide instrument and encoding diversity
  (`docs/audits/master_checklist.md`, VALID-01). They do not establish
  matched multi-instrument cell-cycle truth or calibrated real QC masks.
  The 30-sample FlowJo agreement figures remain specific to that reference.
- Bootstrap/perturbation resampling is implemented and has simulation
  coverage evidence under UNC-01. Independent biological interval coverage
  and profile-likelihood comparison have not been established.
- No domain-expert (cytometry/oncology) review has been performed. Nothing
  in this codebase or its docs should be described as "validated," clinical,
  diagnostic, or publication-grade until one has (VALID-01 box 9) — that
  review cannot be produced by an AI working alone, the same limit that
  applies to the previous box.
- CLOCCS (`js/analysis/cell_cycle/models/cloccs.js`) is labelled
  `"CLOCCS (Unverified)"` in its own model metadata and is excluded from
  AIC/BIC selection against DJ/DJF/Watson; nothing above should be read as
  covering it.
- Watson Pragmatic's residual S-phase component (§5.5) is a data residual,
  not a parameterized density, and is therefore never AIC/BIC-ranked against
  DJ/DJF; it is also structurally exempt from the multistart/identifiability
  diagnostics in `uncertainty.js` because it never runs the iterative
  optimizer those diagnostics read from (`docs/audits/master_checklist.md`,
  VALID-01 box 7).

**Remaining known differences from FlowJo**, for a user reading a result
side-by-side with a FlowJo report: peak channels run ~1.6% low at G1 and
~3.2% low at G2 (characterised above, not a defect); phase fractions are far
less affected since both peaks move the same direction; deviance, model
choice, and QC-mask decisions have no FlowJo equivalent to compare against at
all.


### Session detection provenance

Modeling records persist `peak_detection_status` alongside reviewed regions and `model_version`. Restore attaches the detection status before preflight/refitting, so accepting an inferred G2 does not erase the single-peak assumption after reload. Saved status has no saved heuristic score; the review panel omits that score rather than inventing zero. Older sessions lacking detection status cannot recover that lost provenance.

`scatter_gates` contains manual gate inputs and is reapplied. `singlet_gates` is a diagnostic snapshot of the fitted pulse-geometry transform, identification ratio and review flag, not editable gate settings. The session caller reruns the selected QC filters; singlet geometry is derived again from events by `gateByPulseGeometry`. Stored diagnostic coordinates are not reapplied. Model-version persistence is now explicit in TOML; a matching model version alone still does not prove identical analysis implementation (STATE-02).
