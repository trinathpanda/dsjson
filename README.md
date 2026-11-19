# dsjson

**dsjson** converts SDTM datasets (SAS XPT) plus Define-XML metadata into
[CDISC Dataset-JSON v1.1](https://www.cdisc.org/standards/data-exchange/dataset-json).
It runs fully offline as a Python library, a command-line tool and a Windows desktop app.

The goal is a low-risk way to pilot Dataset-JSON next to an existing XPT submission
workflow: you reuse the XPT files and Define-XML every study already has, and nothing
in the current process changes.

## How it works

```text
Define-XML  (structure: names, labels, types, lengths, keys)
     +                                  ->  DSJSON engine  ->  <DS>.json               (Dataset-JSON v1.1)
SDTM XPT    (data: records and values)       merge + build      validation_report/      (schema + row checks)
                                             validate           logs/conversion.log     (execution log)
                                                                conversion_summary.json (batch only)
```

- **Metadata-driven:** Define-XML decides columns, labels, data types, lengths and key
  sequence; the XPT file supplies the values. Nobody writes JSON by hand.
- **Define-XML 1.0 and 2.x:** datasets are matched by `Name` (then `Domain`), labels come
  from `Description/TranslatedText` or `def:Label`, key sequence from `KeySequence` or
  `def:DomainKeys`.
- **Validation:** every file is checked against the bundled Dataset-JSON v1.1 JSON Schema,
  plus row checks (row length, record count, values that do not fit the Define-XML type).
- **Safety checks:** a dataset fails (never a silent wrong file) when the XPT holds a
  different dataset than the one named, or when a variable is only in Define-XML (empty
  column) or only in the XPT (data would be dropped). With validation switched off the status
  is `CONVERTED`, not `PASS`.
- **File-level metadata:** `studyOID`, `metaDataVersionOID`, `metaDataRef` and `fileOID` come
  from Define-XML; `dbLastModifiedDateTime` from the XPT file.
- **Batch:** convert a whole folder in one run; one bad file does not stop the others, and
  a run can be cancelled between datasets.

## Verified on the CDISC pilot study

All 22 SDTM datasets of the public CDISC pilot study (CDISCPILOT01, Define-XML 1.0,
~295,000 records) convert and pass validation in about 20 seconds (11 seconds without
validation; Windows 11 laptop). Compared with CDISC's own reference Dataset-JSON files,
**every cell value matches** except 3 apostrophes in TS, and the five file-level fields
above match too (TS `dbLastModifiedDateTime` differs: CDISC rebuilt its TS in 2024):

| Result | Datasets |
|---|---|
| Identical to the reference | AE, DM, RELREC, SC, SE, SUPPAE, SUPPDM, SUPPDS, SUPPLB, TA, TE, TI |
| All values identical, one numeric type label differs | CM, DS, EX, LB, MH, QS, SV, TV, VS |
| 3 cells differ | TS: dsjson keeps the source's curly `’`, the reference has `'` |

The type-label differences are places where the reference departs from the pilot
Define-XML (for example VISITNUM is `float` in Define-XML; dsjson writes `double`, the
reference `decimal`). dsjson follows Define-XML and reports a warning when the data does
not fit it, e.g. LBSTRESN is `integer` in Define-XML but holds decimals.

## Install

Requires Python 3.9+ (tested with 3.14 on Windows 11).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

> Windows Smart App Control can block numpy's DLLs inside a new virtual environment
> (`An Application Control policy has blocked this file`). Allow it in Windows Security
> or use an environment where pandas already works.

## Desktop app

```bash
.venv/Scripts/python -m desktop_app.app
```

1. **Define-XML:** pick the study's `define.xml`.
2. **SDTM data:** choose **Whole folder** (all `.xpt` files that Define-XML describes are
   listed and ticked) or **Single XPT**. Files that the chosen Define-XML does not describe
   are greyed out, with a note naming them (usually Define-XML and data from different studies).
3. **Output:** pick a folder; keep validation on.
4. Click **Convert to Dataset-JSON** (or press Ctrl+Enter).

Results appear on the right, in a dark theme:

| Tab | Shows |
|---|---|
| **Summary** | One row per dataset: status, records, columns, errors, warnings, time. **Details** gives the failure reason, or which variables do not fit their Define-XML type (e.g. `LBSTRESN: Define-XML says integer, 35,431 value(s) are float`); blank when all is fine. |
| **Data preview** | All rows of the selected dataset. Click a column name to sort (ascending, descending, then file order). Click the funnel or right-click a column to filter by its distinct values, like Excel. A bar above the table lists active filters and sort, with **Clear filters** / **Clear sort**. |
| **Columns** | Variable metadata: name, label, data type, length, key sequence, item OID. |
| **Validation report** | PASS/FAIL with error and warning counts, and every issue as a sortable, filterable table; **Open report file** opens the JSON report. |
| **Logs** | The conversion log (warnings amber, errors red). |

Pick the dataset to inspect in the **Dataset** list above the tabs (or click a row in
Summary). Paths are remembered between runs. The app converts in-process; no data leaves
the computer.

## Command line

<!-- AUTO-GENERATED: from dsjson/cli.py argparse definitions -->
| Command | Description |
|---|---|
| `dsjson convert -m DM -d define.xml -i dm.xpt` | Convert one XPT file |
| `dsjson convert-all -i <xpt folder> -d define.xml` | Convert every XPT in a folder that Define-XML describes |

| Option | Commands | Default | Description |
|---|---|---|---|
| `--domain`, `-m` | convert | required | Dataset name, e.g. `DM` |
| `--input`, `-i` | convert | required | XPT file |
| `--data-dir`, `-i` | convert-all | required | Folder with XPT files |
| `--datasets` | convert-all | all | Only these datasets, e.g. `--datasets DM AE` |
| `--define`, `-d` | both | required | Define-XML file |
| `--out-dir`, `-o` | both | `./output` | Dataset-JSON output folder |
| `--report-dir`, `-r` | both | `<out-dir>/validation_report` | Validation reports |
| `--log-dir`, `-l` | both | `<out-dir>/logs` | `conversion.log` folder |
| `--no-validate` | both | off | Skip validation and reports |
| `-v`, `--verbose` / `--log-level` | both | `INFO` | Log level |
<!-- END AUTO-GENERATED -->

Exit code is `0` on success and `1` if any dataset fails. Use `python -m dsjson ...` when
the `dsjson` script is not on PATH.

Example with the CDISC pilot data:

```bash
.venv/Scripts/python -m dsjson convert-all -i demo/input/cdiscpilot01/sdtm -d demo/input/cdiscpilot01/define.xml -o demo/output/pilot
```

## Python library

```python
from dsjson.services.conversion_service import ConversionService

service = ConversionService()

# one dataset
dataset_json = service.convert("DM", "define.xml", "dm.xpt")
service.write_outputs(dataset_json, "output", "output/validation_report")

# a whole folder
results = service.convert_folder("sdtm/", "define.xml", "output", "output/validation_report")
```

## Scripts and test data

<!-- AUTO-GENERATED: from scripts/ -->
| Script | Description |
|---|---|
| `scripts/fetch_pilot_data.py` | Download the CDISC pilot XPT files, `define.xml` and reference Dataset-JSON (~200 MB) into `demo/input/cdiscpilot01/` (git-ignored) |
| `scripts/compare_with_reference.py <our_dir> <ref_dir>` | Compare output with reference Dataset-JSON per dataset; writes `comparison.json` |
<!-- END AUTO-GENERATED -->

`demo/input/` also holds a small synthetic Define-XML 2.1 study with `DM.xpt`.

## Tests

```bash
.venv/Scripts/python scripts/fetch_pilot_data.py
.venv/Scripts/python -m pytest -q
```

| Test file | Covers |
|---|---|
| `tests/test_define_versions.py` | Define-XML 1.0 and 2.x parsing, labels, types, keys, errors |
| `tests/test_batch.py` | Batch conversion; all 22 pilot datasets against the CDISC reference |
| `tests/test_integrity.py` | Wrong-dataset guard, Define-XML vs XPT variable checks, file-level fields, `CONVERTED` status, cancel |
| `tests/test_desktop.py` | Desktop worker and window (offscreen Qt): dataset list, preview, column filter and sort, Details text |

Pilot-data tests skip when the data has not been downloaded. Older manual scripts without
assertions live in `scripts/manual/` (not collected by pytest).

## Project layout

```text
dsjson/
  cli.py                          convert / convert-all commands
  services/conversion_service.py  orchestration, batch, output writing
  metadata/define_xml.py          Define-XML 1.0 / 2.x parser
  readers/xpt_reader.py           XPT reader (pyreadstat; UTF-8, falls back to cp1252)
  builder/dataset_json.py         Dataset-JSON v1.1 builder
  validation/                     JSON Schema + row validation (schema bundled)
  reports/                        validation and batch summary reports
desktop_app/                      PySide6 desktop app (in-process worker, Excel-style table filter)
scripts/                          pilot data download and reference comparison
tests/                            pytest suite
```

## Status and roadmap

- Done: XPT + Define-XML to Dataset-JSON v1.1, batch conversion, validation reports,
  desktop app, verification on the CDISC pilot study.
- Next: Windows `.exe` packaging (PyInstaller).
- Not yet: SAS7BDAT/CSV input, specification-file metadata, `sourceSystem` and
  `originator` fields, NDJSON output.
- Later: GxP readiness (audit trail, reconciliation, IQ/OQ evidence), see
  [docs/GXP_ROADMAP.md](docs/GXP_ROADMAP.md).
- Releases are tagged (`v0.1.0`); the version shows in the app title.
- Roadmap: offline desktop app (piloting) → reusable Python library → server-based
  automation.

## License

MIT
