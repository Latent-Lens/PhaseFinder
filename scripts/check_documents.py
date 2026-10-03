#!/usr/bin/env python3
"""Validate public and internal documentation links, HTML, tracker freshness/parser, manifest, TOML, and UI labels."""

import contextlib
import html
import io
import json
import re
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_checklist_status as tracker
import test_checklist_status

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
ARCHIVE_DIR = ROOT / "docs/archive"

# DOC-05: Explicit archive exceptions for historical code references in docs/archive/
# Historical documents reference older architectures and specific lines of code.
# Navigational links between documents must still resolve cleanly.
HISTORICAL_LINE_ANCHOR_RE = re.compile(r"^L?\d+(?:-L?\d+)?$")
HISTORICAL_ARCHIVE_EXCEPTIONS = set()

errors = []


class DocumentParser(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack = []
        self.ids = set()
        self.references = []
        self.ui_labels = []
        self._label_depth = 0
        self._label_text = []
        self.has_lang = False
        self.has_title = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "html" and values.get("lang", "").strip():
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        if values.get("id"):
            if values["id"] in self.ids:
                errors.append(f"{self.path}: duplicate id #{values['id']}")
            self.ids.add(values["id"])
        for name in ("href", "src"):
            if values.get(name):
                self.references.append(values[name])
        classes = values.get("class", "").split()
        if "ui_label" in classes:
            self._label_depth = len(self.stack) + 1
            self._label_text = []
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            found = self.stack[-1] if self.stack else "nothing"
            errors.append(f"{self.path}: closing </{tag}> found after <{found}>")
            return
        if self._label_depth == len(self.stack):
            label = " ".join("".join(self._label_text).split())
            if label:
                self.ui_labels.append(label)
            self._label_depth = 0
            self._label_text = []
        self.stack.pop()

    def handle_data(self, data):
        if self._label_depth:
            self._label_text.append(data)

    def close(self):
        super().close()
        if self.stack:
            errors.append(f"{self.path}: unclosed tag <{self.stack[-1]}>")


def verify_tracker_freshness():
    """Verify that the generated tracker HTML is byte-for-byte fresh with the checklist Markdown."""
    if not tracker.CHECKLIST.exists():
        errors.append(f"{tracker.CHECKLIST.relative_to(ROOT)}: missing checklist markdown")
        return
    if not tracker.TEMPLATE.exists():
        errors.append(f"{tracker.TEMPLATE.relative_to(ROOT)}: missing checklist template")
        return
    if not tracker.OUTPUT.exists():
        errors.append(f"{tracker.OUTPUT.relative_to(ROOT)}: missing generated tracker file; run python3 scripts/build_checklist_status.py")
        return
    try:
        source = tracker.CHECKLIST.read_text(encoding="utf-8")
        template = tracker.TEMPLATE.read_text(encoding="utf-8")
        rendered, _ = tracker.render_document(source, template)
        current = tracker.OUTPUT.read_text(encoding="utf-8")
        if rendered != current:
            errors.append(
                f"{tracker.OUTPUT.relative_to(ROOT)}: tracker is stale; run 'python3 scripts/build_checklist_status.py'"
            )
    except Exception as exc:
        errors.append(f"Failed to verify tracker freshness: {exc}")


def verify_tracker_parser():
    """Run regression tests for checklist parser and tracker rendering."""
    try:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            test_checklist_status.main()
    except Exception as exc:
        errors.append(f"scripts/test_checklist_status.py regression failure: {exc}")


verify_tracker_freshness()
verify_tracker_parser()

html_paths = [
    ROOT / "index.html",
    *sorted((ROOT / "help").glob("*.html")),
    ROOT / "docs/audits/master_checklist_status.html",
    ROOT / "docs/audits/checklist_status_template.html",
    ROOT / "docs/document_inventory.html",
    ROOT / "docs/code-flow-diagrams.html",
    ROOT / "docs/function-call-and-user-decision-graphs.html",
    ROOT / "docs/project-directory-tree.html",
]

parsed = {}
for path in html_paths:
    if not path.exists():
        errors.append(f"{path.relative_to(ROOT)}: html file missing")
        continue
    parser = DocumentParser(path.relative_to(ROOT))
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    parsed[path.resolve()] = parser
    if not parser.has_lang:
        errors.append(f"{path.relative_to(ROOT)}: missing html lang")
    if not parser.has_title:
        errors.append(f"{path.relative_to(ROOT)}: missing title")


def check_target(source, raw, is_archive=False):
    if not raw or raw.startswith(("#", "data:", "mailto:", "tel:", "javascript:")):
        return
    parts = urlsplit(raw)
    if parts.scheme or parts.netloc or "{{" in raw:
        return
    rel_source = source.relative_to(ROOT)
    if is_archive and (str(rel_source), raw) in HISTORICAL_ARCHIVE_EXCEPTIONS:
        return
    target = (ROOT / unquote(parts.path.lstrip("/"))) if parts.path.startswith("/") else (source.parent / unquote(parts.path))
    target = target.resolve()
    if not target.exists():
        if is_archive and (raw in HISTORICAL_ARCHIVE_EXCEPTIONS or str(target) in HISTORICAL_ARCHIVE_EXCEPTIONS):
            return
        errors.append(f"{rel_source}: missing local target {raw}")
        return
    if parts.fragment and target.suffix.lower() == ".html":
        if is_archive and HISTORICAL_LINE_ANCHOR_RE.match(unquote(parts.fragment)):
            # Explicit archive exception: line-number references in historical audit notes
            return
        parser = parsed.get(target)
        if parser is None:
            parser = DocumentParser(target.relative_to(ROOT))
            parser.feed(target.read_text(encoding="utf-8"))
            parser.close()
            parsed[target] = parser
        if unquote(parts.fragment) not in parser.ids:
            errors.append(f"{rel_source}: missing anchor {raw}")


for path in html_paths:
    if path.resolve() in parsed:
        is_archive = path.is_relative_to(ARCHIVE_DIR)
        for reference in parsed[path.resolve()].references:
            check_target(path, reference, is_archive=is_archive)

# Recursively discover all active and archive markdown documentation
markdown_paths = [
    ROOT / "README.md",
    ROOT / "THIRD_PARTY_NOTICES.md",
    ROOT / "tests/e2e/README.md",
    *sorted((ROOT / "docs").rglob("*.md")),
]
markdown_link = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
active_md_count = 0
archive_md_count = 0
for path in markdown_paths:
    if not path.exists():
        continue
    is_archive = path.is_relative_to(ARCHIVE_DIR)
    if is_archive:
        archive_md_count += 1
    else:
        active_md_count += 1
    for target in markdown_link.findall(path.read_text(encoding="utf-8")):
        check_target(path, target.strip("<>"), is_archive=is_archive)

manifest_path = ROOT / "assets/img/favicon/site.webmanifest"
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for icon in manifest.get("icons", []):
        check_target(manifest_path, icon["src"])
        if not re.fullmatch(r"\d+x\d+", icon.get("sizes", "")):
            errors.append(f"{manifest_path.relative_to(ROOT)}: invalid icon sizes {icon.get('sizes')!r}")
except (KeyError, ValueError) as error:
    errors.append(f"{manifest_path.relative_to(ROOT)}: {error}")

for path in sorted((ROOT / "assets/misc").glob("*.toml")):
    try:
        tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        errors.append(f"{path.relative_to(ROOT)}: {error}")

source_corpus = html.unescape((ROOT / "index.html").read_text(encoding="utf-8"))
source_corpus += "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "js").rglob("*.js"))
help_html_paths = sorted((ROOT / "help").glob("*.html"))
for path in help_html_paths:
    if path.resolve() in parsed:
        for label in parsed[path.resolve()].ui_labels:
            needle = html.unescape(label).replace("(N)", "(").replace("…", "")
            if needle not in source_corpus and label not in {"Loaded FCS files (N)"}:
                errors.append(f"{path.relative_to(ROOT)}: documented UI label not found in app source: {label!r}")

if errors:
    raise SystemExit("\n".join(errors))
print(
    f"Document checks passed: {len(html_paths)} HTML pages, {active_md_count} active Markdown files, "
    f"{archive_md_count} archive Markdown files, tracker freshness and parser, manifest, TOML, and Help UI labels."
)
