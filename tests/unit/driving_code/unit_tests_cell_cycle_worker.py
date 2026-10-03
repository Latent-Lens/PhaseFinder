#!/usr/bin/env python3
"""Browser unit coverage for js/analysis/cell_cycle/fit_worker.js and
fit_client.js -- the worker actually runs in a real browser Worker, not a
mock, so this exercises the genuine postMessage round trip.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "e2e"))

from helpers import TestContext


GROUP = "Unit / Cell Cycle Worker"


_TESTS = r"""() => {
  const registry = window.CellCycleModelRegistry;
  const results = [];
  const push = (name, pass, detail = '') => results.push({
    name, pass: Boolean(pass), detail: String(detail ?? ''),
  });
  const runAsync = async (name, test) => {
    try {
      const outcome = await test();
      push(name, outcome.pass, outcome.detail);
    } catch (error) {
      push(name, false, `${error.name}: ${error.message}`);
    }
  };

  return (async () => {
    const { peakComponents, convolvedSPhase } = window.CellCycleModelShared;
    const TRUE = {
      g1Area: 8000, g1Mean: 70, g1CV: 0.06,
      g2Area: 3000, g2Mean: 140, g2CV: 0.07,
      sArea: 4000, shape1: 0.5, shape2: -0.3,
    };
    // Canonical {edges, counts} fixture: every canonical model requires
    // peakRegions, so the worker suite drives dean_jett the way the app does.
    const buildHistogram = (bins) => {
      const width = 300 / bins;
      const edges = Array.from({ length: bins + 1 }, (_, i) => i * width);
      const peaks = peakComponents(edges, TRUE);
      const sCounts = convolvedSPhase(edges, {
        sArea: TRUE.sArea, g1Mean: TRUE.g1Mean, g2Mean: TRUE.g2Mean,
        broadeningCV: TRUE.g1CV, shape1: TRUE.shape1, shape2: TRUE.shape2,
      }, 64);
      const counts = peaks.g1.map((value, i) => Math.round(value + sCounts[i] + peaks.g2[i]));
      return { edges, counts };
    };
    const histogram = buildHistogram(256);
    const regions = { g1: { left: 55, right: 85 }, g2: { left: 120, right: 165 } };
    const fitOptions = { peakRegions: regions };

    await runAsync('PERF-01: parameter-independent bin geometry is cached per histogram', async () => {
      const first = window.CellCycleGaussianBinMass.cached_bin_geometry(histogram.edges);
      const second = window.CellCycleGaussianBinMass.cached_bin_geometry(histogram.edges);
      return {
        pass: first === second && first.left.length === 256 && first.right[0] === histogram.edges[1]
          && first.left[255] === histogram.edges[255],
        detail: JSON.stringify({ bins: first.left.length, sameObject: first === second }),
      };
    });

    await runAsync('fit worker: a real fit matches the main-thread result within tolerance', async () => {
      registry.clear_registry();
      registry.register_default_models();
      const entry = registry.get_model('dean_jett');
      const mainThread = entry.normalizeResult(
        entry.fit({ histogram, peakRegions: regions, config: {} })
      );

      const { promise } = window.run_fit_in_worker('dean_jett', histogram, {}, fitOptions);
      const worker = await promise;

      const closeEnough = (a, b, tol) => Math.abs(a - b) <= tol;
      return {
        pass: worker.modelId === 'dean_jett'
          && worker.converged === mainThread.converged
          && closeEnough(worker.parameters.g1Mean, mainThread.parameters.g1Mean, 1e-6)
          && closeEnough(worker.parameters.g2Mean, mainThread.parameters.g2Mean, 1e-6)
          && worker.expectedCounts.length === mainThread.expectedCounts.length
          && worker.expectedCounts.every((value, i) => closeEnough(value, mainThread.expectedCounts[i], 1e-10))
          && Object.keys(worker.parameters).every(key => closeEnough(worker.parameters[key], mainThread.parameters[key], 1e-10))
          && ['g1', 's', 'g2'].every(key => closeEnough(worker.phaseFractions[key], mainThread.phaseFractions[key], 1e-10))
          && closeEnough(worker.diagnostics.deviance, mainThread.diagnostics.deviance, 1e-10)
          && worker.components.map((c) => c.id).join(',') === mainThread.components.map((c) => c.id).join(','),
        detail: JSON.stringify({
          workerG1: worker.parameters.g1Mean, mainG1: mainThread.parameters.g1Mean,
          workerG2: worker.parameters.g2Mean, mainG2: mainThread.parameters.g2Mean,
        }),
      };
    });

    await runAsync('fit worker: onProgress fires during a real worker fit', async () => {
      const events = [];
      const { promise } = window.run_fit_in_worker('dean_jett', histogram, {}, {
        ...fitOptions,
        onProgress: (event) => events.push(event),
      });
      await promise;
      return {
        pass: events.length > 0
          && events.every((event) => Number.isFinite(event.iteration) && Number.isFinite(event.sse)),
        detail: JSON.stringify(events),
      };
    });

    await runAsync('fit worker: an unknown model id rejects with a clear error', async () => {
      const { promise } = window.run_fit_in_worker('not-a-real-model', histogram, {}, {});
      try {
        await promise;
        return { pass: false, detail: 'expected the promise to reject' };
      } catch (error) {
        return { pass: /Unknown model/.test(error.message), detail: error.message };
      }
    });

    await runAsync('MAINT-01: fit worker rejects incompatible protocol versions deterministically', async () => {
      const worker = new Worker(new URL('/js/analysis/cell_cycle/fit_worker.js', location.origin), { type: 'module' });
      try {
        const response = await new Promise((resolve, reject) => {
          const timer = setTimeout(() => reject(new Error('worker timeout')), 3000);
          worker.onmessage = (event) => { clearTimeout(timer); resolve(event.data); };
          worker.onerror = (event) => { clearTimeout(timer); reject(new Error(event.message)); };
          worker.postMessage({ protocolVersion: 999, type: 'fit', request_id: 17 });
        });
        return {
          pass: response.protocolVersion === 1 && response.type === 'result'
            && response.ok === false && response.code === 'WORKER_PROTOCOL_MISMATCH',
          detail: JSON.stringify(response),
        };
      } finally { worker.terminate(); }
    });

    await runAsync('fit worker: concurrent requests are routed back to the correct caller by request id', async () => {
      const narrowHistogram = buildHistogram(64);
      const wideHistogram = buildHistogram(512);
      const a = window.run_fit_in_worker('dean_jett', narrowHistogram, {}, fitOptions);
      const b = window.run_fit_in_worker('dean_jett', wideHistogram, {}, fitOptions);
      const [resultA, resultB] = await Promise.all([a.promise, b.promise]);
      return {
        pass: resultA.expectedCounts.length === 64 && resultB.expectedCounts.length === 512,
        detail: JSON.stringify({ a: resultA.expectedCounts.length, b: resultB.expectedCounts.length }),
      };
    });

    await runAsync('PERF-01: cancellation terminates active work promptly and a subsequent fit succeeds', async () => {
      let cancelAt = null;
      let ticks = 0;
      const timer = setInterval(() => ticks++, 1);
      const handle = window.run_fit_in_worker('dean_jett', histogram, {}, {
        ...fitOptions, onProgress: () => {
          if (cancelAt === null) { cancelAt = performance.now(); handle.cancel(); }
        },
      });
      let caught;
      try { await handle.promise; } catch (error) { caught = error; }
      const latency = performance.now() - cancelAt;
      clearInterval(timer);
      const next = await window.run_fit_in_worker('dean_jett', histogram, {}, fitOptions).promise;
      return { pass: caught?.code === 'FIT_CANCELLED' && cancelAt !== null
        && latency < 250 && ticks > 0 && next.modelId === 'dean_jett',
        detail: JSON.stringify({ latencyMs: latency, uiTicks: ticks, code: caught?.code }) };
    });

    await runAsync('PERF-01: unavailable workers reject instead of fitting on the UI thread', async () => {
      const NativeWorker = window.Worker;
      try {
        window.Worker = class { constructor() { throw new Error('unavailable'); } };
        // Fresh module has no previously created idle workers.
        const client = await import('/js/analysis/cell_cycle/fit_client.js?unavailable-test');
        let caught;
        try { await client.run_fit_in_worker('dean_jett', histogram, {}, fitOptions).promise; }
        catch (error) { caught = error; }
        return { pass: caught?.code === 'FIT_WORKER_UNAVAILABLE', detail: caught?.message };
      } finally { window.Worker = NativeWorker; }
    });

    await runAsync('PERF-01: queued cancellation, worker failure and recovery are isolated', async () => {
      const NativeWorker = window.Worker;
      const descriptor = Object.getOwnPropertyDescriptor(navigator, 'hardwareConcurrency');
      const workers = [];
      class HeldWorker {
        constructor() { this.listeners = {}; this.terminated = false; workers.push(this); }
        addEventListener(type, callback) { this.listeners[type] = callback; }
        postMessage(message) { this.message = message; }
        terminate() { this.terminated = true; }
      }
      try {
        Object.defineProperty(navigator, 'hardwareConcurrency', { value: 2, configurable: true });
        window.Worker = HeldWorker;
        const client = await import('/js/analysis/cell_cycle/fit_client.js?queue-test');
        const a = client.run_fit_in_worker('dean_jett', histogram, {}, fitOptions);
        const b = client.run_fit_in_worker('dean_jett', histogram, {}, fitOptions);
        const c = client.run_fit_in_worker('dean_jett', histogram, {}, fitOptions);
        const outcomes = Promise.allSettled([a.promise, b.promise, c.promise]);
        b.cancel();
        const bounded = workers.length === 1 && !workers[0].terminated;
        workers[0].listeners.error();
        const recovery = workers.length === 2 && workers[0].terminated;
        const active = workers[1];
        active.listeners.message({ data: { protocolVersion: 1, type: 'result',
          request_id: active.message.request_id, ok: true, result: { recovered: true } } });
        const result = await outcomes;
        a.cancel(); // A completed handle cannot terminate a replacement worker.
        return { pass: bounded && recovery && !active.terminated
          && result[0].reason?.code === 'FIT_WORKER_FAILED'
          && result[1].reason?.code === 'FIT_CANCELLED' && result[2].value?.recovered,
          detail: JSON.stringify({ bounded, recovery, statuses: result.map(r => r.status) }) };
      } finally {
        window.Worker = NativeWorker;
        if (descriptor) Object.defineProperty(navigator, 'hardwareConcurrency', descriptor);
        else delete navigator.hardwareConcurrency;
      }
    });

    await runAsync('pool size: scales as a fraction of logical cores, always leaving one for the UI', async () => {
      const { compute_pool_size, fit_pool_size } = window.FitClientPool;
      // Default 0.5 of cores, floored by "leave one for the UI", min 1.
      const cases = [
        [1, 1],   // single core -> 1 worker
        [2, 1],   // round(1)=1 -> 1
        [4, 2],   // round(2)=2
        [8, 4],   // round(4)=4
        [12, 6],  // round(6)=6
        [16, 8],  // round(8)=8
        [32, 16], // round(16)=16 -- no hard cap at 4 anymore
      ];
      const wrong = cases.filter(([cores, expected]) => compute_pool_size(cores) !== expected);
      // A missing/invalid hint falls back to a modest assumed machine (>= 1).
      const fallbackOk = compute_pool_size(undefined) >= 1 && compute_pool_size(0) >= 1
        && compute_pool_size(NaN) >= 1;
      // A custom fraction is honoured, and the leave-one-for-UI ceiling caps
      // fraction 1 at cores-1.
      const fractionOk = compute_pool_size(8, 0.25) === 2 && compute_pool_size(8, 1) === 7;
      const liveOk = Number.isInteger(fit_pool_size()) && fit_pool_size() >= 1;
      return {
        pass: wrong.length === 0 && fallbackOk && fractionOk && liveOk,
        detail: JSON.stringify({ wrong, fallbackOk, fractionOk, live: fit_pool_size() }),
      };
    });

    await runAsync('QC-08: peak-tracking worker matches direct QC, reports progress, and cancels', async () => {
      const n = 50000;
      const data = { eventCount: n, pnr: { Time: 100000 }, channels: {
        Time: Float64Array.from({ length: n }, (_, i) => i / 10),
        DNA_A: Float64Array.from({ length: n }, (_, i) => 180 + 20 * Math.sin(i / 47)),
      } };
      const options = { method: 'peak-tracking', channels: ['DNA_A'] };
      const expected = window.PeakTrackingTimeQC.runPeakTrackingTimeQC(data, null, options);
      const progress = [];
      const handle = window.run_peak_tracking_time_qc_in_worker(data, null, options,
        { onProgress: event => progress.push(event) });
      const actual = await handle.promise;
      const cancelled = window.run_peak_tracking_time_qc_in_worker(data, null, options);
      cancelled.cancel();
      let cancelledCode = null;
      try { await cancelled.promise; } catch (error) { cancelledCode = error.code; }
      return { pass: actual.retainedEventCount === expected.retainedEventCount
        && actual.percentRemoved === expected.percentRemoved
        && actual.timeQCMask.every((value, i) => value === expected.timeQCMask[i])
        && progress.some(event => event.stage === 'Tracking population peaks')
        && progress.at(-1)?.completed === progress.at(-1)?.total
        && cancelledCode === 'FIT_CANCELLED',
      detail: JSON.stringify({ retained: actual.retainedEventCount,
        progress: progress.map(event => event.stage), cancelledCode }) };
    });

    return results;
  })();
}"""


def run_cell_cycle_worker_tests(ctx: TestContext):
    results = ctx.page.evaluate(_TESTS)
    for result in results:
        ctx.check(GROUP, result["name"], result["pass"], result["detail"])
