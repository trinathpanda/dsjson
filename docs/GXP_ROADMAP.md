# GxP readiness roadmap (future work)

Status: backlog, not started. Parked 2026-11-20 to focus on the PHUSE APAC 2027 talk.

A tool is never "GxP compliant" on its own. Compliance = the app's built-in controls **plus**
a validated process around it. Relevant frameworks: GAMP 5 (2nd ed., risk-based),
21 CFR Part 11 / EU Annex 11 (electronic records, audit trails), FDA Computer Software
Assurance (CSA), ALCOA+ data integrity.

## Part A - features to build into dsjson

| # | Feature | What it does | GxP value |
|---|---|---|---|
| 1 | Run manifest (audit trail) | Each run writes `run_manifest.json`: SHA-256 of every input XPT and `define.xml`, SHA-256 of every output JSON, dsjson version + git commit, schema version, OS user, machine, UTC start/end, settings, per-dataset result. Append-only. | Who ran what, on which inputs, with which version, and what came out (ALCOA+: attributable, contemporaneous, complete). |
| 2 | Version stamp in output | Fill optional Dataset-JSON `sourceSystem` (`{"name": "dsjson", "version": "x.y.z"}`); show version in app title and logs. | Every output traces back to a released, validated build. |
| 3 | Source-to-output reconciliation | After conversion, re-read the XPT and compare with the JSON: record counts, cell-by-cell values, column order. PASS/FAIL in the validation report. | Independent proof the conversion is lossless (today we only compare against the CDISC reference). |
| 4 | Deterministic output | Same inputs -> byte-identical output; option to pin `datasetJSONCreationDateTime`. | Reproducibility; re-run verification becomes trivial. |
| 5 | IQ/OQ evidence generator | `dsjson qualify`: IQ checks (Python, package versions, schema hash) + OQ (test suite + CDISC pilot comparison) -> dated report mapping tests to requirement IDs. | Installation/Operational Qualification as a 2-minute repeatable run. |

Supporting items:
- Mark outputs read-only after writing.
- Pin dependencies with hashes (lock file) and produce an SBOM.
- No silent failures: any unexpected exception marks the dataset FAIL.
- Release discipline: git tags, CHANGELOG, signed .exe.

## Part B - process artefacts (team / QA own these)

- Validation plan + URS (user requirements with IDs).
- Risk assessment (GAMP 5 category 5, output feeds submissions). Under CSA, test hardest where errors harm data (values, types, record counts).
- Traceability matrix requirement -> test (feature 5 can generate it from test IDs).
- PQ: users run dsjson on a real, finished study side by side with the XPT process.
- SOPs + change control: every change via reviewed PR, OQ re-run, new version.
- Part 11 e-signatures / access control: do not build into the desktop tool. Store outputs in a validated document/repository system (fits roadmap stage 3, server).

## Suggested order

1. Features 1-3 (about a day, biggest trust gain).
2. Feature 5 (turns existing tests into QA evidence).
3. Feature 4 and supporting items.
