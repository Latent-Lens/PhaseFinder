// MAINT-02: Authoritative named, versioned configuration for scientific policy thresholds.
// Every policy threshold is documented with numerical value, unit, and scientific rationale.
// Pure module: zero DOM dependencies, imports nothing, safe for all execution contexts
// (main thread, web workers, headless harness, Node.js).

export const POLICY_CONFIG_VERSION = "1.0.0";

export const POLICY_THRESHOLDS = Object.freeze({
  version: POLICY_CONFIG_VERSION,

  // QC domain thresholds
  qc: Object.freeze({
    timeQc: Object.freeze({
      defaultThreshold: Object.freeze({
        value: 4,
        unit: "mad_multiples",
        rationale: "Standard Hampel identifier cutoff for robust outlier detection in acquisition time series.",
      }),
      minEventsPerSlice: Object.freeze({
        value: 100,
        unit: "events",
        rationale: "Minimum event count per time slice needed for statistically valid median and MAD calculation.",
      }),
      minSlices: Object.freeze({
        value: 5,
        unit: "slices",
        rationale: "Minimum number of temporal slices required to evaluate acquisition stability.",
      }),
      madScaleFactor: Object.freeze({
        value: 1.4826,
        unit: "dimensionless",
        rationale: "Normal consistency scaling factor relating median absolute deviation to Gaussian standard deviation.",
      }),
      minSliceVariationFactor: Object.freeze({
        value: 0.1,
        unit: "dimensionless",
        rationale: "Noise floor factor preventing division by zero on uniform or discrete event counts.",
      }),
      stableSlicesMinRatio: Object.freeze({
        value: 0.6,
        unit: "ratio",
        rationale: "Minimum fraction of slices (60%) that must pass stability criteria for acquisition validity.",
      }),
      defaultTimerRange: Object.freeze({
        value: 32.6824,
        unit: "seconds",
        rationale: "Standard 1/100th second counter cycle characteristic of cytometer acquisition timers.",
      }),
    }),

    peakTracking: Object.freeze({
      defaultTimeBins: Object.freeze({
        value: 30,
        unit: "bins",
        rationale: "Temporal division count balancing time resolution against sufficient event count per bin.",
      }),
      defaultMaxDriftPercent: Object.freeze({
        value: 15,
        unit: "percent",
        rationale: "Maximum allowable peak centroid shift across the acquisition run before flagging fluidic drift.",
      }),
      defaultMinTrackSupport: Object.freeze({
        value: 0.5,
        unit: "fraction",
        rationale: "Minimum proportion of temporal slices (50%) in which a peak must be tracked to confirm continuity.",
      }),
    }),

    contract: Object.freeze({
      minimumModelingEvents: Object.freeze({
        value: 100,
        unit: "events",
        rationale: "Floor below which statistical cell-cycle decomposition degenerates into non-identifiability.",
      }),
      minimumNonemptyBins: Object.freeze({
        value: 5,
        unit: "bins",
        rationale: "Minimum non-zero histogram bins required to avoid underdetermined parameter estimation.",
      }),
      minimumPeakSupportEvents: Object.freeze({
        value: 10,
        unit: "events",
        rationale: "Minimum event density required within candidate peak regions to validate peak initialization.",
      }),
      qcCriticalRemovalPercent: Object.freeze({
        value: 50,
        unit: "percent",
        rationale: "Event removal exceeding 50% indicates severe contamination, fluidic blockage, or gating anomaly.",
      }),
    }),
  }),

  // Constraint audit and parameter bounds
  constraints: Object.freeze({
    activeBoundEpsilon: Object.freeze({
      value: 1e-3,
      unit: "dimensionless",
      rationale: "Relative proximity threshold to parameter bound at which an active bound warning is triggered.",
    }),
    jointConstraintTolerance: Object.freeze({
      value: 1e-9,
      unit: "dimensionless",
      rationale: "Numerical tolerance for biological inequality constraint verification.",
    }),
  }),

  // Bootstrap and perturbation resampling
  resampling: Object.freeze({
    minimumUsableReplicates: Object.freeze({
      value: 40,
      unit: "replicates",
      rationale: "Empirical lower bound of converged replicates needed for meaningful percentile confidence intervals.",
    }),
    defaultIntervalLevel: Object.freeze({
      value: 0.95,
      unit: "fraction",
      rationale: "Nominal 95% two-sided coverage confidence level.",
    }),
    selectionStabilityThreshold: Object.freeze({
      value: 0.8,
      unit: "fraction",
      rationale: "Minimum replicate model selection consensus (80%) to report a stable model choice.",
    }),
    failureRateWarning: Object.freeze({
      value: 0.05,
      unit: "fraction",
      rationale: "Bootstrap replicate optimizer failure rate exceeding 5% triggers a reliability warning.",
    }),
    failureRateCritical: Object.freeze({
      value: 0.20,
      unit: "fraction",
      rationale: "Bootstrap failure rate exceeding 20% invalidates the interval for unreserved reporting.",
    }),
  }),

  // Histogram binning policy
  binning: Object.freeze({
    minEventsPerBin: Object.freeze({
      value: 20,
      unit: "events",
      rationale: "Recommended lower limit on mean counts per bin to maintain Poisson deviance approximation validity.",
    }),
    comfortableEventsPerBin: Object.freeze({
      value: 50,
      unit: "events",
      rationale: "Comfortable event density per bin for high-fidelity parametric fitting.",
    }),
    coarseBinCount: Object.freeze({
      value: 128,
      unit: "bins",
      rationale: "Fallback bin count for low-count acquisitions.",
    }),
  }),
});

/*
Purpose:
	Returns a serializable summary of all active policy threshold values and metadata
	for embedding in fit provenance and session records.
*/
export function get_policy_provenance() {
  return {
    policyVersion: POLICY_CONFIG_VERSION,
    thresholds: {
      minimumModelingEvents: POLICY_THRESHOLDS.qc.contract.minimumModelingEvents.value,
      minimumNonemptyBins: POLICY_THRESHOLDS.qc.contract.minimumNonemptyBins.value,
      minimumPeakSupportEvents: POLICY_THRESHOLDS.qc.contract.minimumPeakSupportEvents.value,
      qcCriticalRemovalPercent: POLICY_THRESHOLDS.qc.contract.qcCriticalRemovalPercent.value,
      activeBoundEpsilon: POLICY_THRESHOLDS.constraints.activeBoundEpsilon.value,
      jointConstraintTolerance: POLICY_THRESHOLDS.constraints.jointConstraintTolerance.value,
      minimumUsableReplicates: POLICY_THRESHOLDS.resampling.minimumUsableReplicates.value,
      defaultIntervalLevel: POLICY_THRESHOLDS.resampling.defaultIntervalLevel.value,
      selectionStabilityThreshold: POLICY_THRESHOLDS.resampling.selectionStabilityThreshold.value,
      failureRateWarning: POLICY_THRESHOLDS.resampling.failureRateWarning.value,
      failureRateCritical: POLICY_THRESHOLDS.resampling.failureRateCritical.value,
      minEventsPerBin: POLICY_THRESHOLDS.binning.minEventsPerBin.value,
      comfortableEventsPerBin: POLICY_THRESHOLDS.binning.comfortableEventsPerBin.value,
      timeQcThreshold: POLICY_THRESHOLDS.qc.timeQc.defaultThreshold.value,
      minEventsPerSlice: POLICY_THRESHOLDS.qc.timeQc.minEventsPerSlice.value,
      minSlices: POLICY_THRESHOLDS.qc.timeQc.minSlices.value,
      stableSlicesMinRatio: POLICY_THRESHOLDS.qc.timeQc.stableSlicesMinRatio.value,
    },
  };
}
