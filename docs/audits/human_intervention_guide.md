# Human intervention guide

Plain-language text for [the handoff page](human_intervention_status.html). `scripts/build_human_intervention_status.py` reads this file: `## Start here` and `## Words you'll see` go at the top of the page, and each `## HI-… — Title` section goes on that ask's card. The task lists on each card are rebuilt from `master_checklist.md`; everything in this file is written by hand and has to be kept current by hand. `## Everything I need from you, in one list` goes right under the intro. A `{answer: KEY}` marker at the end of a list item, or alone on a line, becomes an answer box. Boxes with the same key are the same answer, so the one-list item and the question on its card should share a key; the builder warns when they don't.

## Start here

PhaseFinder is mostly built and checked by AI agents. An agent gets stuck when a task needs something it can't produce itself: real lab data, a decision about what the product should do, a password, or a qualified person's judgement. Everything on this page is one of those. Each card below is one thing I need from you: what it is in plain English, what you'd actually do, and what I'd suggest. The list right after this section puts every separate question in one place, with my suggested answer and a box for yours.

*Written 2026-09-23. The plain-English text and suggestions are written by hand and can fall behind; the task lists under each card are rebuilt from the checklist every time.*

#### Suggested order: quickest first

1. **[Make some decisions](#HI-DECIDE)**, about an hour. Four multiple-choice questions about what the app should do. Each has my suggested answer, so "go with your suggestions" is a complete reply.
2. **[Turn on the test website](#HI-RELEASE)**, about 30 minutes of clicking in GitHub and Cloudflare. I found why it can't work yet: the secrets have the wrong names. It's a small fix.
3. **[Confirm the FlowJo reference](#HI-REFERENCE)**, about 10 minutes. You did most of this on 2026-09-23. Two short questions are left.
4. **[Collect labelled lab data](#HI-DATA)**. This is the big one: weeks, depending on lab time. Start with the 15-minute part (choosing error-rate targets) and collect files over time.
5. **[Get an expert to sign off](#HI-EXPERT)**. Do this last, because the expert reviews what steps 1–4 produce. Ask someone now so they're ready when the time comes.

#### How to hand things back

You don't have to edit the checklist yourself. Tell an agent in chat what you decided or where you put things, for example *"D4–D8: go with your suggestions"* or *"the labelled files are in the lab share under qc_corpus"*. It will record your answer in `master_checklist.md` and rebuild this page. You can also type answers into the boxes on `human_intervention_status.html`, click "Save answers into this file", and then tell an agent the answers are in that file.

#### Already decided

Your 2026-09-25 answers to D1 (no release until validation is finished), D2 (a lone peak gets an alert, not a G1/G2 label), D3 (Chrome, Edge, Firefox and Safari) and D7 (no ModFit comparison) are recorded in `master_checklist.md` under *Owner decisions on record*, so they're no longer on this page. The question numbers below keep their original labels.

## Everything I need from you, in one list

Every separate thing I need, grouped by ask and in the suggested order. Each line shows my suggested answer, so "agree" is a complete reply. *Full detail* jumps to the explanation further down. The box there is the same box: typing in either place fills both.

#### 1. Decisions: about an hour, no lab work

1. **D4: What should Time QC do when peaks cross or merge?** Suggested: keep the simple tracker and the manual-review flag. {answer: HI-DECIDE/D4}
2. **D5: How many cells does a bad stretch of a recording remove?** Suggested: switch to the majority rule (peak-tracking-v3). {answer: HI-DECIDE/D5}
3. **D6: Keep four future features on hold?** Suggested: yes, keep all four parked. {answer: HI-DECIDE/D6}
4. **D8: The "limited reliability" flag is on for every fit. What should count as a good fit?** Suggested: keep the strict curve-shape checks, and judge the flag by whether the clearly wrong fits get a specific warning. Revisit once the peak-width difference (MODEL-02) is understood. {answer: HI-DECIDE/D8}

#### 2. Test website: about 30 minutes

1. **Which Cloudflare secret names should the workflow use?** Suggested: reply "use the existing secret names", and an agent changes the workflow. {answer: HI-RELEASE/secret-names}
2. **Is the Cloudflare side ready?** You check in the Cloudflare dashboard that the token can edit Pages, and create a `phasefinder-staging` project if there isn't one. Reply "done" or say what you found. {answer: HI-RELEASE/cloudflare}
3. **Set up GitHub environments?** Optional. Suggested: create `staging` and `production`, with your approval required on `production`. {answer: HI-RELEASE/environments}
4. **Go-ahead for the first staging deploy?** An agent pushes a test tag and deploys to staging. Both are outward-facing, so they need your explicit OK. {answer: HI-RELEASE/go-ahead}
5. **Who practises the rollback?** Suggested: let the agent do it with the same token. Or you click it in Cloudflare yourself. {answer: HI-RELEASE/rollback}
6. **Which work becomes version 0.9.0, and may an agent push the tag?** Nothing is committed yet. Suggested: when you want a release, say which work to commit; an agent then bumps to 0.9.0, tags it, and pushes only after your OK. {answer: HI-RELEASE/version-tag}

#### 3. FlowJo reference: about 10 minutes

1. **Were the FlowJo workspace files the original analysis or a re-run?** Just say which. {answer: HI-REFERENCE/original-or-rerun}
2. **What happens to the workspace files?** They contain your Windows username, lab project and operator names and the instrument serial number, and the dataset is marked not redistributable. Suggested: keep them local only; the settings write-up that is safe to commit already exists. {answer: HI-REFERENCE/workspace-files}

#### 4. Lab data: Part 1 about 15 minutes, Part 2 over weeks

1. **Do you accept the five error-rate targets?** For example, at most 5% false alarms on clean files and at least 90% of real problems caught. Suggested: accept them as a starting point. {answer: HI-DATA/targets}
2. **Are the 30 async yeast files clean?** Confirm, or name the ones that aren't. {answer: HI-DATA/clean-runs}
3. **Clogs, gaps and time glitches.** Ask the MACSQuant operator for about 10 runs that clogged or stalled, and roughly when. Note who you asked and what they said. {answer: HI-DATA/clog-runs}
4. **Doublet-heavy runs.** A sonicated/unsonicated pair of the same sample, the next time the lab records yeast. {answer: HI-DATA/doublet-runs}
5. **Debris-heavy runs.** About 10 files from old or stressed cultures. {answer: HI-DATA/debris-runs}
6. **Peak answer key.** Who will mark G1 and G2 on about 50 histograms, and should an agent build the marking page? {answer: HI-DATA/peak-key}
7. **Where do the files go?** A folder path (it can stay off GitHub), and whether an agent should make the spreadsheet template. {answer: HI-DATA/location}

#### 5. Expert sign-off: one email now, their review comes last

1. **Who will review?** A flow-cytometry person who didn't help build PhaseFinder, for example a core facility manager. {answer: HI-EXPERT/who}
2. **Draft the review packet now?** Suggested: yes, have an agent draft it so it's ready when they are. {answer: HI-EXPERT/packet}

## Words you'll see

| Word | What it means here |
|---|---|
| FCS file | The data file a flow cytometer saves. One file is one sample: a list of every cell measured (often hundreds of thousands) and how bright each cell was in each colour channel. |
| DNA histogram | A bar chart of how bright the DNA dye is in each cell. Cells with one copy of their DNA pile up in one peak. Cells with two copies pile up in a second peak at about double the brightness. |
| G1, S, G2 | Stages of the cell cycle. G1 means one copy of the DNA. S means the DNA is being copied, so the cell sits between the two peaks. G2 (with M, mitosis) means two copies, about to divide. PhaseFinder's main job is to report what percent of cells are in each stage. |
| Model / fit | The curve PhaseFinder draws over the histogram to split it into G1, S and G2. Dean-Jett-Fox (DJF) and Watson are two standard recipes for that curve. |
| Peak width (CV) | How spread out a peak is. The CV is the peak's width divided by its position, written as a percent. Two programs can agree on where a peak is and still disagree on how wide it is. |
| Gate | A filter that removes some particles before analysis, such as debris or clumps. If two programs gate differently, they aren't analysing the same cells. |
| QC (quality control) | Automatic checks for problems in a recording: a clog, a gap, a timer glitch, clumped cells, or junk particles. |
| Doublet | Two cells stuck together and measured as one. It looks like one cell with double the DNA, so it can be mistaken for a G2 cell. |
| Debris | Broken pieces of cells. Usually dim, but it can outnumber the real cells in a bad sample. |
| Labelled data / ground truth | Files where a person already knows the right answer and has written it down, like an answer key. |
| False alarm / detection rate | A false alarm (false positive) is a good file flagged as bad. The detection rate is the share of real problems a check catches. You can't have zero false alarms and also catch everything, so someone has to pick the trade-off. |
| FlowJo / ModFit | Commercial programs scientists use for this same analysis. FlowJo is the one this project compares against. |
| P0 – P3 | Priority. P0 must be done before release, or before a big scientific claim. P3 means "someday". |
| Staging | A private test copy of the website, used to check a release before the real one goes live. |

## HI-DECIDE — Make some product decisions

#### In plain English

Some tasks aren't stuck on a bug. They're stuck because nobody has decided what the app *should* do. An agent could guess, but then it would be making up requirements for your product. You're the owner, so these decisions are yours. Each question below is multiple choice and shows the option I'd pick.

#### The questions, with my suggested answers

1. **D4: What should Time QC do when peaks cross or merge?** *(QC-04)* Time QC follows the DNA peaks over the few minutes a sample records, to spot clogs. The current tracker matches each peak to its nearest neighbour and flags the file for manual review when things get ambiguous. A full tracking model that understands peaks crossing, merging, splitting, appearing and disappearing would be a sizeable project. *Options:* (a) build the full model; (b) keep the simple tracker and the review flag. **My pick: (b)**, until real files show the simple tracker getting something wrong. {answer: HI-DECIDE/D4}
2. **D5: When part of a recording looks bad, how many cells get thrown out?** *(QC-04, QC-CAL-01)* The check looks at overlapping time windows. Today a cell is removed if *any* window it's in looks bad. On a test file with a fake clog, that caught the whole clog but also removed 650 good cells. A *majority* rule removes a cell only if most of its windows look bad. It also caught the whole clog, and removed only 150 good cells. **My pick: switch to the majority rule.** Caveat: this was measured on made-up test files, not real ones. The change affects results, so it gets a new version number (peak-tracking-v3) to keep old sessions reproducible. {answer: HI-DECIDE/D5}
3. **D6: Keep these future features on hold?** *(FUTURE-01, FEAT-03, FEAT-04, FEAT-05)* Four features are parked: modelling many samples together; extra curve pieces for debris, dying cells and unusual DNA amounts; moving CLOCCS (the time-course model) out of "Unverified"; and using extra marker colours alongside DNA. **My pick: keep all four parked**, and record that as your decision rather than as "waiting on someone". Each one builds on the basic single-sample fit, which isn't independently validated yet. Building on top of it first would multiply the risk. Once your decision is recorded, these four come off this page. {answer: HI-DECIDE/D6}
4. **D8: The "limited reliability" flag is on for every fit. What should count as a good fit?** *(GATE-03)* Every fit on the 30 FlowJo samples gets the "limited reliability" flag, including fits whose G1/S/G2 numbers match FlowJo to within a point. The reason is real: the fitted curve doesn't follow the histogram's bars closely enough. The "overdispersed fit" check allows a score of 2 and these fits score from about 300 to 3,400, and the leftover differences form patterns, not random noise. An agent has added specific warnings that now correctly catch the clearly wrong fits (G1 placed on the G2 peak, and Watson fits with almost no S phase). The task's last box asks that most fits matching FlowJo come out *without* a warning, and none do (0 of 54). *Options:* (a) keep the strict curve-shape checks, and change that box to "the clearly wrong fits get a specific warning", which is already true; (b) downgrade the curve-shape warnings to information-only so fits matching FlowJo look clean, which hides a misfit that was actually measured; (c) collect labelled curve-shape examples (part of [HI-DATA](#HI-DATA)) and recalibrate the checks against them. **My pick: (a), and revisit after MODEL-02.** Part of the misfit may come from PhaseFinder's narrower peaks, so the scores may drop once that is understood. A number that matches FlowJo doesn't prove the curve fits. {answer: HI-DECIDE/D8}

#### What "done" looks like

You reply in chat with your answers ("all suggestions" counts). An agent records each one, with the date, in the matching task in `master_checklist.md`.

#### Rough effort

About an hour to read and decide. No lab work.

## HI-RELEASE — Turn on the test website

#### In plain English

PhaseFinder is a website hosted on Cloudflare Pages. Before a real release, the plan is to put a private test copy online (staging), check that it loads and behaves, and practise rolling back to an older version. The automated pipeline can do almost all of this. It needs a key to your Cloudflare account and your OK to publish, and only the account owner can give those.

#### What I found when I checked (2026-09-23)

- Your GitHub repository already has two Cloudflare secrets, `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` (added 2026-07-02).
- The deploy workflow looks for secrets named `CF_API_TOKEN` and `CF_ACCOUNT_ID`, which don't exist. So a staging deploy would fail right now even if you started it.
- No GitHub environments are set up. GitHub creates one automatically the first time a job asks for it, but that way there's no approval step.

#### What you'd actually do

1. Say "use the existing secret names", and an agent will change the workflow to read `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. (Or add two new secrets with the `CF_` names yourself. The result is the same.) {answer: HI-RELEASE/secret-names}
2. In the Cloudflare dashboard, check that the token has permission to edit Cloudflare Pages. If there's no Pages project named `phasefinder-staging`, create one. {answer: HI-RELEASE/cloudflare}
3. Optional but sensible: in GitHub → Settings → Environments, create `staging` and `production`, and set `production` to require your approval before a deploy runs. {answer: HI-RELEASE/environments}
4. Tell the agent to go. It pushes a test tag, runs the deploy workflow with *deploy_staging* switched on, checks the site and its security headers, and records the deployment ID. {answer: HI-RELEASE/go-ahead}
5. Practise one rollback on staging: in the project's Deployments list in Cloudflare, roll back to the previous deployment. An agent can also do this with the same token if you allow it. {answer: HI-RELEASE/rollback}
6. At the next release, say which work becomes version 0.9.0 *(REL-05)*. The versioning rules, changelog and model-version bumps are done. What's left is choosing the release commit and approving the tag. Nothing on this branch is committed yet, so tagging now would label the old code. Once you say which work to commit, an agent bumps `package.json` to 0.9.0, commits, tags `v0.9.0`, and pushes the tag only after your OK. {answer: HI-RELEASE/version-tag}

#### What "done" looks like

A working staging address, a recorded deployment ID and header check in `docs/release-and-privacy.md`, and one practised rollback. Final release sign-off (READY-04) comes later, after the other asks.

#### My recommendation

Do this second, right after the decisions. It's the cheapest ask, and it unblocks three of REL-01's boxes and one of READY-01's. Keep production deploys switched off (leave `ENABLE_PRODUCTION_DEPLOY` unset) until you're ready for a real release.

#### Rough effort

About 30 minutes of your time.

## HI-REFERENCE — Show exactly how FlowJo was set up

#### In plain English

To check PhaseFinder's answers, the project compares them with FlowJo's on the same 30 yeast samples. That comparison is only fair if both programs were set up the same way. If FlowJo removed some cells first (a gate) or used different model settings, the differences could come from the setup and not the math. The project had FlowJo's *answers* but not its *settings*.

#### Status: mostly done

On 2026-09-23 you supplied recovered FlowJo workspace files ([evidence write-up](flowjo_reference_settings_2026_09_23.md)). I checked the files directly. FlowJo used no gates, the Dean-Jett-Fox model with synchronisation off, the same DNA channel (FL7-A), and no limit on peak width. The sample in the files (1468f) reproduces the published FlowJo numbers exactly: G1 CV 9.7403 against 9.74 published. That covers the settings half of this ask.

#### What's left for you

1. **Were these files the original analysis, or a re-run?** They're dated 2026-09-19, months after the April spreadsheets, and they're named "seed" like the FlowJo automation work from that same week. A re-run is fine, because it matches exactly. Just say which it is so the record is accurate. {answer: HI-REFERENCE/original-or-rerun}
2. **Before committing the workspace files:** they contain your Windows username in a file path, the lab project and operator names, and the instrument serial number. The dataset is also recorded as not redistributable. The files aren't committed yet. Decide whether to commit them as they are, strip those fields first, or keep them local only. {answer: HI-REFERENCE/workspace-files}

#### What's *not* left for you

MODEL-02's deeper question is why PhaseFinder's peaks come out narrower than FlowJo's, and you can't answer that by supplying anything. The next step is agent work. FlowJo's fitted curve for 1468f is fully recorded, so an agent can draw it over PhaseFinder's histogram of the same cells and see where the two differ. The agent should check one thing first: the write-up says both programs used every cell, but PhaseFinder's MODEL-02 numbers were measured after its own QC removed about 1.4% of the cells (the off-scale ones). If the difference turns out to be two ways of defining "width", neither of them wrong, then choosing which one PhaseFinder reports goes to the expert ([HI-EXPERT](#HI-EXPERT)), which is why MODEL-07 also waits there.

#### Rough effort

About 10 minutes.

## HI-DATA — Collect labelled lab data

#### In plain English

PhaseFinder runs automatic quality checks on every file. It looks for clogs, gaps, timer glitches, clumped cells (doublets) and junk (debris), and it warns when a model fit looks poor. Each check has a dial that sets how unusual something must be before it gets flagged. Right now the dials are set to sensible defaults and tested only on fake files the project generated itself.

To set the dials properly, we need real files where a person has already written down what's wrong with each one: an answer key. The key has to come from outside PhaseFinder, because grading software with an answer key it wrote itself proves nothing.

This ask has two parts. One is quick and one is slow.

#### Part 1 (quick): choose your error-rate targets

No check can catch every problem and also never raise a false alarm. Turning one down turns the other up, like the sensitivity setting on a smoke alarm. Someone has to say which trade-off is acceptable, and that's a preference, not a measurement. Here are the starting numbers I'd suggest. Change any you disagree with.

| Target | Suggested starting value | In plain words |
|---|---|---|
| False alarms on clean files | At most 5% of clean files get a QC warning | 1 in 20 good files may get flagged for a second look |
| Detection | At least 90% of real, labelled problems are flagged | The checks catch 9 in 10 real clogs, gaps, doublet-heavy or debris-heavy files |
| Retention | A clean file keeps at least 95% of its cells | QC shouldn't throw away good data |
| Collateral around a real problem | At most a quarter of the cells removed around a bad stretch are good ones | When cutting out a clog, don't cut too much around it. (The majority rule in D5 scored 20% on the test file; today's rule scored 52%.) |
| Fit-quality warning | Warns on at most 5% of good fits and catches at least 80% of clearly bad ones | This is the "overdispersed fit" warning (STAT-01) |

{answer: HI-DATA/targets | Do you accept the five error-rate targets?}

#### Part 2 (slow): build the answer-key collection

What's needed is real FCS files plus a simple spreadsheet saying what's in each one. A workable first collection:

- **Clean runs:** about 20 files that someone who knows the data has looked at and confirmed are fine. The 30 async yeast files you already have are good candidates. {answer: HI-DATA/clean-runs}
- **Clogs, gaps and time glitches:** about 10 files. Ask whoever runs the cytometer (the MACSQuant) whether they remember runs that clogged or stalled, and roughly when in the run it happened. Some can be made on purpose, for example by briefly pausing sample uptake. Ask the operator what's safe for the instrument. {answer: HI-DATA/clog-runs}
- **Doublet-heavy:** about 10 files. The same sample recorded once properly separated (sonicated) and once not makes a clean pair: the unsonicated one has more clumps, and you know why. {answer: HI-DATA/doublet-runs}
- **Debris-heavy:** about 10 files, for example from old or stressed cultures with many dead or broken cells. {answer: HI-DATA/debris-runs}
- **Peak answer key:** for about 50 histograms, someone who knows the data marks which peak is G1 and which is G2. An agent can build a small page or spreadsheet that shows each histogram and records the answers. {answer: HI-DATA/peak-key}

The spreadsheet needs one row per file: file name, category, the approximate start and end of any problem (seconds into the run), who labelled it, the date, and notes. An agent can make the template.

An honest caveat: 10 files of each kind gives a rough first calibration, not a precise one. With 10 files, "caught 9 out of 10" is consistent with a true catch rate anywhere from about 55% to nearly 100%. More files over time narrow that.

#### What "done" looks like

The files in one folder (it can stay off GitHub if they're private), the spreadsheet next to them, and the Part 1 targets recorded. Agents then calibrate the dials against the files and report which targets are met.

{answer: HI-DATA/location | Where do the files go, and should an agent make the spreadsheet template?}

#### My recommendation

Do Part 1 now: accept or edit the table, which takes about 15 minutes. For Part 2, start small with what you already have. Confirm the 30 async files as clean, ask the cytometer operator for known-bad runs, and add a sonicated/unsonicated pair the next time the lab records yeast. Don't wait for a complete collection before handing anything over; agents can start with the clean files.

#### Rough effort

Part 1: about 15 minutes. Part 2: a few hours of someone's time, spread over weeks depending on lab schedules.

## HI-EXPERT — Get an expert to sign off

#### In plain English

Before anyone says PhaseFinder's results are scientifically valid, whether in a paper, a grant, or to another lab, a qualified flow-cytometry person needs to look at the evidence and put their name to it. An AI can gather and organise the evidence, but it can't be the one who vouches for it.

#### Who

Someone experienced in DNA-content cell-cycle analysis who didn't help build PhaseFinder. For example, a flow-cytometry core facility manager, or a PI or staff scientist who runs these experiments routinely.

{answer: HI-EXPERT/who | Who will review?}

#### What they'd review

- What PhaseFinder says it's for, and what it says it isn't for (the "supported use" claims).
- The comparison with FlowJo, including the known and explained differences: PhaseFinder's G1 peak sits about 1.6% lower, its peaks come out narrower, and its G2:G1 ratio lands near 1.97 where FlowJo's sits close to 2.0.
- If the FlowJo comparison shows the width difference is two conventions and not an error, which one PhaseFinder should report (MODEL-02, MODEL-07).
- The stated limits on how certain the numbers are.
- How the app decides which cloud of particles is the real cells and which is debris (QC-05).

#### What "done" looks like

A dated note from the expert (an email is fine) saying what they reviewed, what they agree with, and any caveats. It gets saved under `docs/audits/` and cited from the tasks.

#### My recommendation

Ask someone now, but have them review last, after the data and decisions are in. That way they review the finished picture once instead of a moving target. In the meantime, ask an agent to put together a short review packet (a few pages, plain figures, links to the evidence) so their time goes into judging and not digging. If you don't need publication-grade claims soon, this can wait; the app already avoids calling itself validated, and it won't be released until validation is finished.

{answer: HI-EXPERT/packet | Draft the review packet now?}

#### Rough effort

For you: one email to find the person. For them: roughly 2–4 hours with a good packet.
