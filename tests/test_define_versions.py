"""Define-XML parsing for both Define-XML 1.0 (CDISC pilot) and 2.x (demo)."""

from pathlib import Path

import pytest

from dsjson.exceptions import DefineXMLDomainNotFoundError, DefineXMLParseError
from dsjson.metadata.define_xml import DefineXMLParser

ROOT = Path(__file__).resolve().parent.parent
DEMO_DEFINE = ROOT / "demo" / "input" / "define.xml"
PILOT_DEFINE = ROOT / "demo" / "input" / "cdiscpilot01" / "define.xml"


def _parser(path: Path) -> DefineXMLParser:
    if not path.exists():
        pytest.skip(f"missing {path} (run scripts/fetch_pilot_data.py)")
    parser = DefineXMLParser(path)
    parser.parse()
    return parser


def test_demo_define_v2_dm_columns():
    parser = _parser(DEMO_DEFINE)
    cols = parser.get_dataset_json_columns("DM")
    assert len(cols) == 29
    assert cols[0]["name"] == "STUDYID"
    assert cols[0]["label"] == "Study Identifier"
    assert parser.get_dataset_label("DM") == "Demographics"


def test_pilot_define_v1_dataset_names():
    names = _parser(PILOT_DEFINE).get_dataset_names()
    for ds in ("DM", "AE", "LB", "SUPPDM", "SUPPLB", "TS"):
        assert ds in names


def test_pilot_define_v1_labels_from_def_label():
    parser = _parser(PILOT_DEFINE)
    assert parser.get_dataset_label("DM") == "Demographics"
    cols = {c["name"]: c for c in parser.get_dataset_json_columns("AE")}
    assert cols["STUDYID"]["label"] == "Study Identifier"
    assert cols["AESEQ"]["dataType"] == "integer"


def test_pilot_dates_keys_and_length():
    cols = {c["name"]: c for c in _parser(PILOT_DEFINE).get_dataset_json_columns("DM")}
    assert cols["STUDYID"]["keySequence"] == 1  # from def:DomainKeys
    assert cols["USUBJID"]["keySequence"] == 2
    assert "keySequence" not in cols["AGE"]
    assert cols["RFSTDTC"]["dataType"] == "date"
    assert cols["RFXSTDTC"]["dataType"] == "datetime"
    assert "length" not in cols["RFSTDTC"] and "length" not in cols["AGE"]
    assert cols["USUBJID"]["length"] == 11


def test_pilot_supp_dataset_resolves_to_itself():
    parser = _parser(PILOT_DEFINE)
    assert parser.get_domain("SUPPDM").attrib["Name"] == "SUPPDM"
    assert parser.get_domain("suppdm").attrib["Name"] == "SUPPDM"


def test_unknown_dataset_raises():
    with pytest.raises(DefineXMLDomainNotFoundError):
        _parser(DEMO_DEFINE).get_domain("ZZ")


def test_bad_define_raises_parse_error(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("not xml <", encoding="utf-8")
    with pytest.raises(DefineXMLParseError):
        DefineXMLParser(bad).parse()
