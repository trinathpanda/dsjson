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
- **Batch:** convert a whole folder in one run; one bad file does not stop the others.

## Verified on the CDISC pilot study

All 22 SDTM datasets of the public CDISC pilot study (CDISCPILOT01, Define-XML 1.0,
~295,000 records) convert and pass validation in about 15 seconds. Compared with CDISC's
own reference Dataset-JSON files, **every cell value matches** except 3 apostrophes in TS:

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
   listed and ticked) or **Single XPT**.
3. **Output:** pick a folder; keep validation on.
4. Click **Convert to Dataset-JSON** (or press Ctrl+Enter).

Results appear on the right: totals (datasets, passed, failed, records, time) and tabs for
**Summary** (one row per dataset), **Data preview** (all rows, with a filter),
**Columns** (variable metadata), **Validation report** and **Logs**. Paths are remembered
between runs. The app converts in-process; no data leaves the computer.

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
.venv/Scripts/python -m pytest tests/test_define_versions.py tests/test_batch.py tests/test_desktop.py -q
```

| Test file | Covers |
|---|---|
| `tests/test_define_versions.py` | Define-XML 1.0 and 2.x parsing, labels, types, keys, errors |
| `tests/test_batch.py` | Batch conversion; all 22 pilot datasets against the CDISC reference |
| `tests/test_desktop.py` | Desktop worker and window (offscreen Qt) |

Pilot-data tests skip when the data has not been downloaded. The older
`tests/test_pipeline.py`, `test_validator.py`, `test_xptreader.py` and
`test_defineparser.py` are manual scripts without assertions.

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
desktop_app/                      PySide6 desktop app (in-process worker)
scripts/                          pilot data download and reference comparison
tests/                            pytest suite
```

## Status and roadmap

- Done: XPT + Define-XML to Dataset-JSON v1.1, batch conversion, validation reports,
  desktop app, verification on the CDISC pilot study.
- Next: Windows `.exe` packaging (PyInstaller).
- Not yet: SAS7BDAT/CSV input, specification-file metadata, optional top-level fields
  (`studyOID`, `metaDataVersionOID`, `sourceSystem`, ...), NDJSON output.
- Roadmap: offline desktop app (piloting) → reusable Python library → server-based
  automation.

## License

MIT
