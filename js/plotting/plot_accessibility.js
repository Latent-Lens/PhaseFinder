// Visible plot data summary and axis-clipping warning.

import { plot_area, plot_channels } from "./data.js";
import { fraction_trust_reason } from "../analysis/cell_cycle/result_contract.js";

// Keep the visible summary's trust caveat aligned with fraction_trust_reason().
export function analysis_text(entry, fit) {
  if (!fit) {
    const qc_steps = entry.pipelineState?.lastRunIndex;
    return qc_steps == null ? "QC not run; no model fit" : `QC through stage ${qc_steps + 1}; no model fit`;
  }
  const phases = ["g1", "s", "g2"]
    .map((key) => `${key === "g2" ? "G2/M" : key.toUpperCase()} ${Number(fit.fractions[key]).toFixed(1)}%`)
    .join(", ");
  const reason = fraction_trust_reason(fit);
  return `${fit.modelLabel || fit.modelId || "Cell-cycle model"}: ${phases}${reason ? ` (${reason})` : ""}`;
}

// LEGACY-01: canonical warnings only. The legacy stage-8 report's warnings used
// to be merged in here, mixing a different model's diagnostics into the
// accessible description of a canonical fit.
function warning_text(fit) {
  const warnings = [...(fit?.warnings || [])];
  return warnings.length
    ? warnings.map((warning) => warning.message || String(warning)).join("; ")
    : "None";
}

export function render_plot_accessibility_summary(entries, fits, x_domain, y_domain) {
  const parent = plot_area.parentElement;
  parent?.querySelector(":scope > .plot_accessibility_summary")?.remove();
  if (!parent) return;
  const fit_by_name = new Map(fits.map((fit) => [fit.name, fit]));
  const details = document.createElement("details");
  details.className = "plot_accessibility_summary";
  const summary = document.createElement("summary");
  summary.textContent = "Plot data and analysis summary";
  const axes = document.createElement("p");
  axes.textContent = `${plot_channels.dna_area || "DNA-content area"}: X ${x_domain[0]} to ${x_domain[1]}; events per bin Y ${y_domain[0]} to ${y_domain[1]}.`;
  const table = document.createElement("table");
  table.innerHTML = "<caption>Text alternative for the current plot</caption><thead><tr><th scope=\"col\">Sample</th><th scope=\"col\">Color group</th><th scope=\"col\">Events</th><th scope=\"col\">Outside range</th><th scope=\"col\">QC and model result</th><th scope=\"col\">Warnings</th></tr></thead>";
  const body = table.createTBody();
  if (!entries.length) {
    const cell = body.insertRow().insertCell();
    cell.colSpan = 6;
    cell.textContent = "No samples are currently plotted.";
  }
  entries.forEach((entry) => {
    const fit = fit_by_name.get(entry.name);
    const row = body.insertRow();
    [entry.name, String(entry.group || "Ungrouped"), Number(entry.stats?.plotted ?? entry.values.length).toLocaleString(), `${entry.stats?.underflow || 0} below; ${entry.stats?.overflow || 0} above`, analysis_text(entry, fit), warning_text(fit)]
      .forEach((value, index) => {
        const cell = index === 0 ? document.createElement("th") : document.createElement("td");
        if (index === 0) cell.scope = "row";
        cell.textContent = value;
        row.appendChild(cell);
      });
  });
  details.append(summary, axes, table);
  parent.appendChild(details);
}

export function render_plot_clipping_warning(entries) {
  const parent = plot_area.parentElement;
  parent?.querySelector(":scope > .plot_clipping_warning")?.remove();
  const clipped = entries.filter((entry) => (entry.stats?.underflow || 0) + (entry.stats?.overflow || 0) > 0);
  if (!parent || !clipped.length) return;
  const warning = document.createElement("p");
  warning.className = "plot_clipping_warning";
  warning.textContent = `Axis range excludes events in ${clipped.length} sample${clipped.length === 1 ? "" : "s"}: ` +
    clipped.map((entry) => `${entry.name} (${entry.stats.underflow} below, ${entry.stats.overflow} above)`).join("; ");
  parent.appendChild(warning);
}
