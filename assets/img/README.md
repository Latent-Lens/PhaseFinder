# PhaseFinder Image Assets & Brand Usage

This directory contains visual brand assets, iconography, and UI illustration files for PhaseFinder.

## Master Logo

- **Source File:** `logo.png`
- **Dimensions:** 1593 × 331 px (32-bit RGBA PNG, transparent)
- **Full Specification:** See [`docs/brand-guidelines.md`](../../docs/brand-guidelines.md).

### Quick Usage Rules

1. **Minimum Display Size:**
   - Digital UI: minimum height **28 CSS pixels** (approx. 135 CSS pixels wide).
   - Never render the horizontal wordmark below 28px height; use dedicated square icons in `favicon/` for compact representations.
2. **Clearspace:**
   - Minimum clearspace of $0.25 \times H$ (and at least **12 CSS pixels**) required on all four sides. No text or UI controls may encroach into this exclusion zone.
3. **Surfaces:**
   - **Primary Surface (App Header):** `.site_logo` in `css/layout.css` (`width: min(260px, 100%)`, ~54px height).
   - **Second Surface (Help Center):** `.help_header_logo` in `css/help.css` (`height: 42px; width: auto`).
   - **Reports & Exports:** When embedding in printable HTML or PDF reports, render at height between 32px and 48px with at least 16px padding.
