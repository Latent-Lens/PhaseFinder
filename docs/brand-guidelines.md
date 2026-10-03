# PhaseFinder Brand Asset & Usage Guidelines

**Task:** BRAND-01 (P3)  
**Agency Reference:** AUDIT-015  
**Author:** Gemini 3.8 Flash High  
**Date:** 2026-09-08  

---

## 1. Scope and Purpose

This specification governs the visual presentation, clearspace boundaries, minimum display dimensions, and surface-specific usage rules for PhaseFinder brand marks across application interfaces, documentation, exported artifacts, and companion surfaces.

Adherence prevents visual degradation, legibility loss, and brand drift as new surfaces (e.g. Help Center, exported PDF/HTML reports, and social preview cards) are added.

---

## 2. Master Asset Inventory

| Asset Path | Type | Native Dimensions | Purpose & Permitted Context |
|---|---|---|---|
| [`assets/img/logo.png`](../assets/img/logo.png) | 32-bit RGBA PNG | 1593 × 331 px | Primary horizontal wordmark with stylized phase-curve symbol. Used for application headers and documentation. |
| [`assets/img/favicon/favicon-32x32.png`](../assets/img/favicon/favicon-32x32.png) | 32-bit RGBA PNG | 32 × 32 px | Standard desktop browser tab favicon. |
| [`assets/img/favicon/favicon-16x16.png`](../assets/img/favicon/favicon-16x16.png) | 32-bit RGBA PNG | 16 × 16 px | High-density / small-format browser tab icon. |
| [`assets/img/favicon/apple-touch-icon.png`](../assets/img/favicon/apple-touch-icon.png) | 32-bit RGBA PNG | 180 × 180 px | iOS home screen / touch device bookmark icon. |
| [`assets/img/favicon/android-chrome-192x192.png`](../assets/img/favicon/android-chrome-192x192.png) | 32-bit RGBA PNG | 192 × 192 px | Android PWA launcher icon. |
| [`assets/img/favicon/android-chrome-512x512.png`](../assets/img/favicon/android-chrome-512x512.png) | 32-bit RGBA PNG | 512 × 512 px | Android PWA splash screen and high-resolution maskable icon. |

---

## 3. Clearspace Requirements

To preserve visual prominence and brand authority, a mandatory clearspace zone must surround the horizontal logo mark on all surfaces.

1. **Clearspace Definition:**  
   The minimum exclusion zone on all four sides (top, bottom, left, right) is defined as:
   $$\text{Clearspace} \ge 0.25 \times H$$
   where $H$ is the rendered display height of the logo.
2. **Absolute Minimum Clearspace:**  
   In digital layouts, clearspace must never fall below **12 CSS pixels** (`0.75rem`) regardless of display scaling.
3. **Exclusion Rule:**  
   No text, buttons, dividers, borders, or background patterns may encroach within the clearspace boundary.

---

## 4. Minimum Display Dimensions

The horizontal wordmark incorporates fine geometric curve lines representing cell-cycle Gaussian components. Below specific size thresholds, these details become illegible or aliased:

1. **Digital Displays (Web / UI):**
   - **Minimum Rendered Height:** **28 CSS pixels** (which yields an intrinsic rendered width of approximately 135 CSS pixels at the native 4.81:1 aspect ratio).
   - **Enforcement:** Never render the horizontal logo at a height smaller than 28px.
2. **High-Resolution Export / Print (Reports / Vector Overlays):**
   - **Minimum Print Height:** **10 mm** (0.40 inches, or 120 physical pixels at 300 DPI).
3. **Sub-28px Small-Format Surfaces:**
   - On surfaces smaller than 28px (such as browser tabs or list-item bullet markers), **do not downscale the horizontal wordmark**.
   - Instead, use the dedicated square icon assets from `assets/img/favicon/` (`favicon-16x16.png`, `favicon-32x32.png`), which isolate the primary peak emblem.

---

## 5. Surface Specifications

### 5.1 Primary Surface: Main Application Header
- **Target File:** [`index.html`](../index.html) (`<img id="site_logo" class="site_logo">`)
- **Stylesheet:** [`css/layout.css`](../css/layout.css)
- **Rendered Size:** `width: min(260px, 100%); height: auto;` (evaluates to ~54 CSS pixels high on desktop).
- **Clearspace Compliance:** Enforced via flexbox alignment in `.header_brand` with `gap: 12px` and header action margins.

### 5.2 Second Surface: Help Center Header
- **Target Files:** [`help/index.html`](../help/index.html), [`help/*.html`](../help/) (`<img class="help_header_logo">`)
- **Stylesheet:** [`css/help.css`](../css/help.css)
- **Rendered Size:** `height: 42px; width: auto;` (evaluates to ~202 CSS pixels wide). Exceeds the 28px minimum height requirement.
- **Clearspace Compliance:** Enforced via `.help_header` padding (`10px 24px`) and flex gap (`gap: 16px; margin-left: 30px` to title).

### 5.3 Exported Artifacts & Printable Reports
- **Target Module:** [`js/analysis/cell_cycle/export.js`](../js/analysis/cell_cycle/export.js) / standalone report generators.
- **Rules:**
  - Printable HTML / PDF report headers must embed `logo.png` with an explicit height between **32px and 48px**.
  - A minimum top, bottom, and side margin of **16px** must isolate the logo from report metadata tables and summary cards.
  - Image aspect ratio must remain locked (`height: auto` or matched aspect ratio attributes `width="X" height="Y"` maintaining 1593:331).

---

## 6. Prohibited Practices

To protect brand coherence, the following treatments are strictly forbidden across all current and future surfaces:

1. **Aspect Ratio Distortion:** Do not stretch, compress, or disproportionately scale the horizontal mark.
2. **Recoloring & Filtering:** Do not alter the logo's color palette, invert hues, or apply CSS color drop-shadows.
3. **Text Replacement:** Do not reconstruct the wordmark using system fonts or arbitrary typographic styling.
4. **Low Contrast Placement:** Do not place the logo on busy photographic backgrounds or surfaces where it is hard to distinguish.
