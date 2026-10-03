#!/usr/bin/env python3
"""Build the human-intervention handoff page from the master checklist.

The page groups by *root ask* rather than by task. Many blocked tasks wait on
the same dataset, the same sign-off or the same credential, so listing one card
per task overstates how much a person actually has to supply. Roots are defined
in the checklist's "Human intervention roots" table and named per task with a
``**Human Intervention Root:**`` field.

Plain-language explanations and recommendations come from a hand-written
guide (``human_intervention_guide.md``). Its ``## HI-… — Title`` sections go on
the matching cards, and its other ``## `` sections go at the top of the page.
A card with no guide section falls back to the checklist's wording.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path

from build_checklist_status import CHECKLIST, inline, parse_checklist, render_body


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/audits/human_intervention_status.html"
GUIDE = ROOT / "docs/audits/human_intervention_guide.md"
ROOTS_HEADING = "### Human intervention roots"
ROW_RE = re.compile(r"^\|\s*`(HI-[A-Z0-9]+)`\s*\|(.+)\|\s*$")
GUIDE_ROOT_RE = re.compile(r"^## (HI-[A-Z0-9]+) — (.+)$")
GUIDE_INTRO, GUIDE_GLOSSARY = "Start here", "Words you'll see"
GUIDE_BUNDLE = "Everything I need from you, in one list"
PRIORITY_ORDER = ("P0", "P1", "P2", "P3")

TRIAGE_ROOT = {
    "id": "HI-UNASSIGNED",
    "title": "Blocked without a named root — needs triage",
    "supply": "Nothing, until the block is explained. Each task below carries a `Human Intervention Needed` flag but no `Human Intervention Root`, so the handoff cannot say what a person is meant to provide.",
    "why": "A task held for a person without naming what the person must supply cannot be acted on and cannot be closed. Either give it a root from the table in the checklist, or remove the flag if the task is not in fact waiting on anyone.",
}


def parse_roots(text: str) -> list[dict]:
    """Read the root definitions from the checklist's roots table."""
    roots, inside = [], False
    for line in text.splitlines():
        if line.startswith(ROOTS_HEADING):
            inside = True
            continue
        if inside and line.startswith("#"):
            break
        if not inside:
            continue
        match = ROW_RE.match(line.strip())
        if match:
            cells = [cell.strip() for cell in match[2].split("|")]
            if len(cells) < 3:
                raise ValueError(f"Root row needs title, supply and why columns: {match[1]}")
            roots.append({"id": match[1], "title": cells[0], "supply": cells[1], "why": cells[2]})
    if not roots:
        raise ValueError(f"No root definitions found under {ROOTS_HEADING!r}")
    return roots


def parse_guide(text: str) -> dict:
    """Split the hand-written guide on its ``## `` headings.

    Returns page-level sections keyed by heading text, per-root sections keyed
    by root id, and the order the root sections appear in (the suggested order
    of work). Anything before the first ``## `` is a note to editors and is
    not rendered.
    """
    sections: dict[str, list[str]] = {}
    roots: dict[str, dict] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            match = GUIDE_ROOT_RE.match(line)
            if match:
                if match[1] in roots:
                    raise ValueError(f"Guide has two sections for {match[1]}")
                roots[match[1]] = {"title": match[2].strip(), "lines": []}
                current = roots[match[1]]["lines"]
            else:
                current = sections.setdefault(line[3:].strip(), [])
            continue
        if current is not None:
            current.append(line)
    return {"sections": sections, "roots": roots, "order": list(roots)}


def guide_drift(groups: list[dict], guide: dict) -> list[str]:
    """Name the places the hand-written guide no longer matches the checklist."""
    held = {group["id"] for group in groups}
    notes = [
        f"{root_id}: guide section present, but no blocked task names this root any more"
        for root_id in guide["order"]
        if root_id not in held
    ]
    notes += [
        f"{group['id']}: no guide section, so the card falls back to the checklist's wording"
        for group in groups
        if group["id"] != TRIAGE_ROOT["id"] and group["id"] not in guide["roots"]
    ]
    return notes


# Answers typed into the page are kept in this JSON block. The page writes it
# when the person saves, and main() carries it into every rebuild so
# regenerating the page never loses them.
ANSWERS_RE = re.compile(r'(<script id="saved-answers" type="application/json">)(.*?)(</script>)', re.S)
# `{answer: KEY}` or `{answer: KEY | question}` in the guide marks where an
# answer box goes. The same key on the one-list and on a card is one answer.
MARKER_RE = r"\{answer: ([^}|]+?)\s*(?:\|\s*([^}]+?))?\s*\}"


def plain_text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def answer_box(key: str, label: str, question: str) -> str:
    return (
        f'<div class="answer"><label>{html.escape(label)}'
        f'<textarea data-answer-key="{html.escape(key)}" data-question="{html.escape(question)}" rows="3" '
        f'placeholder="Type your answer or notes. They save as you type."></textarea></label></div>'
    )


def box_label(key: str) -> str:
    tail = key.rsplit("/", 1)[-1]
    return f"Your answer to {tail}" if re.fullmatch(r"D\d+", tail) else "Your answer"


def fill_answer_boxes(body: str, keys: list[str], anchors: set[str] | None = None, linked: set[str] = frozenset()) -> str:
    """Turn the guide's answer markers into answer boxes.

    On cards (``anchors`` given) the first list item carrying a key gets the
    id ``q-KEY`` so the one-list can link to it. On the one-list, items whose
    key also appears on a card get a *Full detail* link. Every key used is
    appended to ``keys``.
    """
    def item(match: re.Match) -> str:
        content, key, question = match[1], match[2].strip(), match[3]
        keys.append(key)
        strong = re.match(r"\s*<strong>(.*?)</strong>", content, re.S)
        question = question or (plain_text(strong[1]) if strong else plain_text(content)[:160])
        attrs, link = "", ""
        if anchors is not None and key not in anchors:
            anchors.add(key)
            attrs = f' id="q-{html.escape(key)}"'
        if key in linked:
            link = f' <a class="detail-link" href="#q-{html.escape(key)}">Full detail</a>'
        return f"<li{attrs}>{content.rstrip()}{link}{answer_box(key, box_label(key), question)}</li>"

    def paragraph(match: re.Match) -> str:
        key = match[1].strip()
        keys.append(key)
        return answer_box(key, box_label(key), match[2] or "Your answer")

    body = re.sub(r"<li>((?:(?!</li>).)*?)\s*" + MARKER_RE + r"\s*</li>", item, body, flags=re.S)
    return re.sub(r"<p>\s*" + MARKER_RE + r"\s*</p>", paragraph, body)


def keep_saved_answers(page: str, previous: str | None) -> str:
    """Carry the answers saved in the previous page into the freshly built one."""
    match = previous and ANSWERS_RE.search(previous)
    if not match:
        return page
    return ANSWERS_RE.sub(lambda m: m[1] + match[2] + m[3], page, count=1)


def group_by_root(items: list[dict], roots: list[dict]) -> list[dict]:
    """Attach each blocked task to every root it names, newest flag first."""
    known = {root["id"]: dict(root, tasks=[]) for root in roots}
    triage = dict(TRIAGE_ROOT, tasks=[])
    for item in items:
        named = [
            name.strip()
            for name in item["fields"].get("Human Intervention Root", "").split(",")
            if name.strip()
        ]
        unknown = [name for name in named if name not in known]
        if unknown:
            raise ValueError(f"{item['id']} names undefined root(s): {', '.join(unknown)}")
        for name in named or []:
            known[name]["tasks"].append(item)
        if not named:
            triage["tasks"].append(item)
    groups = [root for root in known.values() if root["tasks"]]
    if triage["tasks"]:
        groups.append(triage)
    for group in groups:
        counts = Counter(task["priority"] for task in group["tasks"])
        group["priority"] = min(counts, key=PRIORITY_ORDER.index)
        group["priorities"] = [p for p in PRIORITY_ORDER if counts[p]]
        group["breakdown"] = " ".join(f"{p}×{counts[p]}" for p in group["priorities"])
        group["tasks"].sort(key=lambda task: (PRIORITY_ORDER.index(task["priority"]), task["id"]))
    groups.sort(key=lambda group: (PRIORITY_ORDER.index(group["priority"]), -len(group["tasks"])))
    return groups


def task_block(item: dict, current_root: str) -> str:
    fields = item["fields"]
    review = next(
        (fields[key] for key in sorted(fields, reverse=True) if key.startswith("Review (")),
        "No current review recorded.",
    )
    reason = fields.get("Human Intervention Reason", "No reason recorded.")
    blocked_by = fields.get("Blocked By", "Not recorded")
    blocked_at = fields.get("Human Intervention Needed", "Not recorded")
    # Only the *other* roots this task names; the card it is rendered under is
    # not news to the reader.
    also = [
        name.strip()
        for name in fields.get("Human Intervention Root", "").split(",")
        if name.strip() and name.strip() != current_root
    ]
    shared = (
        '<p class="also">Not closed by this ask alone — also waits on {}.</p>'.format(
            ", ".join(
                '<a href="#{0}--{1}"><code>{0}</code></a>'.format(
                    html.escape(name), html.escape(item["id"])
                )
                for name in also
            )
        )
        if also
        else ""
    )
    return f'''<article class="task" id="{html.escape(current_root)}--{html.escape(item["id"])}" data-task-id="{html.escape(item["id"])}" data-priority="{item["priority"]}">
  <h3>{html.escape(item["id"])} · {html.escape(item["priority"])} — {inline(item["title"])}</h3>
  <div class="meta"><span>Acceptance boxes: {item["ticked"]}/{item["total"]}</span><span>Blocked by: {html.escape(blocked_by)}</span><span>Human flag: {html.escape(blocked_at)}</span></div>
  <p class="task-reason"><strong>What this task needs specifically:</strong> {inline(reason)}</p>
  {shared}
  <details>
    <summary>Background, evidence, and acceptance checklist</summary>
    <div class="source-text">
      <p class="why"><strong>Why this matters:</strong> {inline(review)}</p>
      <p class="recommendation"><strong>Recommended next step:</strong> {inline(fields.get("Recommendation", "Review the checklist and record the decision."))}</p>
      {render_body(item["body"])}
    </div>
  </details>
</article>'''


def card(group: dict, plain: dict | None, keys: list[str], anchors: set[str]) -> str:
    count = len(group["tasks"])
    plural = "task" if count == 1 else "tasks"
    ids = " ".join(task["id"] for task in group["tasks"])
    chips = " ".join(
        f'<a class="chip" href="#{html.escape(group["id"])}--{html.escape(task["id"])}">{html.escape(task["id"])}</a>'
        for task in group["tasks"]
    )
    tasks = "\n".join(task_block(task, group["id"]) for task in group["tasks"])
    if plain:
        # The guide's wording leads; the checklist's terser wording and the
        # per-task detail stay on the card, one click away, for agents.
        heading = f'''<h2>{inline(plain["title"])}</h2>
      <p class="subtitle">Checklist name: {inline(group["title"])}</p>'''
        explained = f'''<section class="plain">
{fill_answer_boxes(render_body(plain["lines"]), keys, anchors)}
{answer_box(group["id"] + "/notes", "Your notes on this ask", "General notes")}
  </section>
  <details class="technical">
    <summary>Technical wording from the checklist</summary>
    <p><strong>What to supply:</strong> {inline(group["supply"])}</p>
    <p><strong>Why a person has to do this:</strong> {inline(group["why"])}</p>
  </details>'''
        held = f'''<h3>Checklist tasks this unblocks</h3>
    <p class="chips">{chips}</p>
    <details class="held">
      <summary>Show all {count} {plural} in technical detail</summary>
      {tasks}
    </details>'''
    else:
        heading = f"<h2>{inline(group['title'])}</h2>"
        explained = f'''<section class="human-needed">
    <h3>What to supply</h3>
    <p>{inline(group["supply"])}</p>
  </section>
  <section>
    <h3>Why a person has to do this</h3>
    <p>{inline(group["why"])}</p>
  </section>
  {answer_box(group["id"] + "/notes", "Your notes on this ask", "General notes")}'''
        held = f'''<h3>Held on this ask</h3>
    <p class="chips">{chips}</p>
    {tasks}'''
    return f'''<article class="card" id="{html.escape(group["id"])}" data-priority="{group["priority"]}" data-priorities="{" ".join(group["priorities"])}" data-task-ids="{html.escape(ids)}">
  <header class="card-header">
    <div>
      <p class="eyebrow">{html.escape(group["id"])} · unblocks {count} {plural} · {html.escape(group["breakdown"])}</p>
      {heading}
    </div>
    <label class="complete-toggle"><input class="completion" type="checkbox" data-task-id="{html.escape(group["id"])}" aria-label="Mark {html.escape(group["id"])} supplied"> <span>Supplied</span></label>
  </header>
  {explained}
  <section class="blocked-list">
    {held}
  </section>
  <footer><strong>Agent handoff:</strong> An agent may prepare code and evidence around these items, but should not mark the human dependency complete or claim a task until this ask is satisfied and recorded in <code>docs/audits/master_checklist.md</code>.</footer>
</article>'''


def guide_header(guide: dict) -> str:
    intro = guide["sections"].get(GUIDE_INTRO)
    glossary = guide["sections"].get(GUIDE_GLOSSARY)
    if not intro and not glossary:
        return ""
    parts = ['<section class="guide" aria-labelledby="start-here">']
    if intro:
        parts += [f'  <h2 id="start-here">{html.escape(GUIDE_INTRO)}</h2>', render_body(intro)]
    if glossary:
        parts += [
            '  <details class="glossary">',
            f"    <summary>{html.escape(GUIDE_GLOSSARY)}: open this if a term is unfamiliar</summary>",
            render_body(glossary),
            "  </details>",
        ]
    parts.append("</section>")
    return "\n".join(parts)


def bundle_section(guide: dict, card_keys: list[str], anchors: set[str]) -> tuple[str, list[str]]:
    """The one-list of every question, each sharing its box with the card."""
    lines = guide["sections"].get(GUIDE_BUNDLE)
    if not lines:
        return "", []
    keys: list[str] = []
    body = fill_answer_boxes(render_body(lines), keys, linked=anchors)
    notes = [f"{key}: answer box on a card but not in the one-list" for key in dict.fromkeys(card_keys) if key not in keys]
    notes += [f"{key}: in the one-list but on no card" for key in keys if key not in card_keys]
    return (
        f'<section class="guide bundle" id="everything">\n  <h2>{html.escape(GUIDE_BUNDLE)}</h2>\n{body}\n</section>',
        notes,
    )


def build(markdown: str, guide_text: str = "") -> tuple[str, list[str]]:
    """Return the page and any notes on where the guide has drifted."""
    items = [item for item in parse_checklist(markdown) if item["human_intervention"]]
    roots = parse_roots(markdown)
    guide = parse_guide(guide_text)
    unknown = [root_id for root_id in guide["order"] if root_id not in {root["id"] for root in roots}]
    if unknown:
        raise ValueError(f"Guide has sections for undefined root(s): {', '.join(unknown)}")
    groups = group_by_root(items, roots)
    # Guide order is the suggested order of work. The sort is stable, so roots
    # the guide doesn't cover keep their priority order after it, and triage
    # stays last.
    rank = {root_id: index for index, root_id in enumerate(guide["order"])}
    groups.sort(key=lambda group: (group["id"] == TRIAGE_ROOT["id"], rank.get(group["id"], len(rank))))
    priority_counts = Counter(p for group in groups for p in group["priorities"])
    priority_options = "".join(
        f'<option value="{priority}">{priority} ({priority_counts[priority]})</option>'
        for priority in PRIORITY_ORDER
        if priority_counts[priority]
    )
    priority_summary = " · ".join(
        f"{priority}: {priority_counts[priority]}"
        for priority in PRIORITY_ORDER
        if priority_counts[priority]
    )
    page = PAGE.replace("__TOTAL__", str(len(groups)))
    page = page.replace("__TASK_TOTAL__", str(len(items)))
    page = page.replace("__PRIORITY_SUMMARY__", html.escape(priority_summary))
    page = page.replace("__PRIORITY_OPTIONS__", priority_options)
    page = page.replace("__GUIDE__", guide_header(guide))
    card_keys: list[str] = []
    anchors: set[str] = set()
    cards = "\n".join(card(group, guide["roots"].get(group["id"]), card_keys, anchors) for group in groups)
    bundle, bundle_notes = bundle_section(guide, card_keys, anchors)
    page = page.replace("__BUNDLE__", bundle)
    page = page.replace("__CARDS__", cards)
    return page, guide_drift(groups, guide) + bundle_notes


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>PhaseFinder · Human intervention handoff</title>
<style>
:root{color-scheme:light;--ink:#172b42;--muted:#50657a;--line:#a8b6c5;--paper:#fff;--bg:#eef3f8;--accent:#174fa0;--warn:#795000;--warn-bg:#fff8df;--done:#24633a;--done-bg:#edf8ef}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:34px 22px 70px}a{color:var(--accent)}h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.12;margin:8px 0 12px}h2{font-size:1.5rem;line-height:1.3;margin:0}h3{font-size:1rem;margin:0 0 7px}.intro{max-width:850px;color:var(--muted)}.eyebrow{color:var(--accent);font-size:.8rem;font-weight:750;letter-spacing:.12em;margin:0 0 5px;text-transform:uppercase}.note{background:var(--warn-bg);border:1px solid #d2b45c;border-radius:8px;padding:12px 16px}.counters{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:24px 0}.counter,.filters,.card{background:var(--paper);border:1px solid var(--line);border-radius:10px}.counter{border-top:4px solid var(--accent);padding:15px}.counter strong{display:block;font-size:2.2rem;line-height:1.2}.counter span{color:var(--muted)}.filters{display:flex;flex-wrap:wrap;gap:14px;margin:18px 0;padding:16px}.filters label{display:flex;flex-direction:column;gap:4px;font-size:.85rem;font-weight:650;flex:1 1 240px}.filters input,.filters select,.filters button{font:inherit;min-height:42px;padding:8px;border:1px solid var(--line);border-radius:5px;background:white;color:inherit}.filters button{align-self:end;cursor:pointer}.card{margin:18px 0;padding:22px;scroll-margin-top:18px}.card[hidden]{display:none}.card.is-complete{border-color:#75a987;background:var(--done-bg)}.card#HI-UNASSIGNED{border-color:#c39116;border-left-width:5px}.card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.complete-toggle{display:flex;align-items:center;gap:8px;white-space:nowrap;color:var(--done);font-weight:700}.complete-toggle input{width:20px;height:20px}.meta{display:flex;flex-wrap:wrap;gap:7px 16px;margin:8px 0 12px;color:var(--muted);font-size:.88rem}.meta span{border-left:3px solid var(--line);padding-left:8px}.card section{margin:20px 0}.human-needed{background:var(--warn-bg);border-left:4px solid #c39116;border-radius:5px;padding:12px 15px}.recommendation{border-left:3px solid #54769c;padding-left:14px}.blocked-list{border-top:1px solid var(--line);padding-top:16px}.chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px}.chip{background:var(--bg);border:1px solid var(--line);border-radius:999px;font-size:.85rem;font-weight:700;padding:5px 12px;text-decoration:none}.task{border-top:1px solid #dbe3ec;margin-top:14px;padding-top:14px;scroll-margin-top:18px}.task h3{font-size:1.02rem;margin:0 0 4px}.task-reason{margin:6px 0}.also{color:var(--muted);font-size:.9rem;margin:6px 0 0}.card details{margin-top:12px}.card summary{cursor:pointer;color:var(--accent);font-weight:700;min-height:42px;align-content:center}.source-text{overflow:auto}.source-text p{margin:8px 0 13px}.source-text ul{padding-left:24px}.source-text li{margin:5px 0}.source-text code{font-size:.9em}.card footer{border-top:1px solid var(--line);color:var(--muted);font-size:.9rem;margin-top:20px;padding-top:14px}#visible-count{color:var(--muted)}.subtitle{color:var(--muted);font-size:.9rem;margin:4px 0 0}.guide{background:var(--paper);border:1px solid var(--line);border-top:4px solid var(--accent);border-radius:10px;margin:22px 0;padding:18px 22px}.guide>h2{margin:0 0 8px}.guide p,.guide ol,.guide ul,.plain{max-width:80ch}.guide h4,.plain h4{font-size:1.05rem;margin:22px 0 6px}.plain h4:first-child{margin-top:0}.guide ol,.guide ul,.plain ol,.plain ul{padding-left:26px}.guide li,.plain li{margin:9px 0}.guide p,.plain p{margin:8px 0 12px}.guide table,.plain table{border-collapse:collapse;width:100%;margin:10px 0 14px;font-size:.95rem}.guide th,.guide td,.plain th,.plain td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}.guide th,.plain th{background:var(--bg)}.guide code,.plain code{overflow-wrap:anywhere}.glossary{margin-top:16px}.glossary summary{cursor:pointer;color:var(--accent);font-weight:700;min-height:42px;align-content:center}.technical{background:var(--bg);border-radius:6px;padding:2px 14px}.technical p{margin:8px 0}[hidden]{display:none!important}.answer{margin:8px 0 14px}.answer label{display:flex;flex-direction:column;gap:4px;font-size:.85rem;font-weight:700;color:var(--accent)}.answer textarea{font:15px/1.5 system-ui,sans-serif;color:var(--ink);background:#fbfdff;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:8px 10px;resize:vertical;min-height:4.8em;max-width:80ch;width:100%}.answer textarea.has-answer{background:#f3f9f4;border-left-color:var(--done)}.plain .answer{max-width:80ch}.answers-bar{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;background:var(--paper);border:1px solid var(--line);border-top:4px solid var(--done);border-radius:10px;padding:10px 16px;margin:18px 0;box-shadow:0 4px 14px rgba(23,43,66,.08)}.answers-bar button{font:inherit;font-weight:700;min-height:38px;padding:6px 14px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);cursor:pointer}.answers-bar button.primary{background:var(--done);border-color:var(--done);color:#fff}#answer-status{color:var(--muted);font-size:.9rem;flex:1 1 260px}#answer-status.unsaved{color:var(--warn);font-weight:700}.orphans{background:var(--warn-bg);border:1px solid #d2b45c;border-radius:10px;padding:14px 18px;margin:18px 0}.bundle h4{font-size:1.05rem;margin:22px 0 4px;color:var(--accent)}.bundle ol{padding-left:26px}.bundle li{margin:12px 0}.detail-link{font-size:.85rem;font-weight:700;white-space:nowrap}.orphans pre{white-space:pre-wrap;font:14px/1.5 system-ui,sans-serif;margin:4px 0 12px}
</style>
</head>
<body><main>
<header>
  <p class="eyebrow">PhaseFinder · Human handoff</p>
  <h1>What I need from you</h1>
  <p class="intro">Right now __TASK_TOTAL__ checklist tasks are stuck waiting on a person. Many wait on the same thing, so they come down to __TOTAL__ asks. Each card below is one ask. Satisfy it and every task under it can move again.</p>
  <p><a href="master_checklist_status.html">Back to the master status board</a> · <a href="master_checklist.md">Markdown source</a> · <a href="human_intervention_guide.md">Plain-language guide source</a></p>
</header>
__GUIDE__
<div class="answers-bar">
  <span id="answer-status">No answers yet.</span>
  <button id="save-answers" type="button" class="primary">Save answers into this file</button>
  <button id="copy-answers" type="button">Copy all answers</button>
</div>
<p class="note"><strong>Answering here:</strong> Type under any question. Everything saves in this browser as you type. To keep it in the file itself, click <em>Save answers into this file</em> (or press Ctrl+S) and choose this same <code>human_intervention_status.html</code> to overwrite it. Chrome and Edge remember the file after the first save. Other browsers download a copy instead. When you're done, tell an agent "my answers are in human_intervention_status.html". Rebuilding this page keeps saved answers.</p>
<section class="orphans" id="orphans" hidden><h2>Earlier answers whose question has changed</h2><p>These were saved against questions that are no longer on this page. They are kept so nothing is lost.</p><div id="orphan-list"></div></section>
__BUNDLE__
<p class="note"><strong>About the checkboxes:</strong> <em>Supplied</em> is a bookmark saved only in this browser. An ask is really finished when the answer is recorded in <code>docs/audits/master_checklist.md</code>. Tell an agent, and it will do that.</p>
<section class="counters" aria-label="Human intervention counts">
  <div class="counter"><strong id="count-total">__TOTAL__</strong><span>Distinct asks</span></div>
  <div class="counter"><strong id="count-complete">0</strong><span>Marked supplied in this browser</span></div>
  <div class="counter"><strong id="count-remaining">__TOTAL__</strong><span>Remaining in this browser</span></div>
</section>
<p class="intro"><strong>Asks holding at least one task of each priority:</strong> __PRIORITY_SUMMARY__ · <strong>Blocked tasks covered:</strong> __TASK_TOTAL__</p>
<form class="filters" role="search" onsubmit="return false">
  <label>Search asks and tasks<input id="search" type="search" placeholder="e.g. QC, calibration, credentials, READY-03"></label>
  <label>Priority<select id="priority"><option value="">All priorities</option>__PRIORITY_OPTIONS__</select></label>
  <button id="clear-completed" type="button">Clear local checkmarks</button>
</form>
<p id="visible-count" role="status" aria-live="polite">Showing __TOTAL__ of __TOTAL__ asks.</p>
<section id="cards" aria-label="Human intervention asks">
__CARDS__
</section>
<script id="saved-answers" type="application/json">{}</script>
<script>
// Captured before any script changes the page, so a save writes back exactly
// what the builder produced plus the answers block.
const PRISTINE = '<!doctype html>\n' + document.documentElement.outerHTML;
const storageKey = 'phasefinder-human-intervention-complete-v2';
const cards = [...document.querySelectorAll('.card')];
const search = document.querySelector('#search');
const priority = document.querySelector('#priority');
const state = (() => { try { return JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (_) { return {}; } })();
function save() { try { localStorage.setItem(storageKey, JSON.stringify(state)); } catch (_) {} }
function update() {
  let complete = 0;
  const query = search.value.trim().toLowerCase();
  for (const card of cards) {
    const input = card.querySelector('.completion');
    const checked = Boolean(state[input.dataset.taskId]);
    input.checked = checked;
    card.classList.toggle('is-complete', checked);
    if (checked) complete++;
    card.hidden = !card.textContent.toLowerCase().includes(query) || (priority.value && !card.dataset.priorities.split(' ').includes(priority.value));
  }
  document.querySelector('#count-complete').textContent = complete;
  document.querySelector('#count-remaining').textContent = cards.length - complete;
  document.querySelector('#visible-count').textContent = 'Showing ' + cards.filter(card => !card.hidden).length + ' of ' + cards.length + ' asks.';
}
for (const input of document.querySelectorAll('.completion')) input.addEventListener('change', () => { state[input.dataset.taskId] = input.checked; save(); update(); });
search.addEventListener('input', update);
priority.addEventListener('input', update);
document.querySelector('#clear-completed').addEventListener('click', () => { for (const input of document.querySelectorAll('.completion')) delete state[input.dataset.taskId]; save(); update(); });
// An in-page link may point into a card the current filter has hidden, or into
// a closed <details>; open the way to it before the browser scrolls there.
function reveal(hash) {
  const target = hash && hash.length > 1 && document.getElementById(decodeURIComponent(hash.slice(1)));
  if (!target) return;
  const card = target.closest('.card');
  if (card && card.hidden) { card.hidden = false; }
  for (let node = target.parentElement; node; node = node.parentElement) { if (node.tagName === 'DETAILS') node.open = true; }
  if (target.matches('.task')) { const details = target.querySelector('details'); if (details) details.open = true; }
  return target;
}
document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (link) reveal(link.getAttribute('href'));
});
window.addEventListener('hashchange', () => reveal(location.hash));
update();

const answersKey = 'phasefinder-human-intervention-answers-v1';
const fileData = (() => { try { return JSON.parse(document.querySelector('#saved-answers').textContent || '{}'); } catch (_) { return {}; } })();
const localData = (() => { try { return JSON.parse(localStorage.getItem(answersKey) || '{}'); } catch (_) { return {}; } })();
// Per answer, the newer of the file copy and the browser copy wins.
const answers = { ...(fileData.answers || {}) };
for (const [key, entry] of Object.entries(localData.answers || {})) {
  if (!answers[key] || (entry.updated || '') > (answers[key].updated || '')) answers[key] = entry;
}
if (fileData.supplied && !Object.keys(state).length) { Object.assign(state, fileData.supplied); save(); update(); }
let fileHandle = null;
let unsaved = JSON.stringify(answers) !== JSON.stringify(fileData.answers || {});
const boxes = [...document.querySelectorAll('textarea[data-answer-key]')];
function answered() { return Object.values(answers).filter(entry => entry.text.trim()).length; }
function showStatus(message) {
  const el = document.querySelector('#answer-status');
  const count = answered();
  el.textContent = message || (count ? count + (count === 1 ? ' answer' : ' answers') + (unsaved ? ' · saved in this browser, not yet in the file' : ' · saved in this file') : 'No answers yet.');
  el.classList.toggle('unsaved', unsaved && count > 0);
}
for (const box of boxes) {
  const entry = answers[box.dataset.answerKey];
  if (entry) box.value = entry.text;
  box.classList.toggle('has-answer', Boolean(box.value.trim()));
  box.addEventListener('input', () => {
    answers[box.dataset.answerKey] = { text: box.value, question: box.dataset.question, card: box.dataset.answerKey.split('/')[0], updated: new Date().toISOString() };
    // The one-list and the card show the same answer in two boxes.
    for (const twin of boxes) {
      if (twin !== box && twin.dataset.answerKey === box.dataset.answerKey) { twin.value = box.value; twin.classList.toggle('has-answer', Boolean(box.value.trim())); }
    }
    if (!box.value.trim()) delete answers[box.dataset.answerKey];
    box.classList.toggle('has-answer', Boolean(box.value.trim()));
    unsaved = true;
    try { localStorage.setItem(answersKey, JSON.stringify({ answers })); } catch (_) {}
    showStatus();
  });
}
const onPage = new Set(boxes.map(box => box.dataset.answerKey));
const orphans = Object.entries(answers).filter(([key, entry]) => !onPage.has(key) && entry.text.trim());
if (orphans.length) {
  document.querySelector('#orphans').hidden = false;
  document.querySelector('#orphan-list').replaceChildren(...orphans.flatMap(([key, entry]) => {
    const h = document.createElement('h3'); h.textContent = key + (entry.question ? ' — ' + entry.question : '');
    const pre = document.createElement('pre'); pre.textContent = entry.text;
    return [h, pre];
  }));
}
function pageWithAnswers() {
  const payload = JSON.stringify({ savedAt: new Date().toISOString(), answers, supplied: state }, null, 1).replace(/</g, '\\u003c');
  return PRISTINE.replace(/(<script id="saved-answers" type="application\/json">)[\s\S]*?(<\/script>)/, (_, open, close) => open + payload + close);
}
async function saveIntoFile() {
  const html = pageWithAnswers();
  if (window.showSaveFilePicker) {
    try {
      fileHandle = fileHandle || await window.showSaveFilePicker({ suggestedName: 'human_intervention_status.html', types: [{ description: 'HTML page', accept: { 'text/html': ['.html'] } }] });
      const writable = await fileHandle.createWritable();
      await writable.write(html);
      await writable.close();
      unsaved = false;
      showStatus();
      return;
    } catch (error) {
      if (error.name === 'AbortError') return;
      fileHandle = null;
    }
  }
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
  link.download = 'human_intervention_status.html';
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
  unsaved = false;
  showStatus('Downloaded a copy with your answers. Replace docs/audits/human_intervention_status.html with it.');
}
function answersAsText() {
  const lines = [];
  for (const [key, entry] of Object.entries(answers).sort()) {
    if (!entry.text.trim()) continue;
    lines.push('## ' + key + (entry.question ? ' — ' + entry.question : ''), entry.text.trim(), '');
  }
  return lines.join('\n') || 'No answers yet.';
}
document.querySelector('#save-answers').addEventListener('click', saveIntoFile);
document.querySelector('#copy-answers').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(answersAsText()); showStatus('Copied ' + answered() + ' answers to the clipboard.'); setTimeout(() => showStatus(), 2500); }
  catch (_) { showStatus('Copy failed. Use Save answers into this file instead.'); }
});
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); saveIntoFile(); }
});
window.addEventListener('beforeunload', (event) => { if (unsaved && answered()) { event.preventDefault(); event.returnValue = ''; } });
showStatus();
// Opened at a deep link: the browser scrolled before the details were open.
const linked = reveal(location.hash);
if (linked) linked.scrollIntoView();
</script>
</main></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the generated page is stale.")
    args = parser.parse_args()
    guide_text = GUIDE.read_text(encoding="utf-8") if GUIDE.exists() else ""
    page, drift = build(CHECKLIST.read_text(encoding="utf-8"), guide_text)
    page = keep_saved_answers(page, OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None)
    for note in drift:
        print(f"Guide drift: {note}", file=sys.stderr)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != page:
            print("Human intervention page is stale: run python3 scripts/build_human_intervention_status.py")
            return 1
    else:
        OUTPUT.write_text(page, encoding="utf-8")
    asks = page.count('<article class="card"')
    distinct = len(set(re.findall(r'<article class="task" [^>]*data-task-id="([^"]+)"', page)))
    print(f"Human intervention page: {asks} asks covering {distinct} blocked tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
