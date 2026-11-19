# dsjson improvement backlog

Status: backlog. Collected 2026-11-20 while preparing the PHUSE APAC 2027 talk.
GxP items are tracked separately in [GXP_ROADMAP.md](GXP_ROADMAP.md).

Priority: **P0** = fix before PHUSE (Jan 2027), **P1** = next release, **P2** = later, **Watch** = depends on others.

## 1. Specification compliance (checked against CDISC Dataset-JSON v1.1, final 2024-12-05)

Source: [doc/dataset-json1-1.md](https://github.com/cdisc-org/DataExchange-DatasetJson/blob/master/doc/dataset-json1-1.md)

| # | Finding | Spec says | dsjson today | Priority |
|---|---|---|---|---|
| S1 | Top-level attribute order | "Strongly recommended" order: ... `itemGroupOID`, **`records`**, `name`, `label`, `columns`, `rows` (lets streaming readers work) | Fixed 2026-11-20 (test enforces the order) | Done |
| S2 | `displayFormat` column attribute | Optional SAS display format for numeric float and date values | Dropped. CDISC reference keeps it (e.g. VISITNUM `8.1`); pyreadstat exposes XPT formats | P1 |
| S3 | `targetDataType` column attribute | Optional; `integer` for ADaM numeric dates/times, `decimal` for decimals sent as strings | Dropped | P1 (needed for ADaM) |
| S4 | `decimal` data type | `decimal` values are exchanged as JSON **strings** with `targetDataType: "decimal"` | dsjson writes `double` with numbers (valid). Note: the CDISC reference labels VISITNUM `decimal` but stores numbers without `targetDataType`, which does not follow this rule | Keep; document the choice |
| S5 | ADaM dates | ADaM numeric SAS dates: `dataType` date/datetime/time, JSON string, `targetDataType: integer`, `displayFormat` e.g. `E8601DA.` | Not handled (SDTM only); XPT numeric dates would be written as numbers | P1 before ADaM support |
| S6 | Missing vs empty | Missing = `null`; empty string = `""` | Numeric missing -> `null`, character blank -> `""` (same as CDISC reference) | OK |
| S7 | `dbLastModifiedDateTime` | Must be on or before `datasetJSONCreationDateTime` | XPT modification time, always earlier | OK |
| S8 | `metaDataRef` | A URI for the metadata file | File name `define.xml` (a relative URI) | OK; option for full URI later (P2) |
| S9 | One dataset per file, `.json` extension, lowerCamelCase | Required | Yes | OK |
| S10 | Column attribute order | `itemOID`, `name`, `label`, `dataType`, `targetDataType`, `length`, `displayFormat`, `keySequence` | Same order for the fields written | OK; keep when adding S2/S3 |

## 2. Ideas from related open-source projects

| # | Idea | Inspired by | Value | Effort | Priority |
|---|---|---|---|---|---|
| R1 | Round-trip check: Dataset-JSON -> XPT -> compare with source XPT (or run `dsjconvert` as an independent reader) | [swhume/dataset-json](https://github.com/swhume/dataset-json) (`dsjconvert`, Python, MIT) | Independent proof of a lossless conversion; also GxP item 3 | ~2 h | P0 if time allows |
| R2 | Viewer mode: open any Dataset-JSON file (from any tool), preview and validate it | [atorus-research/datasetjson](https://github.com/atorus-research/datasetjson) (`read_dataset_json`, `validate_dataset_json`, R, Apache-2.0) | Useful to file receivers and reviewers; preview and validation tabs already exist | ~2-3 h | P1 |
| R3 | NDJSON output (`.ndjson`: line 1 metadata, then one row per line) | Official CDISC NDJSON representation; `dsjconvert` default; R `write_dataset_ndjson` | Streaming for very large datasets (QS 121k rows) | ~2 h | P1 |
| R4 | Compressed Dataset-JSON (`.dsjc`, compressed NDJSON) | Official CDISC "Compressed Dataset-JSON v1.1" spec; R `write_dataset_dsjc` | Much smaller files for transfer | ~2 h after R3 | P2 |
| R5 | SAS7BDAT input | `dsjconvert` | Start from SAS datasets, not only XPT (a stub reader exists) | ~2 h | P1 |
| R6 | `originator` (and other optional fields) as a setting | R package setters (`set_originator`, ...) | Complete file-level metadata | ~30 min | P2 |
| R7 | Infer metadata without Define-XML | `dsjconvert --no-define` | Draft or ADaM data without Define-XML; weakens the metadata-driven message | ~2 h | P2 / maybe never |
| R8 | Publish to PyPI (`pip install dsjson`) | `dsjconvert` | Needed for the Python library stage | ~1 h | P1 |
| R9 | Server stage built on the CDISC Dataset-JSON API (OpenAPI 3.1, draft v1.0 2025-08-07) | [cdisc-org/DataExchange-DatasetJson-API](https://github.com/cdisc-org/DataExchange-DatasetJson-API) | Standard endpoints instead of a home-made API; code can be generated from the OAS file | Days | Roadmap |

## 3. App and project items already known

| # | Item | Priority |
|---|---|---|
| A1 | Windows `.exe` (PyInstaller); bundle the JSON schema and `desktop_app/assets/` | P1 |
| A2 | Tag `v0.1.1` (sourceSystem landed after the `v0.1.0` tag) | P1 |
| A3 | GxP readiness (audit trail, reconciliation, IQ/OQ evidence) | see [GXP_ROADMAP.md](GXP_ROADMAP.md) |
| A4 | Remove or finish unused scaffolding (`dsjson/services.py`, `utils.py`, `metadata/source_infer.py`, `metadata/spec_file.py`, `readers/base.py`, `csv_reader.py`, `sas7bdat_reader.py`) before the repo goes public | Done 2026-11-20 |

## 4. Positioning (for talks and the README)

dsjson does not claim to be the first converter. It is complementary to `dsjconvert` and the R
`datasetjson` package. What it adds: a desktop workflow for non-programmers, safety checks that
refuse silently wrong output, plain-language findings, and value-by-value evidence against the
CDISC pilot reference. We prefer contributing ideas back over duplicating features.
