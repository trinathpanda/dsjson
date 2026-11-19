"""Guards against silently wrong output, plus file-level fields, status and cancel."""

from pathlib import Path

import pytest

from dsjson.services.conversion_service import ConversionService
from dsjson.validation.schema_validator import SchemaValidator

ROOT = Path(__file__).resolve().parent.parent
DEFINE = ROOT / "demo" / "input" / "define.xml"
DM_XPT = ROOT / "demo" / "input" / "sdtm" / "DM.xpt"
PILOT = ROOT / "demo" / "input" / "cdiscpilot01"


def test_structure_issues_flag_missing_and_extra_variables():
    define = [{"name": "STUDYID"}, {"name": "USUBJID"}, {"name": "AGE"}]
    xpt = [{"name": "STUDYID"}, {"name": "USUBJID"}, {"name": "SEX"}]
    messages = [i.message for i in ConversionService._structure_issues(define, xpt)]
    assert messages == [
        "In Define-XML but not in the XPT file (column would be empty): AGE",
        "In the XPT file but not in Define-XML (data would be dropped): SEX",
    ]
    assert ConversionService._structure_issues(define, define) == []


def test_file_level_fields_and_status():
    service = ConversionService()
    dataset_json = service.convert("DM", str(DEFINE), str(DM_XPT))
    assert service.status() == "PASS"
    assert dataset_json["studyOID"] and dataset_json["metaDataVersionOID"]
    assert dataset_json["fileOID"] == f"{dataset_json['studyOID']}.dm"
    assert dataset_json["metaDataRef"] == "define.xml"
    assert len(dataset_json["dbLastModifiedDateTime"]) == 19  # YYYY-MM-DDTHH:MM:SS

    unchecked = ConversionService(validator=SchemaValidator(skip_validation=True))
    unchecked.convert("DM", str(DEFINE), str(DM_XPT))
    assert unchecked.status() == "CONVERTED"  # not "PASS" when nothing was validated


@pytest.mark.skipif(not (PILOT / "define.xml").exists(), reason="pilot data missing")
def test_wrong_dataset_name_is_refused():
    with pytest.raises(ValueError, match="holds dataset AE, not DM"):
        ConversionService().convert("DM", str(PILOT / "define.xml"), str(PILOT / "sdtm" / "ae.xpt"))


@pytest.mark.skipif(not (PILOT / "define.xml").exists(), reason="pilot data missing")
def test_cancel_skips_remaining_datasets(tmp_path):
    calls = []

    def stop_after_first():
        calls.append(1)
        return len(calls) > 1

    results = ConversionService().convert_folder(
        str(PILOT / "sdtm"), str(PILOT / "define.xml"), str(tmp_path), datasets=["DM", "TA", "TE"],
        should_stop=stop_after_first,
    )
    assert [r["status"] for r in results] == ["PASS", "SKIPPED", "SKIPPED"]
    assert [r.get("message") for r in results[1:]] == ["Cancelled", "Cancelled"]
