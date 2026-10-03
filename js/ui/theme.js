// Light/Dark theme management for PhaseFinder (UI-12).
// The status-bar toggle flips between light and dark. Until the user picks one,
// the theme follows the live OS preference ("system"). Persists the choice in
// localStorage, updates the root data-theme attribute and the toggle's icon and
// hover text, and triggers plot color re-read.

import { theme_toggle } from "./dom.js";
import { Tooltips } from "./hover_text.js";
import { refresh_plot_theme_colors, is_dark_theme } from "../plotting/data.js";
import { render_density_plot } from "../plotting/render.js";

export const THEME_STORAGE_KEY = "phasefinder_theme";
export const VALID_THEMES = Object.freeze(["system", "light", "dark"]);

let current_theme = "system";

export function get_current_theme() {
  return current_theme;
}

export function apply_theme(theme, persist = true) {
  if (!VALID_THEMES.includes(theme)) {
    theme = "system";
  }
  current_theme = theme;

  if (persist) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (_) {
      // localStorage may be unavailable or disabled
    }
  }

  if (typeof document !== "undefined" && document.documentElement) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }

  refresh_plot_theme_colors();
  update_theme_icon();

  const event_detail = { theme, isDark: is_dark_theme() };
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("pf-theme-changed", { detail: event_detail }));
  }
  if (typeof document !== "undefined") {
    document.dispatchEvent(new CustomEvent("pf-theme-changed", { detail: event_detail }));
  }

  try {
    render_density_plot();
  } catch (_) {
    // Plot may not be initialized yet during initial bootstrap
  }
}

// The toggle shows the theme a click switches to: a sun while dark, a moon while light.
function update_theme_icon() {
  if (!theme_toggle) return;
  const dark = is_dark_theme();
  const label = Tooltips.text(dark ? "themeToLight" : "themeToDark");
  const icon = theme_toggle.querySelector(".theme_icon_symbol");
  if (icon) icon.textContent = dark ? "☀️" : "🌙";
  theme_toggle.setAttribute("aria-label", label);
  Tooltips.set_quick_tooltip(theme_toggle, dark ? "themeToLight" : "themeToDark");
}

export function init_theme() {
  let initial_theme = "system";
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (VALID_THEMES.includes(stored)) {
      initial_theme = stored;
    }
  } catch (_) {
    // storage access blocked/private mode
  }

  theme_toggle?.addEventListener("click", () => apply_theme(is_dark_theme() ? "light" : "dark"));

  if (typeof window !== "undefined" && window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handle_system_change = () => {
      if (current_theme === "system") {
        refresh_plot_theme_colors();
        update_theme_icon();
        const event_detail = { theme: "system", isDark: is_dark_theme() };
        window.dispatchEvent(new CustomEvent("pf-theme-changed", { detail: event_detail }));
        document.dispatchEvent(new CustomEvent("pf-theme-changed", { detail: event_detail }));
        try {
          render_density_plot();
        } catch (_) {
          // Plot may not be ready yet
        }
      }
    };
    if (media.addEventListener) {
      media.addEventListener("change", handle_system_change);
    } else if (media.addListener) {
      media.addListener(handle_system_change);
    }
  }

  apply_theme(initial_theme, false);
}
