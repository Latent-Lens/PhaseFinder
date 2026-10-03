// UI-13: the residual strip beneath the main histogram -- the most direct
// visual evidence of whether a fit is good, currently computed on every fit
// (histogram_prep.js's build_fit_series_entry attaches `fit.residuals`) and,
// until this module, displayed nowhere.
//
// One .residual_group per currently visible/fitted sample, stacked inside a
// single #residual_panel (mirrors modeling.js's render_fit_results_table,
// which stacks one <tbody> per fit in a single overlay table for the same
// reason: "Fit All" can leave more than one canonical result on screen at
// once). Each group gets its own small SVG, but every group shares the exact
// x_scale the caller drew the main histogram with, so bins line up vertically
// with the features they explain -- that's the point of a residual strip.

import * as d3 from "d3";
import { residual_panel, residual_panel_normalize, residual_panel_body } from "../ui/dom.js";

const css_color = (name, fallback) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;

const RESIDUAL_BAND_FILL = css_color("--residual_band_fill", "#eef2f8");
const RESIDUAL_BAND_EDGE = css_color("--residual_band_edge", "#c3cede");
const RESIDUAL_MARK = css_color("--residual_mark", "#2563eb");
const RESIDUAL_MARK_OUT = css_color("--residual_mark_out", "#b42318");
const RESIDUAL_ZERO = css_color("--residual_zero", "#172033");

const GROUP_HEIGHT = 64;
const GROUP_MARGIN = { top: 8, bottom: 6 };
const STEM_WIDTH = 1.4;
// Pearson residuals: a |z| > 2 bin is the conventional "worth a look" cutoff.
// The reference band and the outlier mark color both key off this; raw
// (un-normalized) residuals have no such fixed threshold -- counts scale with
// peak height, which is exactly why Pearson is the default (see the panel's
// own toggle label and UI-13's checklist entry).
const OUTLIER_THRESHOLD = 2;

let last_fits = [];
let last_x_scale = null;
let last_width = 0;
let normalize_pearson = true;
let listener_installed = false;

function install_toggle_listener() {
  if (listener_installed || !residual_panel_normalize) return;
  listener_installed = true;
  normalize_pearson = residual_panel_normalize.checked;
  residual_panel_normalize.addEventListener("change", () => {
    normalize_pearson = residual_panel_normalize.checked;
    if (last_fits.length && last_x_scale) draw_panel(last_fits, last_x_scale, last_width);
  });
}

// The values this fit's strip actually plots, given the current toggle state.
function residual_values(fit) {
  return normalize_pearson ? fit.residuals.pearson : fit.residuals.raw;
}

function draw_group(container, fit, x_scale, width) {
  const values = residual_values(fit);
  const x = fit.residuals.x;
  const y_extent = Math.max(OUTLIER_THRESHOLD, d3.max(values, (value) => Math.abs(value)) || 0) * 1.15;
  const y_scale = d3
    .scaleLinear()
    .domain([-y_extent, y_extent])
    .range([GROUP_HEIGHT - GROUP_MARGIN.bottom, GROUP_MARGIN.top]);

  const wrap = container.append("div").attr("class", "residual_group");
  wrap.append("div").attr("class", "residual_group_title").attr("title", fit.name).text(fit.name);

  const svg = wrap
    .append("svg")
    .attr("class", "residual_plot")
    .attr("width", width)
    .attr("height", GROUP_HEIGHT)
    .attr("viewBox", `0 0 ${width} ${GROUP_HEIGHT}`);

  const draw = svg.append("g");

  // Draw order per the design: the ±2 reference band first, residual stems
  // over it, the zero line on top -- so stems read against the band and the
  // zero line is never obscured by an overplotted stem.
  if (normalize_pearson) {
    draw
      .append("rect")
      .attr("x", x_scale.range()[0])
      .attr("width", Math.max(0, x_scale.range()[1] - x_scale.range()[0]))
      .attr("y", y_scale(OUTLIER_THRESHOLD))
      .attr("height", Math.max(0, y_scale(-OUTLIER_THRESHOLD) - y_scale(OUTLIER_THRESHOLD)))
      .attr("fill", RESIDUAL_BAND_FILL)
      .attr("stroke", RESIDUAL_BAND_EDGE)
      .attr("stroke-width", 1);
  }

  const zero_y = y_scale(0);
  draw
    .selectAll("line.residual_stem")
    .data(values.map((value, index) => ({ value, position: x[index] })))
    .join("line")
    .attr("class", "residual_stem")
    .attr("x1", (d) => x_scale(d.position))
    .attr("x2", (d) => x_scale(d.position))
    .attr("y1", zero_y)
    .attr("y2", (d) => y_scale(d.value))
    .attr("stroke", (d) => (normalize_pearson && Math.abs(d.value) > OUTLIER_THRESHOLD ? RESIDUAL_MARK_OUT : RESIDUAL_MARK))
    .attr("stroke-width", STEM_WIDTH);

  draw
    .append("line")
    .attr("x1", x_scale.range()[0])
    .attr("x2", x_scale.range()[1])
    .attr("y1", zero_y)
    .attr("y2", zero_y)
    .attr("stroke", RESIDUAL_ZERO)
    .attr("stroke-width", 1);
}

function draw_panel(fits, x_scale, width) {
  if (!residual_panel || !residual_panel_body) return;
  const visible_fits = fits.filter((fit) => fit.residuals && fit.residuals.x.length);
  residual_panel_body.innerHTML = "";
  if (!visible_fits.length) {
    residual_panel.hidden = true;
    return;
  }
  residual_panel.hidden = false;
  const container = d3.select(residual_panel_body);
  visible_fits.forEach((fit) => draw_group(container, fit, x_scale, width));
}

/*

Purpose:
	Renders (or hides) the residual strip beneath the main histogram, one small
	group per currently visible/fitted canonical result, sharing the caller's
	x_scale so bins align with the main plot.

Input:
	fits [Array<Object>]: series-overlay fit entries from build_fit_series_entry
	                       (histogram_prep.js) -- each carries a `.residuals`
	                       field ({ x, observed, expected, raw, pearson, ... }).
	x_scale [Function]:    the same D3 scale the caller used for the main
	                        histogram's x axis.
	width [number]:        the main plot SVG's pixel width, so this panel's own
	                        SVGs span the identical horizontal extent.

Output:
	(none) [void]: updates #residual_panel and its body; hides the panel when no
	               visible fit has residual data.

*/
export function render_residual_panel(fits, x_scale, width) {
  install_toggle_listener();
  last_fits = fits;
  last_x_scale = x_scale;
  last_width = width;
  draw_panel(fits, x_scale, width);
}
