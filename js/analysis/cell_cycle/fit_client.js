// Bounded worker pool: one request per worker, excess requests wait on the UI
// thread. Cancellation terminates only that request's worker. Scientific work
// never falls back to the UI thread when workers fail or are unavailable.
import { is_worker_message, worker_message } from "../../util/worker_protocol.js";

const POOL_FRACTION = 0.5;

// When navigator.hardwareConcurrency is unavailable, assume a modest 4-core
// machine rather than guessing high.
const ASSUMED_CORES = 4;

/*

Purpose:
	Pure worker-pool sizing policy: how many parallel fit workers to allow for a
	given logical-core count. Uses POOL_FRACTION of the cores, always leaves at
	least one core for the main/UI thread, and always allows at least one worker.
	An invalid/missing core count falls back to ASSUMED_CORES. Exported so the
	policy can be unit-tested deterministically without a real navigator.

Input:
	logicalCores [number|undefined]: navigator.hardwareConcurrency, or undefined
	fraction [number]: the core fraction to use (defaults to POOL_FRACTION)

Output:
	size [number]: the pool size (integer >= 1)

*/
export function compute_pool_size(logicalCores, fraction = POOL_FRACTION) {
  const cores = Number.isFinite(logicalCores) && logicalCores >= 1
    ? Math.floor(logicalCores)
    : ASSUMED_CORES;
  const leaveOneForUI = Math.max(1, cores - 1);
  return Math.max(1, Math.min(leaveOneForUI, Math.round(cores * fraction)));
}

const POOL_SIZE = compute_pool_size(
  typeof navigator !== "undefined" && navigator.hardwareConcurrency
    ? navigator.hardwareConcurrency
    : undefined,
);

const pool = [];
const queue = [];
let requestId = 0;

export function fit_pool_size() { return POOL_SIZE; }

function failure(message, code) {
  return Object.assign(new Error(message), { code });
}

function remove_worker(entry) {
  entry.worker.terminate();
  const index = pool.indexOf(entry);
  if (index >= 0) pool.splice(index, 1);
}

function settle(entry, error, result) {
  const request = entry.request;
  if (!request) return;
  entry.request = null;
  request.entry = null;
  request.done = true;
  if (error) request.reject(error);
  else request.resolve(result);
  dispatch();
}

function make_worker() {
  const worker = new Worker(new URL("./fit_worker.js", import.meta.url), { type: "module" });
  const entry = { worker, request: null };
  const fail = (code, message) => {
    remove_worker(entry);
    settle(entry, failure(message, code));
  };
  worker.addEventListener("message", ({ data: message }) => {
    const request = entry.request;
    if (!request || message?.request_id !== request.id) return;
    if (!is_worker_message(message, ["progress", "result"])) {
      fail("WORKER_PROTOCOL_MISMATCH", "Fit worker protocol mismatch.");
    } else if (message.type === "progress") {
      request.onProgress?.(message);
    } else {
      settle(entry, message.ok ? null : failure(message.error || "Fit worker failed.",
        message.code || "FIT_WORKER_FAILED"), message.result);
    }
  });
  worker.addEventListener("error", () => fail("FIT_WORKER_FAILED", "Fit worker failed."));
  worker.addEventListener("messageerror", () => fail("FIT_WORKER_FAILED", "Fit worker response could not be decoded."));
  return entry;
}

function dispatch() {
  while (queue.length) {
    let entry = pool.find(candidate => !candidate.request);
    if (!entry && pool.length >= POOL_SIZE) return;
    if (!entry) {
      try {
        entry = make_worker();
        pool.push(entry);
      } catch (_) {
        for (const request of queue.splice(0)) {
          request.done = true;
          request.reject(failure("Fit workers are unavailable. Enable Web Workers and reload to fit samples.", "FIT_WORKER_UNAVAILABLE"));
        }
        return;
      }
    }
    const request = queue.shift();
    request.entry = entry;
    entry.request = request;
    try {
      entry.worker.postMessage(worker_message(request.type, request.id, request.payload));
    } catch (_) {
      remove_worker(entry);
      settle(entry, failure("Fit worker request could not be sent.", "FIT_WORKER_FAILED"));
    }
  }
}

function submit(type, payload, { onProgress } = {}) {
  const request = { id: ++requestId, type, payload, onProgress, entry: null, done: false };
  const promise = new Promise((resolve, reject) => { Object.assign(request, { resolve, reject }); });
  queue.push(request);
  dispatch();
  return { promise, cancel() {
    if (request.done) return;
    const error = failure("Fit cancelled.", "FIT_CANCELLED");
    error.name = "AbortError";
    if (request.entry) {
      const entry = request.entry;
      remove_worker(entry);
      settle(entry, error);
    } else {
      const index = queue.indexOf(request);
      if (index >= 0) queue.splice(index, 1);
      request.done = true;
      request.reject(error);
    }
  } };
}

export function run_fit_in_worker(modelId, histogram, config, { onProgress, peakRegions } = {}) {
  return submit("fit", { modelId, histogram, config, peakRegions }, { onProgress });
}

export function run_peak_tracking_time_qc_in_worker(dataset, structuralMask, options, { onProgress } = {}) {
  return submit("peak_tracking_time_qc", { dataset, structuralMask, options }, { onProgress });
}

export function run_domain_sensitivity_in_worker(spec, options = {}) {
  return submit("domain_sensitivity", spec, options);
}

export function run_resample_uncertainty_in_worker(spec, options = {}) {
  return submit("resample_uncertainty", spec, options);
}
