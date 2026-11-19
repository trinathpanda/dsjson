# dsjson handbook

Everything about dsjson in one place: what it does, how every part works, how it is tested,
what the evidence shows, how it fits the standard and other tools, and how to present it at
PHUSE APAC Connect 2027 without surprises.

Version described: dsjson 0.1.0 (main branch, November 2026).

## Contents

1. [What dsjson is](#1-what-dsjson-is)
2. [Background](#2-background)
3. [Field-by-field reference](#3-field-by-field-reference)
4. [How it works inside](#4-how-it-works-inside)
5. [Define-XML 1.0 vs 2.x](#5-define-xml-10-vs-2x)
6. [Validation and safety checks](#6-validation-and-safety-checks)
7. [Using dsjson](#7-using-dsjson)
8. [Outputs explained](#8-outputs-explained)
9. [Testing](#9-testing)
10. [CDISC pilot evidence](#10-cdisc-pilot-evidence)
11. [Standards compliance](#11-standards-compliance)
12. [Related tools and positioning](#12-related-tools-and-positioning)
13. [PHUSE readiness](#13-phuse-readiness)
14. [Known limits and roadmap](#14-known-limits-and-roadmap)

---

## 1. What dsjson is

**Problem.** Regulators and CDISC are moving from SAS XPT v5 towards CDISC Dataset-JSON v1.1,
but most clinical programming teams have no tool, no evidence and no practice with the new
format. They wait for a mandate and lose the learning time.

**Solution.** dsjson converts SDTM datasets (XPT files) plus the study's Define-XML into
Dataset-JSON v1.1, validates every file, and explains what it found. It uses only what every
study already delivers, so a team can run it side by side with the current XPT process without
changing anything.

**Who it is for.**

| User | How they use it |
|---|---|
| Clinical programmers | Desktop app or command line to convert and review a study |
| Standards / metadata owners | Validation findings point at Define-XML quality issues |
| Tool builders | Python library (`ConversionService`) inside their own pipelines |

**What it is not (today).**

- Not a validated (GxP) system yet. See [GXP_ROADMAP.md](GXP_ROADMAP.md).
- Not for ADaM yet (ADaM numeric dates need `targetDataType`; see section 11).
- Does not read SAS7BDAT or CSV, and does not write NDJSON or compressed `.dsjc` yet.
- Does not replace Define-XML; it depends on it.

**Key facts.** Open source (MIT), Python 3.9+, runs fully offline, Windows desktop app and
command line. Verified on all 22 SDTM datasets of the public CDISC pilot study.

---

## 2. Background

### 2.1 SAS XPT v5

The SAS Version 5 transport format (1989) is still the format FDA requires for study data.
Its limits:

| Limit | Value |
|---|---|
| Character set | ASCII only |
| Variable name | 8 characters |
| Variable label | 40 characters |
| Character value | 200 characters |
| Metadata in file | Names, labels, types, lengths, formats only; no link to Define-XML |
| Tooling | Written and read mainly with SAS |

### 2.2 Dataset-JSON v1.1

A CDISC Data Exchange standard (v1.0 final 2023-08-23, **v1.1 final 2024-12-05**). One JSON
file holds exactly one dataset:

```text
{ file-level metadata (who, when, which study, which metadata version, which dataset),
  "columns": [ one object per variable: OID, name, label, type, length, key ],
  "rows":    [ one array per record, values in column order ] }
```

It is UTF-8 text, readable in any language, and carries OIDs that link every file, dataset and
variable back to Define-XML. CDISC also publishes an **NDJSON** representation (line 1 =
metadata, then one row per line, for streaming) and a **Compressed Dataset-JSON (DSJC)**
specification. Official repository:
https://github.com/cdisc-org/DataExchange-DatasetJson

### 2.3 Define-XML

The study's metadata document (based on CDISC ODM). For each dataset (`ItemGroupDef`) it lists
the variables (`ItemRef` -> `ItemDef`) with name, label, data type, length and key order.
Version 1.0 and 2.x exist and store some of this differently (section 5). dsjson uses
Define-XML as the source of truth for structure.

### 2.4 Where regulators stand (as of November 2026)

| When | What | Source |
|---|---|---|
| Sep 2023 - Apr 2024 | FDA, CDISC and PHUSE pilot Dataset-JSON for submissions | FDA Federal Register notice below |
| 2024-12-05 | CDISC publishes Dataset-JSON v1.1 | CDISC specification |
| 2025-04-09 | FDA requests public comments on accepting Dataset-JSON v1.1 (docket FDA-2025-N-0129, comments closed 2025-06-09) | Federal Register 90 FR 15251 |
| Today | XPT v5 still required; no FDA requirement date announced; no public PMDA/NMPA position found | FDA Data Standards Catalog |

**Re-check this the week before the talk** in the FDA Data Standards Catalog and the Study Data
Technical Conformance Guide. Most commentary online is secondary.

---

## 3. Field-by-field reference

Order below is the order the specification "strongly recommends" (it lets streaming readers
work). Example values are from the CDISC pilot DM dataset.

### 3.1 Top-level fields

| Field | Required? | Meaning (spec) | Where dsjson gets it | Example |
|---|---|---|---|---|
| `datasetJSONCreationDateTime` | Yes | When this file was created | Current time, UTC, `Z` suffix | `2026-11-19T18:48:10Z` |
| `datasetJSONVersion` | Yes | Version of the standard | Fixed | `1.1.0` |
| `fileOID` | No | Unique identifier of this dataset file | `studyOID` + `.` + dataset name in lower case; left out if Define-XML has no Study OID | `CDISCPILOT01.dm` |
| `dbLastModifiedDateTime` | No | When the source data was last modified; must be on or before the creation time | XPT file's internal modification time | `2012-04-04T22:16:21` |
| `originator` | No | Organisation that generated the file | Not written (decided: optional, left out for now) | - |
| `sourceSystem` | No | `{name, version}` of the system the content was sourced from; both required if present | dsjson and its version | `{"name": "dsjson", "version": "0.1.0"}` |
| `studyOID` | No | Study identifier; foreign key to Define-XML `Study/@OID` | Define-XML `Study/@OID` | `CDISCPILOT01` |
| `metaDataVersionOID` | No | Metadata version; foreign key to `MetaDataVersion/@OID` | Define-XML `MetaDataVersion/@OID` | `CDISC.SDTMIG.3.1.2` |
| `metaDataRef` | No | URI of the metadata file | Define-XML file name (a relative URI) | `define.xml` |
| `itemGroupOID` | Yes | Dataset identifier; foreign key to `ItemGroupDef/@OID` | Define-XML `ItemGroupDef/@OID` | `DM` |
| `records` | Yes | Number of records (0 allowed: metadata only) | Number of XPT rows | `306` |
| `name` | Yes | Dataset name | Requested dataset name (upper case) | `DM` |
| `label` | Yes | Dataset description | Define-XML (section 5) | `Demographics` |
| `columns` | Yes | Variable metadata | Section 3.2 | |
| `rows` | No | Records | XPT values in column order | |

> dsjson writes these fields in exactly this order (checked by `test_file_level_fields_and_status`).

### 3.2 Column fields

| Field | Required? | Meaning | Where dsjson gets it |
|---|---|---|---|
| `itemOID` | Yes | Variable identifier; foreign key to `ItemDef/@OID` | Define-XML `ItemDef/@OID` (e.g. `DM.USUBJID`) |
| `name` | Yes | Variable name | `ItemDef/@Name` |
| `label` | Yes | Variable description | `ItemDef` description (section 5) |
| `dataType` | Yes | Logical type: string, integer, decimal, float, double, boolean, datetime, date, time, URI | `ItemDef/@DataType`, mapped in section 4.3 |
| `targetDataType` | No | Type the receiver must convert to (`integer` or `decimal`) | Not written (backlog S3) |
| `length` | No | Planned number of characters | `ItemDef/@Length`, written for strings only |
| `displayFormat` | No | SAS display format for numbers and dates | Not written (backlog S2) |
| `keySequence` | No | Key variable and its order | `ItemRef/@KeySequence` (2.x) or `def:DomainKeys` (1.0) |

### 3.3 Rows

Each record is an array of values in column order. Missing numeric values are `null`; blank
character values are `""` (the spec: missing = `null`, empty string = `""`). Whole numbers stored
as floats in XPT (e.g. `1.0`) are written as integers (`1`). Dates stay ISO 8601 strings as in
SDTM.

---

## 4. How it works inside

### 4.1 Flow

```text
Define-XML ──► DefineXMLParser ──► columns, label, OIDs ─┐
                                                         ├─► checks ─► DatasetJSONBuilder ─► SchemaValidator ─► outputs
SDTM XPT ────► XPTReader ───────► records, XPT metadata ─┘                                    (+ row checks)
```

`ConversionService` drives the flow; the CLI, the desktop app and Python users all call it.

### 4.2 Code map

| File | Responsibility | Key functions |
|---|---|---|
| `dsjson/__init__.py` | Package version (`__version__ = "0.1.0"`, used by the app title and `sourceSystem`); exposes `ConversionService` | |
| `dsjson/__main__.py` | Lets `python -m dsjson ...` run the CLI; returns the CLI exit code | |
| `dsjson/cli.py` | `convert` and `convert-all` commands, summary table, exit codes | `main`, `_run_convert`, `_run_convert_all` |
| `dsjson/exceptions.py` | Error classes; `DSJSONError` is the base the CLI catches. Used: `DefineXMLParseError`, `DefineXMLDomainNotFoundError` | |
| `dsjson/services/conversion_service.py` | Orchestration, safety checks, validation, file writing, batch, cancel | `convert`, `convert_folder`, `write_outputs`, `status`, `_structure_issues`, `_validate` |
| `dsjson/metadata/define_xml.py` | Define-XML 1.0 / 2.x parser | `get_dataset_names`, `get_dataset_json_columns`, `get_dataset_label`, `get_item_group_oid`, `get_study_oid`, `get_metadata_version_oid` |
| `dsjson/readers/xpt_reader.py` | Reads XPT with pyreadstat (UTF-8, falls back to Windows-1252) | `read`, `get_records`, `dataset_name`, `modified_datetime` |
| `dsjson/builder/dataset_json.py` | Merges metadata, builds rows, writes optional fields in spec order | `build_dataset_json`, `merge_columns`, `build_rows` |
| `dsjson/validation/schema_validator.py` | JSON Schema + row checks | `validate_metadata`, `validate_rows`, `validate_dataset` |
| `dsjson/validation/schemas/` | Bundled official v1.1 JSON Schema | |
| `dsjson/reports/` | Validation report and batch summary | `ValidationReportBuilder.build`, `ConversionReport` |
| `dsjson/logging_config.py` | Log file + console set-up | `setup_logger` |
| `desktop_app/app.py` | App entry point: app name, dark colour scheme, Fusion style, Segoe UI font, opens `MainWindow` | `main` |
| `desktop_app/main_window.py` | Desktop UI | `MainWindow` |
| `desktop_app/worker.py` | Runs conversions in a background thread | `ConversionWorker` (`run`, `cancel`) |
| `desktop_app/table_filter.py` | Excel-style sort and filter | `RowsFilterProxy`, `FilterHeader`, `ColumnFilterPopup` |
| `scripts/fetch_pilot_data.py` | Downloads CDISC pilot XPTs, Define-XML, reference JSON | |
| `scripts/compare_with_reference.py` | Value-by-value comparison with reference files | `compare_dataset` |
| `scripts/manual/` | Older manual scripts (no assertions, not run by pytest) | |
| `__init__.py` files (`builder`, `services`, `metadata`, `validation`, `reports`, `readers`, `desktop_app`) | Package markers; some re-export the main class | |

### 4.2.1 Removed scaffolding

Early placeholder files that the conversion never used (an old `services.py`, `utils.py`,
`metadata/source_infer.py`, `metadata/spec_file.py`, `readers/base.py`, `readers/csv_reader.py`,
`readers/sas7bdat_reader.py`) were removed on 2026-11-20. SAS7BDAT input and metadata without
Define-XML remain backlog items R5 and R7.

### 4.3 Data type mapping (Define-XML -> Dataset-JSON)

| Define-XML `DataType` | Dataset-JSON `dataType` | JSON value |
|---|---|---|
| text, string | string | string |
| integer | integer | number (whole) |
| float, double, decimal | double | number |
| date, datetime, time | date, datetime, time | ISO 8601 string |
| boolean | boolean | true/false |
| anything else / missing | string | string |

Why `double` and not `decimal`: in v1.1, `decimal` values must be sent as **strings** with
`targetDataType: "decimal"`. XPT numbers are binary floating point anyway, so `double` with
JSON numbers is the faithful and valid choice. See section 11.

### 4.4 Design decisions

| Decision | Reason |
|---|---|
| Define-XML decides structure; XPT supplies values | Same metadata as the submission; no hand-written JSON |
| Fail instead of guessing when Define-XML and XPT disagree | A silently wrong file is worse than no file |
| Validate once, keep the reports | Speed; the same result feeds the report file and the UI |
| Batch continues after a failed dataset | One bad file must not hide the others |
| Status `CONVERTED` when validation is off | Never claim PASS for something that was not checked |
| In-process worker in the desktop app | No Python needed on PATH; logs stream live into the UI |
| Everything offline | Clinical data never leaves the machine |

---

## 5. Define-XML 1.0 vs 2.x

| Information | Define-XML 2.x | Define-XML 1.0 (e.g. CDISC pilot) | dsjson |
|---|---|---|---|
| Dataset identity | `ItemGroupDef @Name`, `@Domain` | `@Name` only (no `@Domain`) | Matches on `Name`, then `Domain` (so SUPPAE resolves to itself, not AE) |
| Dataset label | `Description/TranslatedText` | `def:Label` attribute | Reads either |
| Variable label | `Description/TranslatedText` | `def:Label` | Reads either |
| Key order | `ItemRef @KeySequence` | `def:DomainKeys` (comma list on the dataset) | Reads either |
| Data types | ODM types (text, integer, float, date, datetime, time...) | Same | Section 4.3 |

---

## 6. Validation and safety checks

### 6.1 Safety checks (before building)

| Check | Message | Effect |
|---|---|---|
| XPT holds a different dataset than requested | `ae.xpt holds dataset AE, not DM. Check the dataset name or pick the right file.` | Conversion refused (FAIL) |
| Variable in Define-XML but not in the XPT | `In Define-XML but not in the XPT file (column would be empty): AGE` | FAIL, even with validation off |
| Variable in the XPT but not in Define-XML | `In the XPT file but not in Define-XML (data would be dropped): SEX` | FAIL, even with validation off |
| Dataset not in Define-XML | `Domain not found in Define-XML: SC` (single) / `Not in Define-XML` (batch, SKIPPED) | FAIL / SKIPPED |
| Unreadable Define-XML | `Failed to parse Define-XML: <path> -> <reason>` | FAIL |

### 6.2 Schema validation

The bundled official CDISC Dataset-JSON v1.1 JSON Schema (Draft 2019-09) checks required fields,
types, patterns and structure. Any violation is an **error** (FAIL).

### 6.3 Row checks

| Check | Message | Level |
|---|---|---|
| `rows` is an array | `rows must be an array (list of rows)` | error |
| Columns present when rows exist | `columns must be a non-empty array when rows are present` | error |
| Record count | `records (N) does not match number of rows (M)` | error |
| Each row is an array | `Each row must be an array (list of values)` | error |
| Row length | `Row length (N) does not match columns length (M)` | error |
| Value fits integer type | `Value for LBSTRESN expected integer but got float` | warning |
| Value fits numeric type | `Value for X expected numeric but got str` | warning |
| Value fits boolean type | `Value for X expected boolean but got str` | warning |
| Duplicate key order | `Duplicate keySequence values detected in columns` | warning |
| Creation time zone | `datasetJSONCreationDateTime has no timezone offset/Z ...` | warning (dsjson always writes `Z`) |

### 6.4 Statuses

| Status | Meaning |
|---|---|
| PASS | Converted and validated, no errors (warnings allowed) |
| FAIL | An error, a safety check, or an exception |
| CONVERTED | Converted with validation switched off; nothing was validated |
| SKIPPED | Not in Define-XML, or cancelled before it started |

Warnings never fail a dataset: they are findings for people (usually metadata quality).

---

## 7. Using dsjson

### 7.1 Install

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

Windows Smart App Control can block numpy's DLLs in a new virtual environment; allow it in
Windows Security.

### 7.2 Desktop app

```bash
.venv/Scripts/python -m desktop_app.app
```

| Area | What it does |
|---|---|
| Header | Name and version (fixed; the steps below scroll) |
| 1 Define-XML | Pick `define.xml` |
| 2 SDTM data | **Whole folder**: lists every `.xpt`; datasets in Define-XML are ticked; others are greyed out with an amber note naming them. **Single XPT**: one file plus its dataset name |
| 3 Output | Output folder; validation on/off |
| Convert | Starts the run (Ctrl+Enter); progress bar; **Cancel conversion** stops before the next dataset |
| Stat cards | Datasets, passed, failed, records, total time |
| Dataset list | Chooses the dataset for Data preview, Columns and Validation report (hidden on Summary and Logs) |
| Summary tab | One row per dataset; **Details** gives the failure reason or the type warnings in words, blank otherwise |
| Data preview | All rows. Click a column name: ascending, descending, back to file order. Funnel or right-click: Excel-style value filter. The bar shows active filters and sort with Clear links |
| Columns tab | Variable metadata |
| Validation report | PASS/FAIL, counts, every issue as a sortable, filterable table; Open report file |
| Logs | Live log (warnings amber, errors red) |

Paths are remembered between runs. Popups and dialogs blur the window behind them. A loading
card shows while a large dataset opens.

### 7.3 Command line

```bash
dsjson convert -m DM -d define.xml -i dm.xpt
dsjson convert-all -i <xpt folder> -d define.xml [--datasets DM AE]
```

| Option | Commands | Default | Meaning |
|---|---|---|---|
| `--domain`, `-m` | convert | required | Dataset name |
| `--input`, `-i` | convert | required | XPT file |
| `--data-dir`, `-i` | convert-all | required | Folder of XPT files |
| `--datasets` | convert-all | all | Subset |
| `--define`, `-d` | both | required | Define-XML |
| `--out-dir`, `-o` | both | `./output` | Output folder |
| `--report-dir`, `-r` | both | `<out-dir>/validation_report` | Reports |
| `--log-dir`, `-l` | both | `<out-dir>/logs` | Log folder |
| `--no-validate` | both | off | Skip validation (status CONVERTED) |
| `-v`, `--log-level` | both | INFO | Logging |

Exit code 0 on success, 1 if any dataset fails. `python -m dsjson ...` works without the script
on PATH.

### 7.4 Python library

```python
from dsjson.services.conversion_service import ConversionService

service = ConversionService()
dataset_json = service.convert("DM", "define.xml", "dm.xpt")
service.write_outputs(dataset_json, "output", "output/validation_report")
print(service.status())                       # PASS / FAIL / CONVERTED

results = service.convert_folder("sdtm/", "define.xml", "output", "output/validation_report",
                                 datasets=["DM", "AE"], should_stop=lambda: False)
```

---

## 8. Outputs explained

```text
<out-dir>/
  DM.json                          Dataset-JSON v1.1 (one per dataset)
  validation_report/DM_validation.json
  logs/conversion.log
  conversion_summary.json          batch runs only
```

**Validation report** (`<DS>_validation.json`):

| Field | Meaning |
|---|---|
| `dataset`, `status`, `timestamp` | Which dataset, PASS/FAIL, when |
| `summary.errors`, `summary.warnings` | Counts |
| `metadata.status/errors/warnings` | Schema and safety-check results (messages) |
| `rows.status/errors/warnings` | Row checks, each with `message` and `path` (e.g. `/rows/41/12` = row 41, column 12, zero-based) |

**Batch summary** (`conversion_summary.json`): `summary` (total, passed, failed, pending,
skipped) and `results` (one entry per dataset: domain, status, message, records, columns,
errors, warnings, seconds). Note: `CONVERTED` is not counted in a separate total yet.

**Log**: every step with time, level and dataset tag, e.g.
`[LB] DONE | Errors: 0 | Warnings: 85741 | Time: 9.44s`.

---

## 9. Testing

Run everything (pilot tests skip if the pilot data is not downloaded):

```bash
.venv/Scripts/python scripts/fetch_pilot_data.py
.venv/Scripts/python -m pytest -q
```

Current result: **17 passed** (about 25-40 s).

| Test | Proves |
|---|---|
| **test_define_versions.py** | |
| `test_demo_define_v2_dm_columns` | Define-XML 2.1: DM's 29 columns, labels and dataset label |
| `test_pilot_define_v1_dataset_names` | Define-XML 1.0: all 22 dataset names found |
| `test_pilot_define_v1_labels_from_def_label` | Labels read from `def:Label` |
| `test_pilot_dates_keys_and_length` | Date types, `def:DomainKeys` key order, length only for strings |
| `test_pilot_supp_dataset_resolves_to_itself` | SUPPAE is not confused with AE |
| `test_unknown_dataset_raises` | Clear error for a dataset not in Define-XML |
| `test_bad_define_raises_parse_error` | Clear error for broken XML |
| **test_batch.py** | |
| `test_convert_folder_subset_matches_reference` | Batch of DM, TS, SUPPDM passes; DM and SUPPDM metadata, columns and rows equal the CDISC reference; summary and reports written |
| `test_all_pilot_datasets_match_reference_values` | All 22 pilot datasets PASS and match the CDISC reference value by value, with only the known, explained differences |
| `test_convert_folder_continues_after_bad_file` | One broken file does not stop the batch |
| **test_integrity.py** | |
| `test_structure_issues_flag_missing_and_extra_variables` | Variables only in Define-XML or only in XPT are errors |
| `test_file_level_fields_and_status` | studyOID, metaDataVersionOID, fileOID, metaDataRef, sourceSystem, dbLastModifiedDateTime; top-level fields in spec order; CONVERTED when validation is off |
| `test_wrong_dataset_name_is_refused` | `ae.xpt` named DM is refused |
| `test_cancel_skips_remaining_datasets` | Cancel stops before the next dataset |
| **test_desktop.py** (offscreen Qt) | |
| `test_worker_single_file_in_process` | The app converts in-process and writes outputs |
| `test_worker_batch_and_window_dataset_list` | Dataset list, summary, preview (all rows), columns, validation, Excel filter, numeric sort, clear sort, title/version |
| `test_details_explain_type_warnings` | Details text for type warnings and failures |

**Reference comparison method** (`scripts/compare_with_reference.py`): for each dataset it
compares top-level fields (name, label, itemGroupOID, records, fileOID, dbLastModifiedDateTime,
studyOID, metaDataVersionOID, metaDataRef), every column's metadata, and every cell (numbers
compared with tolerance 1e-9). Known differences the test accepts: TS 3 cells (apostrophe), TS
`dbLastModifiedDateTime`, and numeric type labels (VISITNUM in 9 datasets, LBSTRESN, VSSTRESN).

---

## 10. CDISC pilot evidence

**Data**: CDISC SDTM/ADaM pilot project, CDISCPILOT01, Define-XML 1.0, 22 SDTM datasets, public
(https://github.com/cdisc-org/sdtm-adam-pilot-project). Reference Dataset-JSON from the same
repository (created by CDISC with SAS 9.4).

**Results** (Windows 11 laptop, clean runs, November 2026):

| Measure | Value |
|---|---|
| Datasets | 22, all PASS, 0 failures |
| Records | 294,677 |
| Time | ~17-20 s with validation, ~11 s without |
| Values | Every cell identical to the reference except 3 in TS |

| Comparison result | Datasets |
|---|---|
| Identical | AE, DM, RELREC, SC, SE, SUPPAE, SUPPDM, SUPPDS, SUPPLB, TA, TE, TI |
| Values identical, one numeric type label differs | CM, DS, EX, LB, MH, QS, SV, TV, VS |
| 3 cells differ | TS |

**Every difference explained**

| Difference | Reason | Who is "right" |
|---|---|---|
| TS: 3 values with `’` vs `'` | The source XPT (Windows-1252) has a curly apostrophe; the reference changed it to a straight one | dsjson keeps the source value |
| TS `dbLastModifiedDateTime` 2012 vs 2024 | CDISC rebuilt its TS reference in Dec 2024; our ts.xpt is the 2012 file | Both correct for their source |
| VISITNUM `double` vs `decimal` | Define-XML says `float`; dsjson writes `double` (numbers). The reference says `decimal` but stores numbers without `targetDataType`, which the v1.1 rule for decimals does not allow | dsjson follows the spec |
| LBSTRESN / VSSTRESN `integer` vs reference type | Define-XML says integer; data holds decimals. dsjson follows Define-XML and warns | A metadata finding |

**Warnings found (metadata quality findings)**

| Variable | Define-XML says | Values that are decimals |
|---|---|---|
| LBSTRESN | integer | 35,431 |
| LBSTNRHI | integer | 26,348 |
| LBSTNRLO | integer | 23,962 |
| VSSTRESN | integer | 4,618 |
| CMDOSE | integer | 931 |
| QSSTRESN | integer | 28 |

---

## 11. Standards compliance

Checked against the official CDISC Dataset-JSON v1.1 specification (2024-12-05).

| Rule | Status |
|---|---|
| One dataset per file, `.json`, lowerCamelCase, UTF-8 | Yes |
| Required fields present; passes official JSON Schema | Yes |
| Recommended top-level order | Yes (fixed 2026-11-20; enforced by a test) |
| Column attribute order | Yes |
| `sourceSystem` has both name and version | Yes |
| `dbLastModifiedDateTime` <= creation time | Yes |
| Missing = `null`, empty = `""` | Yes |
| Dates as ISO 8601 strings (SDTM) | Yes |
| `decimal` as string + `targetDataType` | Not used: dsjson writes `double` (valid). Row check still treats `decimal` as numeric; align when S3 lands |
| `displayFormat`, `targetDataType` | Not written (backlog S2, S3; needed for ADaM) |
| NDJSON / DSJC representations | Not yet (backlog R3, R4) |

---

## 12. Related tools and positioning

| Project | What it is | Relation to dsjson |
|---|---|---|
| [cdisc-org/DataExchange-DatasetJson](https://github.com/cdisc-org/DataExchange-DatasetJson) | Official spec, schema, examples | Our schema and rules come from here |
| [cdisc-org/DataExchange-DatasetJson-API](https://github.com/cdisc-org/DataExchange-DatasetJson-API) | Draft API standard (OpenAPI 3.1, v1.0 draft 2025-08-07) for exchanging Dataset-JSON | Basis for our server stage |
| [swhume/dataset-json](https://github.com/swhume/dataset-json) (`dsjconvert`) | Python CLI/library by a creator of the standard: XPT/SAS7BDAT <-> JSON/NDJSON, Define-XML or inferred metadata, schema validation, round trip | Closest tool; complementary |
| [atorus-research/datasetjson](https://github.com/atorus-research/datasetjson) | R package (CRAN): read/write/validate JSON, NDJSON, DSJC from data frames | For R pipelines; can read our files |

**What dsjson adds**: a desktop workflow for non-programmers; safety checks that refuse silently
wrong output; findings in plain language; value-by-value evidence against the CDISC reference;
the adoption framework around it. We do not claim to be first, and prefer to contribute ideas
back.

---

## 13. PHUSE readiness

### 13.1 Guideline checklist

| Requirement | Source | Status |
|---|---|---|
| Slides named `PRE_XXnn.pptx` | Presentation Guidelines | Draft is `PRE_XXnn_draft.pptx`; fill in the number |
| Email address on slides | Presentation Guidelines | Placeholder `[work email]` on every slide |
| "PHUSE" in capitals | Presentation Guidelines | Yes |
| Company template allowed | Presentation Guidelines | Waiting for template |
| No promotion of commercial products/services | Commercial Content principles | dsjson is open source (MIT), shown as a method |
| Disclose and cite AI use (APA, tool + version/date); author accountable | PHUSE AI guidance | Closing slide; author must review everything |
| Paper `PAP_XXnn.pdf` (<=10 pages for 15 min, <=12 for 20-25 min) **or** video `VID_XXnn` | Acceptance email | **Open: confirm with Stream Chair** |
| Published publicly after the event | Presentation Guidelines | Public data only; no company data |
| Contact details in the material | Presentation Guidelines | Email + GitHub link (make the repo public or remove the link) |
| Speakers meeting, session time | Stream Chairs | Watch for emails |
| Company publication approval | Your employer | **Start now** |

### 13.2 Abstract promises -> slides

| Abstract promise | Slide(s) |
|---|---|
| Adoption gap XPT vs Dataset-JSON | 3, 5 |
| dsjson architecture | 7 |
| Use of Define-XML metadata | 8 |
| Schema validation | 9 |
| Lessons learned | 11 |
| Roadmap (desktop -> library -> server) | 14 |

### 13.3 Likely questions and answers

| Question | Answer |
|---|---|
| Why not just use dsjconvert or the R package? | They are good tools and complementary. dsjson adds a desktop workflow for non-programmers, checks that refuse silently wrong output, plain-language findings, and value-by-value evidence against CDISC's reference. |
| Is it validated for GxP use? | Not yet. Today it is for piloting side by side. The GxP plan is audit trail, independent reconciliation and IQ/OQ evidence; the process side (URS, risk assessment, SOPs) belongs to each company's QA. |
| Why does VISITNUM say `double` when CDISC's file says `decimal`? | Define-XML says `float`. In v1.1, `decimal` must be sent as text with `targetDataType`; CDISC's reference stores numbers instead. `double` with numbers is valid and faithful to XPT. |
| What about ADaM? | Next: ADaM numeric dates need `targetDataType: integer` and `displayFormat`. Planned. |
| Large datasets? | QS (121k rows) converts in seconds. NDJSON (official CDISC representation) is on the roadmap for streaming. |
| Does FDA accept Dataset-JSON now? | Not yet required; FDA asked for comments in April 2025. Status as of the talk date (re-check). |
| How do you know nothing was lost? | Every cell compared with CDISC's reference; safety checks on structure; round-trip check planned. |
| What if Define-XML is wrong? | The warnings show it, e.g. 35,431 LBSTRESN decimals declared integer. That is a benefit of piloting. |
| Can it run without Define-XML? | No, by design: Define-XML is the source of truth. |
| Data privacy? | Runs fully offline; nothing leaves the computer. |
| Which Define-XML versions? | 1.0 and 2.x. |
| AI use? | Built with AI assistance (disclosed on the closing slide); all code tested and reviewed by the author. |

### 13.4 Before the talk

- Done: field order (S1) and removal of unused scaffolding (A4).
- Re-verify regulatory status (FDA catalog) and re-measure timing on the presentation laptop.
- Record the demo video; keep a backup copy and the poster image.
- Rehearse to ~20 minutes, leaving 4-5 minutes for questions.

---

## 14. Known limits and roadmap

| Limit today | Plan |
|---|---|
| SDTM only (no ADaM date handling) | `targetDataType`, `displayFormat` (backlog S2, S3, S5) |
| XPT input only | SAS7BDAT (R5) |
| JSON output only | NDJSON (R3), DSJC (R4) |
| Desktop + CLI | PyPI library (R8), then server on the CDISC Dataset-JSON API (R9) |
| Not GxP-validated | [GXP_ROADMAP.md](GXP_ROADMAP.md) |
| No `.exe` | PyInstaller build (A1) |

Full list: [IMPROVEMENT_BACKLOG.md](IMPROVEMENT_BACKLOG.md).
