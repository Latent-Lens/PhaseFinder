# Changelog

All notable changes are recorded here, following Keep a Changelog and
Semantic Versioning 2.0.0. The `0.8.0` summary covers work since the
`v0.1.0` tag; intermediate `0.x` releases are not reconstructed.

## [Unreleased]

### Changed

- Widened the default fitted G2:G1 mean-ratio range to 1.75–2.25 and the
  peak-detection range to 1.65–2.35. Bumped Dean–Jett, Dean–Jett–Fox, and
  Watson Classic model versions to `1.1.0` so saved sessions can flag drift.

## [0.8.0] - 2026-09-24

### Added

- Browser cell-cycle modeling with Dean–Jett, Dean–Jett–Fox, Watson, and
  experimental CLOCCS options, peak-region review, QC gates, fit diagnostics,
  uncertainty checks, and versioned result export.
- Synthetic, external-tool, and browser validation suites; checklist-driven
  scientific and release audits.

### Changed

- Reworked the FCS analysis pipeline, plotting, and session format, including
  model-version drift checks and local-first privacy controls.
- Pinned the build to Node 24 and added production artifact provenance,
  privacy checks, staging deployment, and release-note preview support.
