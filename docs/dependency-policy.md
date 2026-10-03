# Dependency update policy

Dependabot opens weekly npm, Python, and GitHub Actions updates. Every update
must keep lockfiles/pins current and pass the normal build, browser, security,
privacy, and production-artifact checks. Major updates to Vite, D3, Playwright,
or a GitHub Action require explicit maintainer review of release notes,
compatibility impact, generated artifact changes, and rollback before merge.

Runtime libraries remain vendored or lockfile-resolved; do not add a runtime CDN
or an unpinned Git/action dependency. Security fixes may be expedited, but they
still require the same automated checks and a documented reviewer.

## Module format and Node CLI CommonJS scope

The repository root `package.json` specifies `"type": "commonjs"`. This setting
governs only the Node-side build, preflight, and verification tooling
(such as `scripts/*.cjs` and root maintenance tools), ensuring deterministic
standalone execution in standard Node environments without requiring experimental
loader flags or custom module resolution shims.

In contrast, the shipped client web application is entirely native ES modules
(ESM). Browser scripts in `js/` use standard `import` and `export` statements and
are loaded via `<script type="module" src="./js/main.js">` in `index.html`.
Vite handles bundling the ESM source tree into the production static artifact
regardless of the repository's root CommonJS declaration.

