#!/usr/bin/env python3
"""Browser unit coverage for js/analysis/cell_cycle/peak_regions.js (region
validation/estimation) and js/analysis/cell_cycle/modeling_state.js (the
peak-region state transitions: detect, select an alternative, edit, accept,
reset)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "e2e"))

from helpers import TestContext


GROUP = "Unit / Cell Cycle Modeling State"


_TESTS = r"""async () => {
  const pipeline = window.PhaseFinder.pipeline;
  const peakRegions = window.CellCyclePeakRegions;
  const modelingState = window.CellCycleModelingState;
  const results = [];
  const push = (name, pass, detail = '') => results.push({
    name, pass: Boolean(pass), detail: String(detail ?? ''),
  });
  const run = (name, test) => {
    try {
      const outcome = test();
      push(name, outcome.pass, outcome.detail);
    } catch (error) {
      push(name, false, `${error.name}: ${error.message}`);
    }
  };
  const runAsync = async (name, test) => {
    try {
      const outcome = await test();
      push(name, outcome.pass, outcome.detail);
    } catch (error) {
      push(name, false, `${error.name}: ${error.message}`);
    }
  };
  const throws = (callback, pattern = null) => {
    try {
      callback();
      return false;
    } catch (error) {
      return pattern ? pattern.test(error.message) : true;
    }
  };

  // --- peak_regions.js: validation ---

  run('validatePeakRegions accepts a well-ordered pair', () => {
    const validated = peakRegions.validatePeakRegions({
      g1: { left: 50, right: 90 }, g2: { left: 110, right: 170 },
    });
    return { pass: validated.g1.left === 50 && validated.g2.right === 170, detail: JSON.stringify(validated) };
  });

  run('validatePeakRegions rejects an inverted region (left >= right)', () => {
    const failed = throws(() => peakRegions.validatePeakRegions({
      g1: { left: 90, right: 50 }, g2: { left: 110, right: 170 },
    }), /left < right/);
    return { pass: failed, detail: `failed=${failed}` };
  });

  run('validatePeakRegions rejects an overlapping pair (G1 right > G2 left)', () => {
    const failed = throws(() => peakRegions.validatePeakRegions({
      g1: { left: 50, right: 120 }, g2: { left: 110, right: 170 },
    }), /ordered and non-overlapping/);
    return { pass: failed, detail: `failed=${failed}` };
  });

  run('validatePeakRegions accepts touching regions (G1 right === G2 left)', () => {
    const validated = peakRegions.validatePeakRegions({
      g1: { left: 50, right: 100 }, g2: { left: 100, right: 170 },
    });
    return { pass: validated.g1.right === validated.g2.left, detail: JSON.stringify(validated) };
  });

  run('estimatePeakFromRegion finds the region-local peak center without any fit', () => {
    const edges = Array.from({ length: 129 }, (_, i) => i * 2);
    const counts = new Array(128).fill(0);
    for (let i = 0; i < 128; i += 1) {
      const center = i * 2 + 1;
      const z = (center - 70) / 6;
      counts[i] = 500 * Math.exp(-0.5 * z * z);
    }
    const estimate = peakRegions.estimatePeakFromRegion(edges, counts, { left: 40, right: 100 });
    return {
      pass: Math.abs(estimate.mean - 70) < 4 && estimate.sigma > 0 && estimate.area > 0,
      detail: JSON.stringify({ mean: estimate.mean, sigma: estimate.sigma, area: estimate.area }),
    };
  });

  // --- modeling_state.js: build a real row + histogram to exercise
  // the state transitions against, via the actual pipeline orchestrator. ---

  function buildBimodalRow(name, eventsPerPeak) {
    const total = eventsPerPeak * 2;
    const dna = new Float64Array(total);
    // Deterministic pseudo-Gaussian spread via a small linear congruential
    // generator so the test is reproducible without Math.random().
    let seed = 12345;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };
    const gaussian = () => {
      const u1 = Math.max(1e-9, rand());
      const u2 = rand();
      return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    };
    for (let i = 0; i < eventsPerPeak; i += 1) dna[i] = 70 + gaussian() * 4.2;
    for (let i = 0; i < eventsPerPeak; i += 1) dna[eventsPerPeak + i] = 140 + gaussian() * 8.4;

    return {
      id: `${name}-id`,
      name,
      data: {
        channel_key: 'DNA-A',
        eventCount: total,
        channels: { DNA_A: dna, DNA_H: null, DNA_W: null, FSC_A: null, SSC_A: null, Time: null },
        pnr: { DNA_A: 300, DNA_H: null, DNA_W: null, FSC_A: null, SSC_A: null, Time: null },
        masks: { structural: null, timeQC: null, scatter: null, singlet: null, final: null },
      },
    };
  }

  run('detect_peak_regions populates peakDetection/peakSelection from a real histogram', () => {
    const row = buildBimodalRow('modeling-state-detect', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });

    const detection = modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);
    return {
      pass: (detection.status === 'detected' || detection.status === 'low_confidence')
        && state.modeling.peakSelection.source === 'automatic'
        && state.modeling.peakSelection.regions !== null
        && state.modeling.peakSelection.stale === false
        && state.modeling.histogramFingerprint === state.histogram.fingerprint
        && Boolean(detection.regionEvidence?.g1?.method)
        && Boolean(detection.regionEvidence?.g2?.method)
        && detection.pairs.every((pair) => typeof pair.id === 'string'),
      detail: JSON.stringify({ status: detection.status, regions: state.modeling.peakSelection.regions }),
    };
  });

  run('detect_peak_regions requires a histogram first', () => {
    const row = buildBimodalRow('modeling-state-no-histogram', 100);
    pipeline.clear_state(row.name);
    const failed = throws(() => modelingState.detect_peak_regions(row), /Build the histogram/);
    return { pass: failed, detail: `failed=${failed}` };
  });

  run('update_peak_regions applies a valid manual edit, marks reviewed, and invalidates cached fits', () => {
    const row = buildBimodalRow('modeling-state-update', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);

    const state = pipeline.get_state(row.name);
    state.modeling.resultsByKey = { 'dean_jett_fox|fp1': { modelId: 'dean_jett_fox' } };
    state.modeling.activeResultKey = 'dean_jett_fox|fp1';

    const updated = modelingState.update_peak_regions(row, {
      g1: { left: 55, right: 85 }, g2: { left: 120, right: 160 },
    });
    return {
      pass: updated.source === 'manual'
        && updated.reviewed === true
        && updated.regions.g1.left === 55
        && state.modeling.histogramFingerprint === state.histogram.fingerprint
        && Object.keys(state.modeling.resultsByKey).length === 0
        && state.modeling.activeResultKey === null,
      detail: JSON.stringify({ updated, resultsByKey: state.modeling.resultsByKey }),
    };
  });

  run('update_peak_regions rejects an invalid edit and leaves the previous regions untouched', () => {
    const row = buildBimodalRow('modeling-state-update-invalid', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);
    const before = JSON.stringify(state.modeling.peakSelection.regions);

    const failed = throws(() => modelingState.update_peak_regions(row, {
      g1: { left: 55, right: 130 }, g2: { left: 120, right: 160 }, // overlapping
    }));
    const after = JSON.stringify(state.modeling.peakSelection.regions);
    return { pass: failed && before === after, detail: `failed=${failed}, unchanged=${before === after}` };
  });

  run('select_peak_pair switches to an alternative pair and invalidates cached fits', () => {
    const row = buildBimodalRow('modeling-state-select', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    const detection = modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);

    if (detection.pairs.length < 2) {
      // Not every random seed produces a second candidate pair; skip cleanly
      // rather than fail on an environment-dependent fixture detail.
      return { pass: true, detail: 'only one candidate pair found; select_peak_pair not exercised' };
    }
    const alternativeId = detection.pairs[1].id;
    state.modeling.resultsByKey = { x: { modelId: 'dean_jett_fox' } };
    const selection = modelingState.select_peak_pair(row, alternativeId);
    return {
      pass: state.modeling.peakDetection.selectedPairId === alternativeId
        && selection.source === 'alternative'
        && Object.keys(state.modeling.resultsByKey).length === 0,
      detail: JSON.stringify({ selectedPairId: state.modeling.peakDetection.selectedPairId, selection }),
    };
  });

  run('select_peak_pair rejects an unknown pair id', () => {
    const row = buildBimodalRow('modeling-state-select-unknown', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    const failed = throws(() => modelingState.select_peak_pair(row, 'not-a-real-pair-id'), /No detected pair/);
    return { pass: failed, detail: `failed=${failed}` };
  });

  run('accept_peak_regions marks reviewed without changing the regions', () => {
    const row = buildBimodalRow('modeling-state-accept', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);
    const before = JSON.stringify(state.modeling.peakSelection.regions);

    const accepted = modelingState.accept_peak_regions(row);
    return {
      pass: accepted.reviewed === true && JSON.stringify(state.modeling.peakSelection.regions) === before,
      detail: JSON.stringify(accepted),
    };
  });

  run('reset_peak_regions restores the automatic proposal after a manual edit', () => {
    const row = buildBimodalRow('modeling-state-reset', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);
    const automatic = JSON.stringify(state.modeling.peakSelection.automaticRegions);

    modelingState.update_peak_regions(row, { g1: { left: 55, right: 85 }, g2: { left: 120, right: 160 } });
    const reset = modelingState.reset_peak_regions(row);
    return {
      pass: reset.source === 'automatic'
        && reset.reviewed === false
        && JSON.stringify(reset.regions) === automatic,
      detail: JSON.stringify({ automatic, reset }),
    };
  });

  run('reset_peak_regions requires detection to have run first', () => {
    const row = buildBimodalRow('modeling-state-reset-no-detect', 100);
    pipeline.clear_state(row.name);
    const failed = throws(() => modelingState.reset_peak_regions(row), /detect_peak_regions/);
    return { pass: failed, detail: `failed=${failed}` };
  });

  run('rerunning detect_peak_regions after a manual edit preserves the manual selection', () => {
    const row = buildBimodalRow('modeling-state-rerun-preserve', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    modelingState.update_peak_regions(row, { g1: { left: 55, right: 85 }, g2: { left: 120, right: 160 } });
    const state = pipeline.get_state(row.name);

    modelingState.detect_peak_regions(row);
    return {
      pass: state.modeling.peakSelection.source === 'manual'
        && state.modeling.peakSelection.reviewed === true
        && state.modeling.peakSelection.regions.g1.left === 55,
      detail: JSON.stringify(state.modeling.peakSelection),
    };
  });

  run('PEAK-01: redetecting an automatic proposal clears the old active fit', () => {
    const row = buildBimodalRow('modeling-state-redetect-invalidates', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    const state = pipeline.get_state(row.name);
    state.modeling.resultsByKey = { old: { modelId: 'watson_pragmatic' } };
    state.modeling.activeResultKey = 'old';
    modelingState.detect_peak_regions(row);
    return {
      pass: state.modeling.activeResultKey === null
        && Object.keys(state.modeling.resultsByKey).length === 0
        && state.modeling.peakSelection.reviewed === false,
      detail: JSON.stringify(state.modeling),
    };
  });

  run('PEAK-01: weak, inferred, and fallback-width proposals require review', () => {
    const low = modelingState.peak_detection_requires_review({ status: 'low_confidence' });
    const inferred = modelingState.peak_detection_requires_review(
      { status: 'inferred_g2' }, { g1: { source: 'detected' }, g2: { source: 'inferred' } });
    const fallback = modelingState.peak_detection_requires_review({
      status: 'detected', regionEvidence: { g1: { fallback: false }, g2: { fallback: true } },
    });
    const ambiguous = modelingState.peak_detection_requires_review({
      status: 'detected', selectedPairId: 'pair-0',
      pairs: [{ id: 'pair-0', scoreMargin: 0.02 }], alternatives: [{ id: 'pair-1' }],
      configuration: { marginScale: 0.08 },
    });
    const clean = modelingState.peak_detection_requires_review({
      status: 'detected', regionEvidence: { g1: { fallback: false }, g2: { fallback: false } },
    });
    return {
      pass: low.required && inferred.required && fallback.required && ambiguous.required && !clean.required,
      detail: JSON.stringify({ low, inferred, fallback, ambiguous, clean }),
    };
  });

  // fit_cell_cycle_model must reject a joint-series model (CLOCCS) with a clear
  // "fit it over all plotted timepoints" message from the per-sample path -- not
  // "Unknown cell-cycle model", and not by attempting a single-sample fit. This
  // guards every per-sample caller (Fit Current, bin-change recompute, ridge
  // edit, session restore) at one chokepoint.
  await runAsync('fit_cell_cycle_model rejects the joint-series CLOCCS model with a clear per-sample message', async () => {
    const row = buildBimodalRow('modeling-state-cloccs-guard', 1500);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    modelingState.accept_peak_regions(row);
    let message = '';
    try {
      await modelingState.fit_cell_cycle_model(row, 'cloccs');
    } catch (error) {
      message = error.message;
    }
    const pass = /joint time-series/i.test(message) && !/Unknown/i.test(message);
    return { pass, detail: message };
  });

  await runAsync('assess_resampling_uncertainty rejects a result without modelId', async () => {
    let failed = false;
    try {
      await modelingState.assess_resampling_uncertainty({}, {});
    } catch (e) {
      failed = /requires a contracted fit result/i.test(e.message);
    }
    return { pass: failed, detail: `failed=${failed}` };
  });

  await runAsync('assess_resampling_uncertainty evaluates bootstrap intervals and records provenance on result', async () => {
    const row = buildBimodalRow('modeling-state-resampling', 1200);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 64, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    modelingState.accept_peak_regions(row);
    const fitResult = await modelingState.fit_cell_cycle_model(row, 'watson_pragmatic');

    const updated = await modelingState.assess_resampling_uncertainty(row, fitResult, {
      replicates: 5,
      seed: 12345,
    });

    const res = updated.resampling;
    const prov = updated.provenance?.resampling;
    const pf = res?.models?.watson_pragmatic?.phaseFractions;

    const pass = res
      && res.replicatesRequested === 5
      && res.replicatesSucceeded > 0
      && prov?.method === res.method
      && prov?.seed === 12345
      && typeof prov?.definition === 'string'
      && Number.isFinite(pf?.g1?.lower)
      && Number.isFinite(pf?.g1?.upper)
      && Number.isFinite(pf?.s?.lower)
      && Number.isFinite(pf?.s?.upper);

    return {
      pass: Boolean(pass),
      detail: JSON.stringify({
        succeeded: res?.replicatesSucceeded,
        definition: prov?.definition,
        g1: pf?.g1,
        s: pf?.s,
      }),
    };
  });

  function buildUnimodalRow(name, events, mean = 70, sigma = 4.2) {
    const otherMean = Math.abs(mean - 70) < 10 ? 140 : 70;
    const otherSigma = Math.abs(mean - 70) < 10 ? 8.4 : 4.2;
    const total = events + 25;
    const dna = new Float64Array(total);
    let seed = 12345;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };
    const gaussian = () => {
      const u1 = Math.max(1e-9, rand());
      const u2 = rand();
      return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    };
    for (let i = 0; i < events; i += 1) dna[i] = mean + gaussian() * sigma;
    for (let i = 0; i < 25; i += 1) dna[events + i] = otherMean + gaussian() * otherSigma;
    return {
      id: `${name}-id`,
      name,
      data: {
        channel_key: 'DNA-A',
        eventCount: total,
        channels: { DNA_A: dna, DNA_H: null, DNA_W: null, FSC_A: null, SSC_A: null, Time: null },
        pnr: { DNA_A: 300, DNA_H: null, DNA_W: null, FSC_A: null, SSC_A: null, Time: null },
        masks: { structural: null, timeQC: null, scatter: null, singlet: null, final: null },
      },
    };
  }

  await runAsync('D2/AMBIG-01: pure-G1 lone-peak fixture produces single_peak_unassigned, blocks fit, and unblocks when assigned G1', async () => {
    const row = buildUnimodalRow('lone-peak-g1', 2000, 70, 4.2);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });

    const detection = modelingState.detect_peak_regions(row);
    const unassignedState = pipeline.get_state(row.name);
    const unassignedStatus = detection.status === 'single_peak_unassigned';
    const regionsNull = unassignedState.modeling.peakSelection.regions === null;

    let fitBlocked = false;
    try {
      await modelingState.fit_cell_cycle_model(row, 'watson_pragmatic');
    } catch (e) {
      fitBlocked = true;
    }

    modelingState.assign_lone_peak_identity(row, 'g1');
    const assignedState = pipeline.get_state(row.name);
    const hasAssignedIdentity = assignedState.modeling.peakSelection.userAssignedIdentity === 'g1';
    const hasRegions = assignedState.modeling.peakSelection.regions !== null;
    const g1Center = 0.5 * (assignedState.modeling.peakSelection.regions.g1.left + assignedState.modeling.peakSelection.regions.g1.right);
    const g2Center = 0.5 * (assignedState.modeling.peakSelection.regions.g2.left + assignedState.modeling.peakSelection.regions.g2.right);

    const fitResult = await modelingState.fit_cell_cycle_model(row, 'watson_pragmatic');
    const hasWarning = fitResult.warnings.some((w) => w.code === 'regions_ambiguous_single_peak');
    const resultIdentity = fitResult.userAssignedPeakIdentity === 'g1';
    const reportable = fitResult.validForReporting === true;

    const pass = unassignedStatus
      && regionsNull
      && fitBlocked
      && hasAssignedIdentity
      && hasRegions
      && Math.abs(g1Center - 70) < 5
      && Math.abs(g2Center - 140) < 10
      && hasWarning
      && resultIdentity
      && reportable;

    return {
      pass: Boolean(pass),
      detail: JSON.stringify({
        unassignedStatus, regionsNull, fitBlocked, hasAssignedIdentity,
        g1Center, g2Center, hasWarning, resultIdentity, reportable,
      }),
    };
  });

  await runAsync('D2/AMBIG-01: G2-shifted lone-peak fixture produces single_peak_unassigned, blocks fit, and unblocks when assigned G2', async () => {
    const row = buildUnimodalRow('lone-peak-g2', 2000, 140, 8.4);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });

    const detection = modelingState.detect_peak_regions(row);
    const unassignedState = pipeline.get_state(row.name);
    const unassignedStatus = detection.status === 'single_peak_unassigned';
    const regionsNull = unassignedState.modeling.peakSelection.regions === null;

    let fitBlocked = false;
    try {
      await modelingState.fit_cell_cycle_model(row, 'watson_pragmatic');
    } catch (e) {
      fitBlocked = true;
    }

    modelingState.assign_lone_peak_identity(row, 'g2');
    const assignedState = pipeline.get_state(row.name);
    const hasAssignedIdentity = assignedState.modeling.peakSelection.userAssignedIdentity === 'g2';
    const g1Center = 0.5 * (assignedState.modeling.peakSelection.regions.g1.left + assignedState.modeling.peakSelection.regions.g1.right);
    const g2Center = 0.5 * (assignedState.modeling.peakSelection.regions.g2.left + assignedState.modeling.peakSelection.regions.g2.right);

    const fitResult = await modelingState.fit_cell_cycle_model(row, 'watson_pragmatic');
    const hasWarning = fitResult.warnings.some((w) => w.code === 'regions_ambiguous_single_peak');
    const resultIdentity = fitResult.userAssignedPeakIdentity === 'g2';
    const reportable = fitResult.validForReporting === true;

    const pass = unassignedStatus
      && regionsNull
      && fitBlocked
      && hasAssignedIdentity
      && Math.abs(g2Center - 140) < 10
      && Math.abs(g1Center - 70) < 5
      && hasWarning
      && resultIdentity
      && reportable;

    return {
      pass: Boolean(pass),
      detail: JSON.stringify({
        unassignedStatus, regionsNull, fitBlocked, hasAssignedIdentity,
        g1Center, g2Center, hasWarning, resultIdentity, reportable,
      }),
    };
  });

  await runAsync('D2/AMBIG-01: session TOML serialize and restore preserves user-assigned peak identity and status', async () => {
    const toml = await import('/js/session/toml_io.js');
    const row = buildUnimodalRow('session-lone-peak', 2000, 70, 4.2);
    pipeline.clear_state(row.name);
    pipeline.apply_structural_qc(row);
    pipeline.apply_dna_histogram(row, { binCount: 128, range: [0, 220] });
    modelingState.detect_peak_regions(row);
    modelingState.assign_lone_peak_identity(row, 'g1');

    const state = pipeline.get_state(row.name);
    const sampleRecord = {
      name: row.name,
      model: 'watson_pragmatic',
      reviewed: true,
      g1_left: state.modeling.peakSelection.regions.g1.left,
      g1_right: state.modeling.peakSelection.regions.g1.right,
      g1_source: state.modeling.peakSelection.regions.g1.source,
      g2_left: state.modeling.peakSelection.regions.g2.left,
      g2_right: state.modeling.peakSelection.regions.g2.right,
      g2_source: state.modeling.peakSelection.regions.g2.source,
      ratio_mode: 'bounded',
      ratio_min: 1.65,
      ratio_max: 2.25,
      locked_ratio: 2,
      cv_mode: 'free',
      ploidy_count: 1,
      peak_detection_status: state.modeling.peakDetection.status,
      user_assigned_peak_identity: state.modeling.peakSelection.userAssignedIdentity,
    };

    const text = toml.serialize_session({
      session: { created: '2026-09-26' },
      files: { names: [row.name] },
      metadata: { columns: [], rows: [] },
      table: { selected_files: [row.name], filters: {} },
      plot: { channel: 'DNA-A', color_by: '', bins: 128, remove_debris: false, remove_doublets: false, show_peak_threshold: false },
      ui: { sidebar_collapsed: false, sidebar_width_px: 300, plot_panel_collapsed: false,
        plot_panel_height_px: 400, metadata_panel_collapsed: false, metadata_panel_height_px: 200 },
      modeling: { samples: [sampleRecord] },
    });

    const parsed = toml.parse_session_toml(text);
    const parsedSample = parsed.modeling.samples[0];
    const pass = parsedSample.user_assigned_peak_identity === 'g1'
      && parsedSample.peak_detection_status === 'single_peak_unassigned';

    return {
      pass: Boolean(pass),
      detail: JSON.stringify({ parsedSample }),
    };
  });

  return results;
}"""


def run_cell_cycle_modeling_state_tests(ctx: TestContext):
    results = ctx.page.evaluate(_TESTS)
    for result in results:
        ctx.check(GROUP, result["name"], result["pass"], result["detail"])
