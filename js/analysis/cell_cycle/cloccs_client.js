// Main-thread client for the CLOCCS fit worker (cloccs_worker.js). Runs the
// joint fit off the UI thread and returns a handle with a cancel() so a slow,
// unverified fit can be interrupted at a round boundary.
//
// run_cloccs_fit(series, config, { onProgress }) -> { promise, cancel }
//   promise resolves with the fit result, or { cancelled: true } if cancelled.

import { is_worker_message, worker_message } from "../../util/worker_protocol.js";

let worker = null;
let nextRequestId = 1;
const pending = new Map(); // request_id -> { resolve, reject, onProgress }

function terminate_worker(error = null) {
  if (worker) {
    try {
      worker.terminate();
    } catch (_) {
      // worker may already be closed
    }
    worker = null;
  }
  if (error) {
    for (const [, request] of pending) {
      request.reject(error);
    }
    pending.clear();
  }
}

function ensure_worker() {
  if (worker) return worker;
  // The `new URL(...)` literal MUST stay inline (a bundler only recognises this
  // exact form as a worker entry point) -- same rule as fit_client.js.
  worker = new Worker(new URL("./cloccs_worker.js", import.meta.url), { type: "module" });
  worker.addEventListener("message", (event) => {
    const message = event.data || {};
    const request = pending.get(message.request_id);
    if (!request) return;
    if (!is_worker_message(message, ["progress", "result", "cancelled", "error"])) {
      pending.delete(message.request_id);
      const error = new Error("CLOCCS worker protocol mismatch.");
      error.code = "WORKER_PROTOCOL_MISMATCH";
      request.reject(error);
      return;
    }
    if (message.type === "progress") {
      request.onProgress?.(message.progress);
      return;
    }
    pending.delete(message.request_id);
    if (message.type === "result") request.resolve(message.result);
    else if (message.type === "cancelled") request.resolve({ cancelled: true });
    else request.reject(new Error(message.message || "CLOCCS fit failed."));
  });
  worker.addEventListener("error", (event) => {
    // WORKER-01: A worker-level failure terminates the failed worker and rejects
    // every in-flight request so the client can recreate a fresh worker on retry.
    const err = new Error(event?.message || "CLOCCS worker error.");
    terminate_worker(err);
  });
  worker.addEventListener("messageerror", () => {
    const err = new Error("CLOCCS worker message could not be deserialized.");
    err.code = "WORKER_MESSAGE_ERROR";
    terminate_worker(err);
  });
  return worker;
}

/*
Purpose: runs one CLOCCS strain fit in the worker.
Input:
	series [object]: the strain series
	config [object]: fit config (DEFAULT_CONFIG overrides)
	options [object]: { onProgress } progress callback
Output:
	handle [object]: { promise, cancel } -- promise resolves with the result (or
		{ cancelled: true }); cancel() requests interruption at the next round.
*/
export function run_cloccs_fit(series, config, { onProgress } = {}) {
  let active;
  try {
    active = ensure_worker();
  } catch (err) {
    return {
      promise: Promise.reject(err),
      cancel: () => {},
    };
  }

  const request_id = nextRequestId;
  nextRequestId += 1;
  let cancel_fn = () => {};
  const promise = new Promise((resolve, reject) => {
    pending.set(request_id, { resolve, reject, onProgress });
    try {
      active.postMessage(worker_message("fit", request_id, { series, config }));
      cancel_fn = () => {
        try {
          active.postMessage(worker_message("cancel", request_id));
        } catch (_) {
          // worker may already be terminated
        }
      };
    } catch (err) {
      // WORKER-01: remove pending request immediately on sync postMessage failure
      pending.delete(request_id);
      reject(err);
    }
  });

  return {
    promise,
    cancel: () => cancel_fn(),
  };
}

// Accessors for testing and worker lifecycle management (WORKER-01)
export function get_cloccs_worker() {
  return worker;
}

export function terminate_cloccs_worker(reason = "CLOCCS worker terminated.") {
  const err = new Error(reason);
  err.code = "WORKER_TERMINATED";
  terminate_worker(err);
}

export function get_cloccs_pending_count() {
  return pending.size;
}
