"""Batch conversion of the CDISC pilot study (needs scripts/fetch_pilot_data.py)."""

import json
from pathlib import Path

import pytest

from dsjson.services.conversion_service import ConversionService

PILOT = Path(__file__).resolve().parent.parent / "demo" / "input" / "cdiscpilot01"


@pytest.fixture
def pilot():
    if not (PILOT / "define.xml").exists():
        pytest.skip("pilot data missing (run scripts/fetch_pilot_data.py)")
    return PILOT


def test_convert_folder_subset_matches_reference(pilot, tmp_path):
    results = ConversionService().convert_folder(
        str(pilot / "sdtm"), str(pilot / "define.xml"), str(tmp_path), str(tmp_path / "reports"),
        datasets=["dm", "TS", "SUPPDM"],
    )
    assert {r["dataset"]: r["status"] for r in results} == {"DM": "PASS", "SUPPDM": "PASS", "TS": "PASS"}

    for ds in ("DM", "SUPPDM"):
        ours = json.loads((tmp_path / f"{ds}.json").read_text(encoding="utf-8"))
        ref = json.loads((pilot / "reference" / f"{ds.lower()}.json").read_text(encoding="utf-8"))
        for key in ("itemGroupOID", "name", "label", "records", "columns", "rows"):
            assert ours[key] == ref[key], f"{ds}.{key}"

    summary = json.loads((tmp_path / "conversion_summary.json").read_text(encoding="utf-8"))
    assert summary["summary"]["passed"] == 3
    assert (tmp_path / "reports" / "DM_validation.json").exists()


def test_all_pilot_datasets_match_reference_values(pilot, tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "compare_with_reference", Path(__file__).resolve().parent.parent / "scripts" / "compare_with_reference.py"
    )
    compare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare)

    results = ConversionService().convert_folder(str(pilot / "sdtm"), str(pilot / "define.xml"), str(tmp_path))
    assert len(results) == 22 and all(r["status"] == "PASS" for r in results)

    # Known, explained differences vs CDISC's reference (reference departs from Define-XML)
    known_cells = {"TS": 3}  # reference turned the source's curly apostrophe into "'"
    # reference TS was rebuilt in Dec 2024; our ts.xpt is the 2012 file, so its modified time differs
    known_top = {"TS": {"dbLastModifiedDateTime"}}
    known_types = {("LB", "LBSTRESN"), ("VS", "VSSTRESN")} | {
        (ds, "VISITNUM") for ds in ("CM", "DS", "EX", "LB", "MH", "QS", "SV", "TV", "VS")
    }
    for ref_path in sorted((pilot / "reference").glob("*.json")):
        ds = ref_path.stem.upper()
        ours = json.loads((tmp_path / f"{ds}.json").read_text(encoding="utf-8"))
        r = compare.compare_dataset(ours, json.loads(ref_path.read_text(encoding="utf-8")))
        assert set(r["top"]) == known_top.get(ds, set()), (ds, r["top"])
        assert r["cells"] == known_cells.get(ds, 0), (ds, r["cell_examples"])
        for diff in r["columns"]:
            assert diff.get("key") == "dataType" and (ds, diff["column"]) in known_types, (ds, diff)


def test_convert_folder_continues_after_bad_file(pilot, tmp_path):
    data = tmp_path / "sdtm"
    data.mkdir()
    (data / "dm.xpt").write_bytes((pilot / "sdtm" / "dm.xpt").read_bytes())
    (data / "ae.xpt").write_bytes(b"not an xpt file")

    results = ConversionService().convert_folder(str(data), str(pilot / "define.xml"), str(tmp_path / "out"))
    status = {r["dataset"]: r["status"] for r in results}
    assert status == {"AE": "FAIL", "DM": "PASS"}
