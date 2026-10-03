# Redaction note

These FlowJo workspaces have been **redacted** before committing. They are not byte-identical to
the originals. The scientific payload is.

Redacted by `redact_workspace.py` (kept alongside the sweep tooling), 2026-09-23.

## What was removed

| Field | Replaced with |
|---|---|
| `$EXP`, `$LAST_MODIFIER` (operator name) | `REDACTED-OPERATOR` |
| `$CYTSN` (instrument serial) | `REDACTED-SERIAL` |
| `$PROJ` (lab project name) | `REDACTED-PROJECT` |
| `$PLATENAME` (rack name) | `REDACTED-PLATE` |
| `hwAddress` / `HWA` (hardware address) | `REDACTED-HWA` |
| `who="…"` on `<Save>` (Windows account) | `REDACTED-USER` |
| All filesystem paths (`uri`, `nonAutoSaveFileName`, `outputFile`) | `file:/REDACTED-PATH/` |

## What was deliberately kept

Everything the evidence depends on:

- The entire `<profile>` element — model, `syncPeak`, all gate attributes, both `<Range>` values,
  the empty `<Cv/>`.
- The entire `<CellCycleResult>` — all fitted statistics and Gaussian parameters.
- Every `$Pn*` parameter definition (channel names, ranges, scaling, detector settings).
- `$TOT`, `$PAR`, `$DATATYPE`, `$BYTEORD`, `$MODE`.
- Instrument **model** and software version (`$CYT`, `$SYS`) — the serial is gone, the model is not.
- Sample identity: `$CELLS`, `$WELLID`, `$FIL`, `$DATE`, `$BTIM`, `$ETIM`. These are already
  published in the reference table in `../../flowjo_reference_settings_2026_09_23.md`.

## Verification

The redactor hashes every `<profile>` and `<CellCycleResult>` block before and after, and aborts if
they differ. Both files passed. Independently re-read after writing, the redacted `djf_seed.wsp`
still yields:

```
G1% 21.61   S% 26.74   G2% 45.99
G1 mean 174.7  G1 CV 9.740   G2 mean 350.5  G2 CV 9.438
profile: model="DeanJettFox" parameter="FL7-A" syncPeak="0"
         autoGate="0" gateG1="0" gateG2="0" gateS="0"
```

— matching the published reference (21.6 / 26.7 / 46.0, means 175/350, CVs 9.74/9.44).

A residual scan for usernames, hardware addresses, personal names, author attributes, emails and
drive-letter paths returns clean on all five files. Note that `http://www.isac-net.org/...` and
`http://www.w3.org/...` namespace URIs remain and are expected — they are Gating-ML schema
references, not local paths.

## Unredacted originals

`Downloads\archivedwl-991\FlowJo_Seed\` on the acquiring workstation. Not committed.

## Still outstanding

The dataset itself (`flowjo_async_djf`) is recorded in the audit as **local-only and not
redistributable**. Redaction addresses personal and instrument identifiers; it does not change the
dataset's licensing status. Resolve that separately before these values become load-bearing for a
publication claim.
