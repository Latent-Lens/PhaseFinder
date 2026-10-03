#!/usr/bin/env python3
"""TEST-02 box 6: Track CI duration, flake rate, browser-specific failures, and benchmark drift."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        # Standard ISO 8601 with Z or offset
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def fetch_gh_runs(limit: int = 30, offline_sample: dict | None = None) -> list[dict]:
    """Fetch recent GitHub Actions runs via gh CLI, or return offline sample."""
    if offline_sample and "runs" in offline_sample:
        return offline_sample["runs"]

    cmd = [
        "gh",
        "run",
        "list",
        "--limit",
        str(limit),
        "--json",
        "databaseId,name,workflowName,headBranch,headSha,event,status,conclusion,startedAt,updatedAt,url",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except Exception:
        pass
    return []


def fetch_run_jobs(run_id: int | str, offline_sample: dict | None = None) -> list[dict]:
    """Fetch jobs for a specific workflow run."""
    if offline_sample and "jobs" in offline_sample:
        sample_jobs = offline_sample["jobs"]
        if isinstance(sample_jobs, dict):
            return sample_jobs.get(str(run_id), [])
        if isinstance(sample_jobs, list):
            return sample_jobs

    cmd = [
        "gh",
        "run",
        "view",
        str(run_id),
        "--json",
        "jobs",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            return data.get("jobs", [])
    except Exception:
        pass
    return []


def analyze_ci_durations_and_flakes(runs: list[dict]) -> dict:
    """Compute run durations, failure rates, and potential flake indicators."""
    durations_by_workflow: dict[str, list[float]] = {}
    completed_runs = 0
    success_count = 0
    failure_count = 0
    other_count = 0

    run_durations: list[dict] = []
    runs_by_commit: dict[str, list[dict]] = {}

    for run in runs:
        wf = run.get("workflowName") or run.get("name") or "Unknown"
        status = run.get("status")
        conclusion = run.get("conclusion")
        sha = run.get("headSha") or run.get("headBranch") or ""

        if sha:
            runs_by_commit.setdefault(sha, []).append(run)

        if status == "completed":
            completed_runs += 1
            if conclusion == "success":
                success_count += 1
            elif conclusion in ("failure", "timed_out"):
                failure_count += 1
            else:
                other_count += 1

            start_dt = parse_iso_datetime(run.get("startedAt"))
            end_dt = parse_iso_datetime(run.get("updatedAt"))
            if start_dt and end_dt and end_dt >= start_dt:
                duration_sec = (end_dt - start_dt).total_seconds()
                durations_by_workflow.setdefault(wf, []).append(duration_sec)
                run_durations.append({
                    "run_id": run.get("databaseId"),
                    "workflow": wf,
                    "duration_sec": duration_sec,
                    "conclusion": conclusion,
                    "date": run.get("startedAt"),
                })

    # Detect flakes: runs on the same commit/branch with mixed conclusions (e.g., failed then succeeded on rerun)
    flaky_shas = set()
    for sha, group in runs_by_commit.items():
        conclusions = {r.get("conclusion") for r in group if r.get("status") == "completed"}
        if "success" in conclusions and ("failure" in conclusions or "timed_out" in conclusions):
            flaky_shas.add(sha)

    workflow_summary = {}
    for wf, durs in durations_by_workflow.items():
        workflow_summary[wf] = {
            "count": len(durs),
            "mean_seconds": round(statistics.mean(durs), 1) if durs else 0.0,
            "median_seconds": round(statistics.median(durs), 1) if durs else 0.0,
            "min_seconds": round(min(durs), 1) if durs else 0.0,
            "max_seconds": round(max(durs), 1) if durs else 0.0,
        }

    total_tracked = success_count + failure_count + other_count
    flake_rate_pct = round((len(flaky_shas) / max(1, len(runs_by_commit))) * 100.0, 1)
    failure_rate_pct = round((failure_count / max(1, total_tracked)) * 100.0, 1)

    return {
        "total_runs_inspected": len(runs),
        "completed_runs": completed_runs,
        "success_count": success_count,
        "failure_count": failure_count,
        "other_count": other_count,
        "failure_rate_pct": failure_rate_pct,
        "flaky_commits_detected": len(flaky_shas),
        "flake_rate_pct": flake_rate_pct,
        "workflow_durations": workflow_summary,
        "recent_durations": sorted(run_durations, key=lambda x: x["duration_sec"], reverse=True)[:5],
    }


def analyze_browser_failures(
    runs: list[dict],
    offline_sample: dict | None = None,
    results_dir: Path | None = None,
) -> dict:
    """Analyze browser-specific failure breakdown across CI jobs and local evidence."""
    browser_stats: dict[str, dict] = {
        "chromium": {"runs": 0, "passed": 0, "failed": 0, "pass_rate_pct": 0.0},
        "firefox": {"runs": 0, "passed": 0, "failed": 0, "pass_rate_pct": 0.0},
        "webkit": {"runs": 0, "passed": 0, "failed": 0, "pass_rate_pct": 0.0},
        "edge": {"runs": 0, "passed": 0, "failed": 0, "pass_rate_pct": 0.0},
        "brave": {"runs": 0, "passed": 0, "failed": 0, "pass_rate_pct": 0.0},
    }

    # 1. Inspect jobs from Browser compatibility runs
    browser_runs = [r for r in runs if "browser" in (r.get("workflowName") or "").lower()][:5]
    for r in browser_runs:
        run_id = r.get("databaseId")
        if not run_id:
            continue
        jobs = fetch_run_jobs(run_id, offline_sample)
        for job in jobs:
            name = (job.get("name") or "").lower()
            conclusion = job.get("conclusion")
            for b in browser_stats.keys():
                if b in name:
                    browser_stats[b]["runs"] += 1
                    if conclusion == "success":
                        browser_stats[b]["passed"] += 1
                    elif conclusion in ("failure", "timed_out"):
                        browser_stats[b]["failed"] += 1
                    break

    # 2. Also inspect local compatibility.json files if available
    ev_dir = results_dir or (ROOT / "tests/e2e/results")
    if ev_dir.exists():
        for comp_file in ev_dir.rglob("compatibility.json"):
            try:
                data = json.loads(comp_file.read_text(encoding="utf-8"))
                browser = (data.get("browser") or "").lower()
                status = (data.get("status") or "").lower()
                if browser in browser_stats:
                    browser_stats[browser]["runs"] += 1
                    if status == "passed":
                        browser_stats[browser]["passed"] += 1
                    elif status == "failed":
                        browser_stats[browser]["failed"] += 1
            except Exception:
                pass

    for b, s in browser_stats.items():
        total = s["passed"] + s["failed"]
        s["pass_rate_pct"] = round((s["passed"] / max(1, total)) * 100.0, 1) if total > 0 else None

    return browser_stats


def analyze_artifact_sizes(dist_dir: Path | None = None) -> dict:
    """Summarize production artifact sizes and verify against budget."""
    target = dist_dir or (ROOT / "dist")
    manifest_path = target / "artifact-manifest.json"

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest.get("files", [])
            total_bytes = sum(f.get("bytes", 0) for f in files)
            js_bytes = sum(f.get("bytes", 0) for f in files if f.get("path", "").endswith(".js"))
            css_bytes = sum(f.get("bytes", 0) for f in files if f.get("path", "").endswith(".css"))
            img_bytes = sum(
                f.get("bytes", 0)
                for f in files
                if re.search(r"\.(?:png|jpe?g|webp|gif|svg|ico)$", f.get("path", ""), re.I)
            )
            return {
                "manifest_present": True,
                "file_count": len(files),
                "total_bytes": total_bytes,
                "js_bytes": js_bytes,
                "css_bytes": css_bytes,
                "images_bytes": img_bytes,
                "within_budget": total_bytes <= 5_000_000,
            }
        except Exception:
            pass

    # Fallback to direct directory scan if dist/ exists
    if target.exists():
        all_files = [p for p in target.rglob("*") if p.is_file()]
        total_bytes = sum(p.stat().st_size for p in all_files)
        js_bytes = sum(p.stat().st_size for p in all_files if p.suffix == ".js")
        css_bytes = sum(p.stat().st_size for p in all_files if p.suffix == ".css")
        img_bytes = sum(
            p.stat().st_size
            for p in all_files
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico")
        )
        return {
            "manifest_present": False,
            "file_count": len(all_files),
            "total_bytes": total_bytes,
            "js_bytes": js_bytes,
            "css_bytes": css_bytes,
            "images_bytes": img_bytes,
            "within_budget": total_bytes <= 5_000_000,
        }

    return {
        "manifest_present": False,
        "file_count": 0,
        "total_bytes": 0,
        "js_bytes": 0,
        "css_bytes": 0,
        "images_bytes": 0,
        "within_budget": True,
    }


def analyze_benchmark_drift(
    benchmark_dir: Path | None = None,
    max_drift_pp: float = 0.15,
) -> dict:
    """Track model error percentage points and detect benchmark drift."""
    bdir = benchmark_dir or (ROOT / "tests/validation/results")
    if not bdir.exists():
        return {"benchmarks_found": 0, "drift_detected": False, "models": {}}

    benchmark_files = sorted(bdir.glob("synthetic_fcs_benchmark_*.json"))
    if not benchmark_files:
        return {"benchmarks_found": 0, "drift_detected": False, "models": {}}

    # Load latest benchmark
    latest_file = benchmark_files[-1]
    history: list[dict] = []

    for f in benchmark_files[-5:]:  # inspect up to last 5 benchmarks
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            models_data = data.get("models", [])
            if not models_data:
                continue
            entry = {
                "file": f.name,
                "model_errors": {},
                "converged_cases": 0,
                "total_cases": len(models_data),
            }
            for m in models_data:
                mid = m.get("modelId")
                err = m.get("maxAbsoluteErrorPercentagePoints")
                if m.get("converged"):
                    entry["converged_cases"] += 1
                if mid and err is not None:
                    entry["model_errors"].setdefault(mid, []).append(err)
            history.append(entry)
        except Exception:
            pass

    if not history:
        return {"benchmarks_found": len(benchmark_files), "drift_detected": False, "models": {}}

    latest = history[-1]
    baseline = history[0]

    model_drift = {}
    drift_detected = False

    all_model_keys = set(latest["model_errors"].keys()) | set(baseline["model_errors"].keys())
    for mid in sorted(all_model_keys):
        latest_errs = latest["model_errors"].get(mid, [])
        base_errs = baseline["model_errors"].get(mid, [])
        latest_mean = statistics.mean(latest_errs) if latest_errs else None
        base_mean = statistics.mean(base_errs) if base_errs else None

        delta = None
        exceeded = False
        if latest_mean is not None and base_mean is not None:
            delta = round(latest_mean - base_mean, 4)
            if delta > max_drift_pp:
                exceeded = True
                drift_detected = True

        model_drift[mid] = {
            "latest_mean_error_pp": round(latest_mean, 3) if latest_mean is not None else None,
            "baseline_mean_error_pp": round(base_mean, 3) if base_mean is not None else None,
            "delta_pp": delta,
            "exceeded_drift_limit": exceeded,
        }

    return {
        "benchmarks_found": len(benchmark_files),
        "latest_file": latest_file.name,
        "baseline_file": baseline["file"],
        "drift_detected": drift_detected,
        "max_drift_pp_allowed": max_drift_pp,
        "models": model_drift,
    }


def generate_markdown_report(
    durations: dict,
    browsers: dict,
    artifacts: dict,
    benchmarks: dict,
) -> str:
    """Format metrics into a GitHub Actions step summary / markdown report."""
    lines = [
        "## CI Trend & Quality Metrics (TEST-02)",
        "",
        "> [!NOTE]",
        "> Automated governance metrics covering CI runtime duration, flake rates, browser compatibility, artifact sizes, and scientific benchmark drift.",
        "",
        "### 1. CI Workflow Durations & Flake Rate",
        "",
        f"- **Runs Inspected:** {durations.get('total_runs_inspected', 0)} ({durations.get('completed_runs', 0)} completed)",
        f"- **Failure Rate:** {durations.get('failure_rate_pct', 0.0)}% ({durations.get('failure_count', 0)} failures)",
        f"- **Flake Rate:** {durations.get('flake_rate_pct', 0.0)}% ({durations.get('flaky_commits_detected', 0)} flaky runs detected)",
        "",
        "| Workflow | Runs | Mean (s) | Median (s) | Min (s) | Max (s) |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for wf, stats in durations.get("workflow_durations", {}).items():
        lines.append(
            f"| {wf} | {stats['count']} | {stats['mean_seconds']}s | {stats['median_seconds']}s | {stats['min_seconds']}s | {stats['max_seconds']}s |"
        )
    if not durations.get("workflow_durations"):
        lines.append("| — | 0 | — | — | — | — |")

    lines.extend([
        "",
        "### 2. Browser Compatibility Breakdown",
        "",
        "| Browser | Runs Tracked | Passed | Failed | Pass Rate |",
        "|---|---:|---:|---:|---:|",
    ])

    for b, s in browsers.items():
        rate = f"{s['pass_rate_pct']}%" if s["pass_rate_pct"] is not None else "—"
        lines.append(f"| {b.capitalize()} | {s['runs']} | {s['passed']} | {s['failed']} | {rate} |")

    lines.extend([
        "",
        "### 3. Production Artifact Size & Budget",
        "",
        f"- **Total Files:** {artifacts.get('file_count', 0)}",
        f"- **Total Size:** {round(artifacts.get('total_bytes', 0) / 1024, 1)} kB",
        f"- **JavaScript:** {round(artifacts.get('js_bytes', 0) / 1024, 1)} kB",
        f"- **CSS:** {round(artifacts.get('css_bytes', 0) / 1024, 1)} kB",
        f"- **Images/Assets:** {round(artifacts.get('images_bytes', 0) / 1024, 1)} kB",
        f"- **Budget Status:** {'✅ Within Budget' if artifacts.get('within_budget') else '⚠️ Exceeds Budget'}",
        "",
        "### 4. Benchmark & Scientific Model Drift",
        "",
        f"- **Benchmark Files Tracked:** {benchmarks.get('benchmarks_found', 0)}",
        f"- **Drift Limit:** ±{benchmarks.get('max_drift_pp_allowed', 0.15)} pp",
        f"- **Drift Status:** {'⚠️ Drift Detected' if benchmarks.get('drift_detected') else '✅ Stable (No Drift Detected)'}",
        "",
        "| Model | Baseline Error (pp) | Latest Error (pp) | Delta (pp) | Status |",
        "|---|---:|---:|---:|---|",
    ])

    for mid, s in benchmarks.get("models", {}).items():
        base_err = f"{s['baseline_mean_error_pp']:.2f}" if s["baseline_mean_error_pp"] is not None else "—"
        lat_err = f"{s['latest_mean_error_pp']:.2f}" if s["latest_mean_error_pp"] is not None else "—"
        delta = f"{s['delta_pp']:+.3f}" if s["delta_pp"] is not None else "—"
        status = "⚠️ Exceeded" if s.get("exceeded_drift_limit") else "✅ Normal"
        lines.append(f"| {mid} | {base_err} | {lat_err} | {delta} | {status} |")

    if not benchmarks.get("models"):
        lines.append("| — | — | — | — | — |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Track CI duration, flakes, browsers, artifacts, and benchmark drift")
    parser.add_argument("--gh-limit", type=int, default=30, help="Maximum GitHub Actions runs to query")
    parser.add_argument("--offline-sample", type=Path, default=None, help="Path to JSON file with mock gh run and job data")
    parser.add_argument("--dist-dir", type=Path, default=None, help="Path to dist directory")
    parser.add_argument("--results-dir", type=Path, default=None, help="Path to test results directory")
    parser.add_argument("--json-output", type=Path, default=None, help="File to write JSON metrics report")
    parser.add_argument("--summary-file", type=Path, default=None, help="File to append markdown report (e.g. $GITHUB_STEP_SUMMARY)")
    parser.add_argument("--check-drift", action="store_true", help="Fail with exit code 1 if benchmark drift exceeds tolerance")
    args = parser.parse_args()

    offline_data = None
    if args.offline_sample and args.offline_sample.exists():
        try:
            offline_data = json.loads(args.offline_sample.read_text(encoding="utf-8"))
        except Exception as err:
            print(f"Warning: failed reading offline sample: {err}", file=sys.stderr)

    runs = fetch_gh_runs(limit=args.gh_limit, offline_sample=offline_data)
    durations = analyze_ci_durations_and_flakes(runs)
    browsers = analyze_browser_failures(runs, offline_sample=offline_data, results_dir=args.results_dir)
    artifacts = analyze_artifact_sizes(dist_dir=args.dist_dir)
    benchmarks = analyze_benchmark_drift(benchmark_dir=args.results_dir)

    markdown = generate_markdown_report(durations, browsers, artifacts, benchmarks)
    print(markdown)

    summary_target = args.summary_file or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if "GITHUB_STEP_SUMMARY" in os.environ else None)
    if summary_target:
        try:
            with open(summary_target, "a", encoding="utf-8") as sf:
                sf.write("\n" + markdown + "\n")
        except Exception as err:
            print(f"Warning: could not write to summary file: {err}", file=sys.stderr)

    if args.json_output:
        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "durations": durations,
            "browsers": browsers,
            "artifacts": artifacts,
            "benchmarks": benchmarks,
        }
        args.json_output.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")

    if args.check_drift and benchmarks.get("drift_detected"):
        print("Error: benchmark drift exceeded threshold!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
