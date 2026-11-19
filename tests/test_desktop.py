"""Desktop app smoke tests (offscreen Qt, no clicks needed)."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")
QtCore = pytest.importorskip("PySide6.QtCore")

from desktop_app.main_window import MainWindow  # noqa: E402
from desktop_app.worker import ConversionWorker  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "demo" / "input" / "cdiscpilot01"


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _run(worker):
    logs, results, finished = [], [], []
    worker.log_message.connect(logs.append)
    worker.results_ready.connect(results.extend)
    worker.finished.connect(lambda ok, msg: finished.append((ok, msg)))
    worker.run()  # same thread: signals are delivered directly
    return logs, results, finished


def test_worker_single_file_in_process(app, tmp_path):
    logs, results, finished = _run(ConversionWorker(
        define_path=str(ROOT / "demo" / "input" / "define.xml"),
        output_dir=str(tmp_path),
        domain="DM",
        xpt_path=str(ROOT / "demo" / "input" / "sdtm" / "DM.xpt"),
    ))
    assert finished == [(True, "1 dataset(s) converted successfully.")]
    assert results[0]["status"] == "PASS"
    assert (tmp_path / "DM.json").exists() and (tmp_path / "validation_report" / "DM_validation.json").exists()
    assert any("[DM] DONE" in line for line in logs)


def test_worker_batch_and_window_dataset_list(app, tmp_path):
    if not (PILOT / "define.xml").exists():
        pytest.skip("pilot data missing (run scripts/fetch_pilot_data.py)")

    window = MainWindow()
    window.define_input.setText(str(PILOT / "define.xml"))
    window.folder_input.setText(str(PILOT / "sdtm"))
    window.refresh_dataset_list()
    assert window.dataset_list.count() == 22
    assert len(window._checked_datasets()) == 22

    _, results, finished = _run(ConversionWorker(
        define_path=str(PILOT / "define.xml"),
        output_dir=str(tmp_path),
        data_dir=str(PILOT / "sdtm"),
        datasets=["DM", "TS"],
    ))
    assert finished[0][0] is True

    window.output_input.setText(str(tmp_path))
    window.show_summary(results)
    assert window.stat_values["passed"].text() == "2"
    assert [window.dataset_combo.itemText(i) for i in range(window.dataset_combo.count())] == ["DM", "TS"]
    details = {window.summary_table.item(r, 0).text(): window.summary_table.item(r, 7).text() for r in range(2)}
    assert details["DM"] == ""  # no warnings, nothing to say
    assert window.windowTitle().startswith("dsjson ") and window.cancel_button.isHidden()

    window.dataset_combo.setCurrentText("DM")  # loads preview, columns, validation
    assert window.open_json_button.isEnabled()
    assert window.preview_model.rowCount() == 306  # all rows, no cap
    assert window.columns_table.rowCount() == 25
    assert "PASS" in window.validation_status.text()

    # Excel-style: distinct values per column, filter, sort both ways, clear sort
    sex = window.preview_model._headers.index("SEX")
    values = dict(window.preview_proxy.distinct_values(sex))
    assert set(values) == {"F", "M"} and sum(values.values()) == 306
    window._apply_column_filter(window.preview_view, sex, {"F"})
    assert window.preview_proxy.rowCount() == values["F"]
    assert "SEX" in window.filter_summary.text() and not window.clear_filters_button.isHidden()
    age = window.preview_model._headers.index("AGE")
    window.preview_view.sortByColumn(age, QtCore.Qt.AscendingOrder)
    ages = [int(window.preview_proxy.index(r, age).data()) for r in range(window.preview_proxy.rowCount())]
    assert ages == sorted(ages)  # numeric, not text, order
    window.preview_view.sortByColumn(age, QtCore.Qt.DescendingOrder)
    assert int(window.preview_proxy.index(0, age).data()) == max(ages)
    assert "sorted by" in window.filter_summary.text()
    first_unsorted = window.preview_model._original[0]
    window.clear_preview_sort()
    assert window.preview_model.rows[0] is first_unsorted  # back to file order
    window.clear_preview_filters()
    assert window.preview_proxy.rowCount() == 306


def test_details_explain_type_warnings(tmp_path):
    report = {"rows": {"warnings": [{"message": "Value for LBSTRESN expected integer but got float"}] * 3}}
    (tmp_path / "LB_validation.json").write_text(__import__("json").dumps(report))
    text = MainWindow._details({"dataset": "LB", "status": "PASS", "warnings": 3, "message": ""}, tmp_path)
    assert text == "LBSTRESN: Define-XML says integer, 3 value(s) are float"
    assert MainWindow._details({"dataset": "XX", "status": "FAIL", "message": "boom"}, tmp_path) == "boom"
