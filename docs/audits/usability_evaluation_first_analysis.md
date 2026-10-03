# Usability Evaluation: First-Analysis Walkthrough & Progress UI Review (DOC-04)

**Date:** 2026-09-08  
**Task:** DOC-04 (P3)  
**Agency Cross-References:** AUDIT-016, AUDIT-017, AUDIT-018  
**Author / Evaluator:** Gemini 3.8 Flash High  

---

## 1. Executive Summary

Agency audit findings AUDIT-016, AUDIT-017, and AUDIT-018 raised three related usability and onboarding concerns for PhaseFinder:
1. **AUDIT-016 (First-Analysis Tutorial):** Users transitioning from commercial tools (FlowJo, Flowreader) or novices running their first analysis lacked an end-to-end guided walkthrough with reproducible sample data, exact expected values, and realistic warning interpretation.
2. **AUDIT-017 (Task Completion Observation & Telemetry):** Evaluated whether remote telemetry or user task tracking should be introduced to measure onboarding completion rates.
3. **AUDIT-018 (Progress / Step Indicator UI):** Proposed introducing a horizontal progress/step indicator or wizard-style stepper UI to guide users through the workflow.

**Conclusions:**
- **AUDIT-016 is fully resolved:** A comprehensive 9-step reproducible tutorial has been created at [`help/help-first-analysis.html`](../../help/help-first-analysis.html), registered in `vite.config.js`, linked from the Help Index ([`help/index.html`](../../help/index.html)) and Getting Started guide ([`help/help-getting-started.html`](../../help/help-getting-started.html)), and validated with `scripts/check_documents.py`. It uses redistributable synthetic datasets ([`truth_clean_50_30_20.fcs`](../../tests/validation/validation_test_data/synthetic_fcs/files/truth_clean_50_30_20.fcs) and [`arrest_g1_95_04_01.fcs`](../../tests/validation/validation_test_data/synthetic_fcs/files/arrest_g1_95_04_01.fcs)) and provides verified reference values for all outputs.
- **AUDIT-017 Telemetry is rejected under privacy policy:** Remote telemetry, tracking pixels, or unconsented automated metrics violate PhaseFinder's strict local-first privacy policy ([`docs/release-and-privacy.md`](../release-and-privacy.md)). Any task completion studies must be conducted via local, consented, qualitative observation.
- **AUDIT-018 Progress UI is not recommended by current evidence:** A horizontal stepper/wizard UI introduces severe vertical screen compression on the histogram and aligned Pearson residual strip, while imposing a rigid linear paradigm on an inherently iterative, exploratory scientific modeling workflow. The existing 3-stage sidebar navigation, in-context tooltips, and new tutorial provide superior guidance without UI bloat.

---

## 2. Cognitive Walkthrough & Task Analysis

A cognitive walkthrough was conducted across the end-to-end cell-cycle modeling lifecycle to identify potential user drop-off points.

### 2.1 Evaluated Workflow Stages

| Stage | User Action | System Feedback | Evaluated Usability & Friction Points |
|---|---|---|---|
| **1. File Ingestion** | Drag & drop or file dialog selection of FCS files | File listed in Metadata Table; row checkbox auto-selected | **Low friction.** Drag-and-drop zone is prominent. Clear row count badge. |
| **2. Channel Selection & Plotting** | Choose DNA channel (e.g. `FL2-A`) and click `Plot Channel Events` | Histogram renders in main plot panel with bins and range controls | **Low friction.** Channel selector auto-detects common DNA/fluorescence channels. |
| **3. Pre-Modeling QC** | Review Time QC, Scatter QC, Pulse Geometry QC badges | Filter badges show event retention / exclusion percentages | **Moderate friction.** Users unfamiliar with flow QC needed clear documentation on why certain events were flagged. Addressed in tutorial section 3. |
| **4. Peak Identification** | Open `Cell Cycle Modeling` &rarr; `Identify Peaks` | Detected G1 and G2/M peaks marked with vertical dashed overlays and boundary spans | **Low friction.** Automatic peak detection reliably seeds initial positions; draggable or manual spin-box adjustments are responsive. |
| **5. Model Fitting** | Select algorithm (DJF, DJ, Watson Pragmatic/Classic, CLOCCS) and click `Fit Current` | Web worker executes non-linear fit; overlay curves render | **Low friction.** Status indicator and spinner inform user of worker execution without freezing UI thread. |
| **6. Residual Inspection** | Inspect aligned Pearson residual strip below histogram | Binned residuals $z = (O - E) / \sqrt{E}$ rendered with $\pm 2$ and $\pm 3$ threshold lines | **High value.** Residual strip provides direct visual proof of local fit quality (e.g. S-phase flatness, peak skewness). |
| **7. Warning Interpretation** | Inspect Warning Badges (ill-conditioned Jacobian, parameter pinning, restart divergence) | Color-coded badges in Results Table with detail tooltips | **Prior drop-off risk.** Commercial tools often hide optimizer failures. Users needed explicit instructions on what warnings mean and how to remediate them. Addressed in tutorial section 7. |
| **8. Export & Reporting** | Click `Download` &rarr; select SVG, PNG, JSON provenance, or CSV curves | Instant local download via Object URLs | **Low friction.** No server roundtrip required. Provenance is cryptographically self-contained. |
| **9. Session Save / Resume** | Click `Save` in header | Generates clean `.toml` session file | **Low friction.** Reloads identical state upon restore. |

### 2.2 Walkthrough Findings

The cognitive walkthrough confirmed that the core application UI functions smoothly once the user understands the sequential progression (Files &rarr; QC &rarr; Peaks &rarr; Model &rarr; Residuals &rarr; Export). However, without a dedicated tutorial:
- First-time users were unsure what reasonable G1/S/G2-M phase fractions should look like.
- Users did not know whether warnings (such as parameter pinning or restart disagreement) represented data defects or model specification issues.
- The distinction between Dean-Jett-Fox (polynomial S phase) and Watson (rectangular/truncated S phase) was theoretical rather than practical.

The creation of [`help/help-first-analysis.html`](../../help/help-first-analysis.html) directly resolves these walkthrough findings by providing concrete data, screenshot references, and exact mathematical benchmarks.

---

## 3. Evaluation of Proposed Progress / Step Indicator UI (AUDIT-018)

AUDIT-018 proposed adding a permanent horizontal progress stepper or wizard component (e.g. `[1. Load] -> [2. Gate] -> [3. Peaks] -> [4. Fit] -> [5. Export]`) to the top application header.

We evaluated this proposal against ergonomic, visual, and workflow criteria:

### 3.1 Vertical Screen Real Estate Constraints
- PhaseFinder is a desktop browser application designed to display dense scientific visualizations simultaneously:
  1. The primary DNA histogram with multi-component Gaussian/polynomial overlay curves.
  2. The vertically aligned Pearson residual strip ($z = (O - E) / \sqrt{E}$) directly below the histogram.
  3. The editable metadata and sample summary table below the plot.
- On standard 1080p laptop displays (1920x1080 CSS pixels with 1.25x or 1.5x OS scaling), vertical space is at a premium (typically 650–750 available vertical pixels in the browser viewport).
- Adding a persistent 50–70px horizontal stepper bar would compress the plot area, forcing either smaller histogram heights (reducing curve resolution) or hiding the residual strip behind a scrollbar. Preserving the vertical alignment between the histogram channels and the residual strip is essential for scientific integrity.

### 3.2 Non-Linear Scientific Workflow Mismatch
- A wizard or linear stepper is appropriate for unidirectional tasks (e.g. e-commerce checkout, account registration).
- Flow cytometry cell-cycle modeling is **iterative, non-linear exploratory analysis**:
  - A researcher fits a model, notices an elevated residual in the S-phase bridge, adjusts the peak bounds, and re-fits.
  - A researcher toggles between Dean-Jett-Fox and Watson Pragmatic to compare AIC/RMSD values.
  - A researcher applies a Time QC filter, re-evaluates peak CVs, and changes bin widths.
- Imposing a linear stepper implies that earlier stages are "locked" or "completed" and discourages active parameter refinement.

### 3.3 Adequacy of Existing Navigation Hierarchy
The current PhaseFinder interface already communicates workflow state clearly:
1. **Sidebar Organization:** The sidebar transitions cleanly between `File Selection` and `Cell Cycle Modeling`, with distinct collapsible sections for `Pre-modeling QC`, `Identify Peaks`, and `Model & Fit`.
2. **Status Channels & Status Bar:** The status bar at the bottom and the modeling status panel provide real-time updates on active operations, worker tasks, and completion states.
3. **Interactive Visual Feedback:** The histogram plot instantly reflects peak identification changes, curve fits, and residual recalculations.

### 3.4 Verdict on AUDIT-018
**No progress/step UI should be added.** The evidence does not warrant a new stepper component. The bundled walkthrough tutorial (`help/help-first-analysis.html`) provides the necessary guidance for first-time onboarding without compromising screen real estate or restricting scientific workflow flexibility.

---

## 4. Evaluation of Usability Study & Telemetry Policy (AUDIT-017)

AUDIT-017 discussed measuring task completion rates and user drop-off via automated telemetry or a formal usability trial.

### 4.1 Strict Local-First Privacy Mandate
- PhaseFinder adheres to strict privacy and data isolation policies ([`docs/release-and-privacy.md`](../release-and-privacy.md)).
- Flow cytometry data frequently contains sensitive clinical or proprietary research information.
- The application architecture guarantees that **zero network requests** are made during analysis: all FCS parsing, QC filtering, Levenberg-Marquardt optimization, and figure generation occur exclusively within the local browser runtime and local web workers.
- Shipping automated analytics SDKs (e.g. Google Analytics, Mixpanel, Sentry telemetry, or custom HTTP tracking beacons) is strictly rejected by project policy.

### 4.2 Consented Qualitative Study Protocol
If future usability testing with external researchers is conducted:
- Studies must be conducted **in-person or via consented screen-share sessions** using the bundled synthetic datasets (`truth_clean_50_30_20.fcs`).
- Observers should record time-to-first-fit, questions asked during peak review, and comprehension of warning badges using a qualitative think-aloud protocol.
- No software modifications or tracking code will be injected into PhaseFinder for this purpose.

---

## 5. Artifacts and Verification Summary

1. **First-Analysis Tutorial:**
   - Location: [`help/help-first-analysis.html`](../../help/help-first-analysis.html)
   - Scope: 9 complete steps from bundled synthetic file ingestion to session preservation.
   - Reference datasets:
     - Baseline benchmark: `tests/validation/validation_test_data/synthetic_fcs/files/truth_clean_50_30_20.fcs` (recovers 49.09% G1, 32.48% S, 18.43% G2/M with `objective_step_tolerance`).
     - Warning interpretation: `tests/validation/validation_test_data/synthetic_fcs/files/arrest_g1_95_04_01.fcs` (reproduces ill-conditioned Jacobian, parameter pinning, and multi-start disagreement).
2. **Integration:**
   - Bundled in production builds via Vite entry `vite.config.js`.
   - Linked in Help Center TOC grid ([`help/index.html`](../../help/index.html)), Quick Links, and Getting Started ([`help/help-getting-started.html`](../../help/help-getting-started.html)).
   - Navigational consistency verified across all 11 help topic sidebars.
3. **Automated Validation:**
   - `python3 scripts/check_documents.py`: 21 HTML pages, 28 active Markdown documents, Help UI labels, manifest, and tracker checks all passing (0 errors).
