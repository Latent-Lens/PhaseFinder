const fs = require("node:fs");
const { execFileSync } = require("node:child_process");

const modelDir = "js/analysis/cell_cycle/models";
const git = (...args) => {
  try {
    return execFileSync("git", args, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  } catch {
    return null;
  }
};

const local = git("diff", "--name-only", "HEAD", "--", modelDir)?.trim();
const base = local ? "HEAD" : "HEAD^";
const range = local ? [base] : [base, "HEAD"];
const changed = git("diff", "--name-only", ...range, "--", modelDir);
if (changed?.trim()) {
  const versions = fs.readdirSync(modelDir).filter((name) => name.endsWith(".js"))
    .map((name) => `${modelDir}/${name}`);
  const version = (source) => source?.match(/^\s{2}version:\s*"([^"]+)"/m)?.[1];
  const bumped = versions.some((path) => {
    const oldVersion = version(git("show", `${base}:${path}`));
    const newVersion = version(fs.readFileSync(path, "utf8"));
    return oldVersion && newVersion && oldVersion !== newVersion;
  });
  const notesDiff = git("diff", "-U0", ...range, "--", "CHANGELOG.md") ?? "";
  const untrackedNotes = local && git("status", "--short", "--", "CHANGELOG.md")?.startsWith("??");
  const notesAdded = /^\+(?!\+\+)\s*-\s+\S/m.test(notesDiff)
    || (untrackedNotes && /^\s*-\s+\S/m.test(fs.readFileSync("CHANGELOG.md", "utf8")));
  if (!bumped) console.warn("Warning: model files changed without a model-version bump.");
  if (!notesAdded) console.warn("Warning: model files changed without a CHANGELOG.md entry.");
}
