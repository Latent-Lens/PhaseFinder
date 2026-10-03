// MODEL-02: analytic Gaussian/split-Gaussian controls, independent of DJF equations.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const moduleUrlCache = new Map();

async function loadAsDataUrl(absolutePath) {
  if (moduleUrlCache.has(absolutePath)) return moduleUrlCache.get(absolutePath);
  const source = await readFile(absolutePath, "utf8");
  const specifiers = [...source.matchAll(/from\s+["'](\.[^"']+)["']/g)].map(([, specifier]) => specifier);
  const dependencyUrls = await Promise.all(
    specifiers.map(specifier => loadAsDataUrl(path.join(path.dirname(absolutePath), specifier))));
  let index = 0;
  const rewritten = source.replace(/from\s+["'](\.[^"']+)["']/g, () => `from "${dependencyUrls[index++]}"`);
  const url = `data:text/javascript;base64,${Buffer.from(rewritten).toString("base64")}`;
  moduleUrlCache.set(absolutePath, url);
  return url;
}

async function importAppModule(relativePath) {
  return import(await loadAsDataUrl(path.join(root, relativePath)));
}


const { estimatePeakFromRegion } = await importAppModule('js/analysis/cell_cycle/peak_regions.js');
const rows = [];
for (const sigma of [6, 11, 22]) {
  for (const kernel of [0, 1, 2, 4]) {
    for (const pedestal of [0, 200]) {
      for (const skew of [1, 1.321]) {
        const edges = Array.from({length: 1602}, (_, i) => (i - 800.5) * 0.25);
        const counts = edges.slice(1).map((right, i) => {
          const x = (right + edges[i]) / 2;
          return pedestal + 1000 * Math.exp(-0.5 * (x / (x > 0 ? sigma * skew : sigma)) ** 2);
        });
        const estimate = estimatePeakFromRegion(edges, counts,
          {left: -6 * sigma, right: 6 * sigma}, {cleanSide: 'left', smoothingSigmaBins: kernel});
        const error = 100 * (estimate.sigma / sigma - 1);
        // Broad resolved peaks: deconvolution/pedestal must not narrow the clean flank by 5%.
        assert.ok(Math.abs(error) < 5, JSON.stringify({sigma, kernel, pedestal, skew, error}));
        rows.push({sigma, kernel, pedestal, skew, estimatedSigma: estimate.sigma, errorPercent: error});
      }
    }
  }
}
console.log(JSON.stringify({cases: rows.length, minErrorPercent: Math.min(...rows.map(r => r.errorPercent)),
  maxErrorPercent: Math.max(...rows.map(r => r.errorPercent)), rows}, null, 2));
