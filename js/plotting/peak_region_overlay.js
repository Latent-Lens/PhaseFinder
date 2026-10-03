// Draggable G1/G2 peak-region handles drawn on top of the density plot for
// whichever sample the sidebar's Identify Peaks panel is currently reviewing
// (see analysis/cell_cycle/peak_review_ui.js's active_peak_review_row()).
// Uses a wide transparent drag target constrained to a single axis and commits
// straight to modeling_state.js rather than routing through a modal callback.
//
// This module never imports render.js. Sidebar edits request a full redraw;
// overlay edits update these live nodes and notify the rest of the UI without
// replacing the focused slider.
//
// render_peak_region_overlay() draws and wires the handles; boundary_limits()
// keeps a handle between its neighbors during a drag; get_value() and set_value()
// read/write a boundary on the live regions.

import * as d3 from "d3";
import { get_state } from "../analysis/pipeline/pipeline_state.js";
import {
  active_peak_review_row,
  commit_peak_region_draft,
  current_peak_region_draft,
} from "../analysis/cell_cycle/peak_review_ui.js";

const G1_COLOR = "#2563eb";
const G2_COLOR = "#b42318";
const BAND_OPACITY = 0.07;

const BOUNDARIES = [
  { key: "g1_left", region: "g1", side: "left", color: G1_COLOR },
  { key: "g1_right", region: "g1", side: "right", color: G1_COLOR },
  { key: "g2_left", region: "g2", side: "left", color: G2_COLOR },
  { key: "g2_right", region: "g2", side: "right", color: G2_COLOR },
];

/*

Purpose:
	The [min, max] a boundary may take given the other three current values,
	enforcing G1.left < G1.right <= G2.left < G2.right live during the drag -- the
	same rule validatePeakRegions checks on commit, applied continuously so a handle
	can't be dragged past its neighbor in the first place.

Input:
	key [string]: the boundary key (g1_left/g1_right/g2_left/g2_right)
	live [object]: the live { g1: {left,right}, g2: {left,right} } regions
	domain [array]: the plot's [min, max] x-domain

Output:
	limits [array]: the [min, max] this boundary may take

*/
function boundary_limits(key, live, domain) {
  const [domain_min, domain_max] = domain;
  switch (key) {
    case "g1_left": return [domain_min, live.g1.right];
    case "g1_right": return [live.g1.left, live.g2.left];
    case "g2_left": return [live.g1.right, live.g2.right];
    case "g2_right": return [live.g2.left, domain_max];
    default: return [domain_min, domain_max];
  }
}

/*

Purpose:
	Writes one boundary's value onto the live regions object.

Input:
	live [object]: the live regions
	key [string]: the boundary key
	value [number]: the new boundary value

Output:
	(none) [void]: mutates live in place

*/
function set_value(live, key, value) {
  const [region, side] = [key.startsWith("g1") ? "g1" : "g2", key.endsWith("left") ? "left" : "right"];
  live[region][side] = value;
}

/*

Purpose:
	Reads one boundary's current value from the live regions object.

Input:
	live [object]: the live regions
	key [string]: the boundary key

Output:
	value [number]: the boundary's current value

*/
function get_value(live, key) {
  const region = key.startsWith("g1") ? "g1" : "g2";
  const side = key.endsWith("left") ? "left" : "right";
  return live[region][side];
}

/*

Purpose:
	Draws the region handles for the currently reviewed row into `svg`, using the
	same scales/margins/clip as the rest of the density plot, and wires their
	drag interaction and commit. A no-op when no row is being reviewed, it
	isn't part of the currently plotted series, or it has no regions yet.

Input:
	context [object]: { svg, series, x_scale, y_scale, margin, height, clipId }

Output:
	(none) [void]: appends the overlay group to svg

*/
export function render_peak_region_overlay({ svg, series, x_scale, y_scale, margin, height, clipId }) {
  const row = active_peak_review_row();
  if (!row) return;
  const entry = series.find((candidate) => candidate.name === row.name);
  if (!entry) return;

  const state = get_state(row.name);
  const regions = current_peak_region_draft(row) ?? state?.modeling?.peakSelection?.regions;
  if (!regions) {
    if (state?.modeling?.peakDetection?.status === "single_peak_unassigned" && !state?.modeling?.peakSelection?.userAssignedIdentity) {
      const alertGroup = svg.append("g")
        .attr("class", "single_peak_alert single_peak_alert_svg")
        .attr("role", "alert");
      const boxW = Math.min(480, Math.max(260, (svg.node()?.getBoundingClientRect()?.width || 560) - margin.left - margin.right));
      const boxX = margin.left + 16;
      const boxY = margin.top + 16;
      alertGroup.append("rect")
        .attr("x", boxX)
        .attr("y", boxY)
        .attr("width", boxW)
        .attr("height", 46)
        .attr("rx", 6)
        .attr("fill", "#fffbeb")
        .attr("stroke", "#d97706")
        .attr("stroke-width", 1.5);
      alertGroup.append("text")
        .attr("x", boxX + 12)
        .attr("y", boxY + 18)
        .attr("font-size", 12)
        .attr("font-weight", "bold")
        .attr("fill", "#92400e")
        .text("Single peak detected — identity cannot be told from histogram");
      alertGroup.append("text")
        .attr("x", boxX + 12)
        .attr("y", boxY + 34)
        .attr("font-size", 11)
        .attr("fill", "#b45309")
        .text("Only one peak was found; assign whether it represents G1 or G2 to proceed.");
    }
    return;
  }

  const top = margin.top;
  const bottom = height - margin.bottom;
  const domain = x_scale.domain();
  const live = { g1: { ...regions.g1 }, g2: { ...regions.g2 } };

  const group = svg.append("g")
    .attr("class", "peak_region_overlay")
    .attr("clip-path", `url(#${clipId})`);

  const band_group = group.append("g");
  const bands = {
    g1: band_group.append("rect").attr("class", "peak_region_band").attr("fill", G1_COLOR).attr("fill-opacity", BAND_OPACITY),
    g2: band_group.append("rect").attr("class", "peak_region_band").attr("fill", G2_COLOR).attr("fill-opacity", BAND_OPACITY),
  };
  const REGION_LABEL_TEXT = { g1: "G1", g2: "G2/M" };
  const label_group = group.append("g").attr("class", "peak_region_label_group");
  const region_labels = {
    g1: {
      pill: label_group.append("rect").attr("class", "peak_region_label_pill").attr("fill", G1_COLOR),
      text: label_group.append("text").attr("class", "peak_region_label_text").attr("text-anchor", "middle").text(REGION_LABEL_TEXT.g1),
    },
    g2: {
      pill: label_group.append("rect").attr("class", "peak_region_label_pill").attr("fill", G2_COLOR),
      text: label_group.append("text").attr("class", "peak_region_label_text").attr("text-anchor", "middle").text(REGION_LABEL_TEXT.g2),
    },
  };

  const value_label = group.append("text")
    .attr("class", "peak_region_value_label")
    .attr("text-anchor", "middle")
    .attr("y", top - 4)
    .style("opacity", 0);

  const lines = {};
  const markers = {};
  const hitAreas = {};

  const redraw = () => {
    ["g1", "g2"].forEach((region) => {
      const x0 = x_scale(live[region].left);
      const x1 = x_scale(live[region].right);
      const band_x = Math.min(x0, x1);
      const band_width = Math.max(0, Math.abs(x1 - x0));
      bands[region]
        .attr("x", band_x)
        .attr("width", band_width)
        .attr("y", top)
        .attr("height", Math.max(0, bottom - top));

      const label_center = band_x + band_width / 2;
      const { pill, text } = region_labels[region];
      text.attr("x", label_center).attr("y", top + 15);
      // getBBox() can throw on some engines (notably Firefox) if the SVG
      // isn't in a fully laid-out state yet; fall back to a fixed-size pill
      // rather than letting that abort the rest of this render pass.
      let text_box;
      try {
        text_box = text.node().getBBox();
      } catch (_) {
        text_box = { x: label_center - 14, y: top + 5, width: 28, height: 12 };
      }
      pill
        .attr("x", text_box.x - 6)
        .attr("y", text_box.y - 3)
        .attr("width", text_box.width + 12)
        .attr("height", text_box.height + 6);
    });
    BOUNDARIES.forEach(({ key }) => {
      const px = x_scale(get_value(live, key));
      lines[key].attr("x1", px).attr("x2", px).attr("y1", top).attr("y2", bottom);
      markers[key].attr("cx", px).attr("cy", top);
      hitAreas[key]
        .attr("x", px - 7)
        .attr("y", top)
        .attr("width", 14)
        .attr("height", Math.max(0, bottom - top));
    });
  };

  const commit = () => {
    try {
      if (!commit_peak_region_draft(row, live, { preserveOverlay: true })) throw new Error("Invalid peak regions");
    } catch (_) {
      // A programming error in the live-clamped bounds above would land
      // here; silently re-sync to the last committed regions rather than
      // leaving the overlay in a state the sidebar disagrees with.
      live.g1 = { ...regions.g1 };
      live.g2 = { ...regions.g2 };
      redraw();
    }
  };

  const show_value_label = (key) => {
    const px = x_scale(get_value(live, key));
    value_label.attr("x", px).text(get_value(live, key).toFixed(2)).style("opacity", 1);
  };
  const hide_value_label = () => value_label.style("opacity", 0);

  BOUNDARIES.forEach(({ key, color }) => {
    lines[key] = group.append("line")
      .attr("class", "peak_region_line")
      .attr("stroke", color)
      .attr("stroke-width", 1.6)
      .attr("stroke-dasharray", "5,3")
      .attr("pointer-events", "none");
    markers[key] = group.append("circle")
      .attr("class", "peak_region_handle_marker")
      .attr("r", 5)
      .attr("fill", color)
      .attr("pointer-events", "none");
    hitAreas[key] = group.append("rect")
      .attr("class", "peak_region_handle")
      .attr("data-boundary-key", key)
      .attr("fill", "transparent")
      .style("cursor", "ew-resize");

    let drag_offset = 0;
    const pointer_x = (event) => x_scale.invert(d3.pointer(event.sourceEvent ?? event, svg.node())[0]);
    const drag = d3.drag()
      .on("start", (event) => {
        drag_offset = get_value(live, key) - pointer_x(event);
        hitAreas[key].classed("peak_region_dragging", true);
        show_value_label(key);
      })
      .on("drag", (event) => {
        const [min, max] = boundary_limits(key, live, domain);
        const value = Math.min(max, Math.max(min, pointer_x(event) + drag_offset));
        set_value(live, key, value);
        redraw();
        show_value_label(key);
      })
      .on("end", () => {
        hitAreas[key].classed("peak_region_dragging", false);
        hide_value_label();
        commit();
      });
    hitAreas[key].call(drag);

  });

  redraw();
}
