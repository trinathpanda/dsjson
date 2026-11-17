"""Main window for the dsjson desktop application.

Layout: input sidebar (left) | results area (right), split by a draggable splitter.
"""

from __future__ import annotations

import html
import json
from collections import Counter
import re
from contextlib import contextmanager
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QEventLoop,
    QModelIndex,
    QSettings,
    QSize,
    Qt,
    QThread,
    QUrl,
)
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsBlurEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from dsjson.metadata.define_xml import DefineXMLParser
from desktop_app.table_filter import BLANK_LABEL, ColumnFilterPopup, FilterHeader, RowsFilterProxy, sort_key
from desktop_app.worker import ConversionWorker

SUMMARY_HEADERS = ["Dataset", "Status", "Records", "Columns", "Errors", "Warnings", "Time (s)", "Details"]
SUMMARY_KEYS = ["dataset", "status", "records", "columns", "errors", "warnings", "seconds", "message"]
COLUMN_HEADERS = ["#", "Name", "Label", "Data type", "Length", "Key seq.", "Item OID"]
VALIDATION_HEADERS = ["Severity", "Check", "Location", "Message"]
CHEVRON = (Path(__file__).parent / "assets" / "chevron-down.svg").as_posix()

PASS_COLOR = QColor("#4ADE80")
FAIL_COLOR = QColor("#F87171")
MUTED_COLOR = QColor("#94A3B8")
WARN_COLOR = QColor("#FBBF24")
TEXT_COLOR = QColor("#E2E8F0")

# One place for the look: dark slate surfaces, blue accent, 4.5:1+ text contrast
STYLE = """
QMainWindow, QWidget#results { background: #0B1120; }
QWidget { color: #E2E8F0; }
QWidget#sidebar { background: #111827; }
QScrollArea#sidebarScroll { border: none; border-right: 1px solid #1F2937; background: #111827; }
QLabel#appTitle { font-size: 17pt; font-weight: 700; color: #F8FAFC; }
QLabel#muted { color: #94A3B8; }
QLabel#warning { color: #FBBF24; }
QLabel#stepTitle { font-size: 10.5pt; font-weight: 600; color: #93C5FD; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 600; color: #F1F5F9; }
QFrame#card { background: #161F30; border: 1px solid #243045; border-radius: 10px; }
QFrame#stat { background: #161F30; border: 1px solid #243045; border-top: 3px solid #3B82F6; border-radius: 10px; }
QLabel#statValue { font-size: 18pt; font-weight: 700; color: #F8FAFC; }
QLabel#statCaption { color: #94A3B8; font-size: 9pt; }
QLineEdit, QComboBox {
    background: #0F172A; border: 1px solid #334155; border-radius: 6px; padding: 5px 8px; min-height: 20px;
    selection-background-color: #2563EB;
}
QLineEdit:hover, QComboBox:hover { border-color: #475569; }
QLineEdit:focus, QComboBox:focus { border: 2px solid #3B82F6; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; border: none; border-left: 1px solid #334155; width: 24px; }
QComboBox::down-arrow { image: url(@CHEVRON@); width: 12px; height: 12px; }
QComboBox::down-arrow:on { top: 1px; }
QComboBox QAbstractItemView {
    background: #111827; border: 1px solid #334155; selection-background-color: #1E3A8A; outline: none;
}
QPushButton {
    background: #1E293B; border: 1px solid #334155; border-radius: 6px; padding: 5px 12px; min-height: 22px;
}
QPushButton:hover { background: #273449; border-color: #475569; }
QPushButton:pressed { background: #0F172A; }
QPushButton:focus { border: 2px solid #3B82F6; }
QPushButton:disabled { color: #64748B; background: #111827; border-color: #1F2937; }
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #4F46E5);
    color: #FFFFFF; border: none; border-radius: 8px; font-size: 11pt; font-weight: 600; padding: 10px; min-height: 26px;
}
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1); }
QPushButton#primary:pressed { background: #1D4ED8; }
QPushButton#primary:focus { border: 2px solid #FBBF24; }
QPushButton#primary:disabled { background: #334155; color: #94A3B8; }
QPushButton#segment { border-radius: 0; padding: 6px 10px; }
QPushButton#segment:checked { background: #2563EB; color: #FFFFFF; border-color: #2563EB; font-weight: 600; }
QPushButton#link { border: none; background: transparent; color: #60A5FA; padding: 2px 4px; min-height: 16px; }
QPushButton#link:hover { color: #93C5FD; text-decoration: underline; }
QListWidget { border: 1px solid #334155; border-radius: 6px; background: #0F172A; outline: none; }
QListWidget::item { padding: 3px 4px; border-radius: 4px; }
QListWidget::item:hover { background: #1E293B; }
QListWidget::item:selected { background: #1E3A8A; color: #F8FAFC; }
QTabWidget::pane { border: 1px solid #243045; border-radius: 8px; background: #111827; top: -1px; }
QTabBar::tab { padding: 8px 16px; color: #94A3B8; background: transparent; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #F8FAFC; border-bottom: 2px solid #3B82F6; font-weight: 600; }
QTabBar::tab:hover:!selected { color: #CBD5E1; }
QTableView, QTableWidget {
    background: #111827; alternate-background-color: #151E2E; gridline-color: #1F2937; border: none;
    selection-background-color: #1E3A8A; selection-color: #F8FAFC;
}
QHeaderView { background: #111827; }
QTableCornerButton::section { background: #1A2333; border: none; border-bottom: 1px solid #334155; }
QHeaderView::section {
    background: #1A2333; border: none; border-right: 1px solid #243045; border-bottom: 1px solid #334155;
    padding: 6px 6px; font-weight: 600; color: #CBD5E1;
}
QScrollBar:vertical { background: transparent; width: 11px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle { background: #334155; border-radius: 4px; }
QScrollBar::handle:vertical { min-height: 28px; }
QScrollBar::handle:horizontal { min-width: 28px; }
QScrollBar::handle:hover { background: #475569; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QPlainTextEdit#mono {
    font-family: Consolas, "Cascadia Mono", monospace; font-size: 9.5pt; background: #0B1120; border: none;
    selection-background-color: #1E3A8A;
}
QProgressBar { border: none; border-radius: 4px; background: #1F2937; max-height: 8px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #22D3EE); border-radius: 4px; }
QSplitter::handle { background: #1F2937; }
QSplitter::handle:hover { background: #3B82F6; }
QStatusBar { background: #111827; border-top: 1px solid #1F2937; color: #94A3B8; }
QToolTip { background: #1E293B; color: #F1F5F9; border: 1px solid #475569; padding: 4px 6px; }
QMessageBox, QDialog { background: #111827; }
QFrame#loadingOverlay { background: rgba(11, 17, 32, 210); border-radius: 8px; }
QWidget#sidebarHeader { background: #111827; border-right: 1px solid #1F2937; border-bottom: 1px solid #1F2937; }
QFrame#popup { background: #111827; border: 1px solid #475569; border-radius: 8px; }
QPushButton#primarySmall { background: #2563EB; color: #FFFFFF; border: none; font-weight: 600; padding: 5px 18px; }
QPushButton#primarySmall:hover { background: #3B82F6; }
QHeaderView#filterHeader::section { padding-right: 34px; }
QHeaderView#filterHeader::up-arrow, QHeaderView#filterHeader::down-arrow { image: none; width: 0px; height: 0px; }
"""


class RowsTableModel(QAbstractTableModel):
    """Read-only table over Dataset-JSON rows; Qt only asks for visible cells, so 100k+ rows stay fast."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._headers: list[str] = []
        self._tooltips: list[str] = []
        self._rows: list[list] = []
        self._original: list[list] = []
        self.foreground = None  # optional (row, column) -> QColor | None

    @property
    def rows(self) -> list[list]:
        return self._rows

    def set_table(self, headers: list[str], rows: list[list], tooltips: list[str] | None = None) -> None:
        self.beginResetModel()
        self._headers, self._tooltips = headers, tooltips or headers
        self._original, self._rows = rows, list(rows)
        self.endResetModel()

    def sort(self, column: int, order=Qt.AscendingOrder) -> None:
        """Sort by one column (blanks first, numbers numerically); column -1 restores file order."""
        self.layoutAboutToBeChanged.emit()
        if 0 <= column < len(self._headers):
            self._rows = sorted(self._original, key=lambda r: sort_key(r[column]), reverse=order == Qt.DescendingOrder)
        else:
            self._rows = list(self._original)
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt API)
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt API)
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            value = self._rows[index.row()][index.column()]
            return "" if value is None else str(value)
        if role == Qt.ForegroundRole and self.foreground:
            return self.foreground(self._rows[index.row()], index.column())
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802 (Qt API)
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._headers[section]
            if role == Qt.ToolTipRole:
                return self._tooltips[section]
        elif role == Qt.DisplayRole:
            return str(section + 1)
        return None


class MainWindow(QMainWindow):
    """Desktop UI for dsjson conversion (whole folder or a single XPT)."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("dsjson")
        self.setMinimumSize(1000, 640)
        self.resize(1360, 860)
        self.setStyleSheet(STYLE.replace("@CHEVRON@", CHEVRON))
        palette = self.palette()  # dark palette for what the stylesheet does not draw (checkboxes, menus)
        for role, color in (
            (QPalette.Window, "#0B1120"), (QPalette.WindowText, "#E2E8F0"), (QPalette.Base, "#0F172A"),
            (QPalette.AlternateBase, "#151E2E"), (QPalette.Text, "#E2E8F0"), (QPalette.Button, "#1E293B"),
            (QPalette.ButtonText, "#E2E8F0"), (QPalette.PlaceholderText, "#64748B"),
            (QPalette.Highlight, "#2563EB"), (QPalette.HighlightedText, "#FFFFFF"),
            (QPalette.ToolTipBase, "#1E293B"), (QPalette.ToolTipText, "#F1F5F9"),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)

        self.settings = QSettings("dsjson", "dsjson")
        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None
        self.results: list[dict] = []
        self.current_dataset_json: dict | None = None

        self._build_inputs()
        self._build_results()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar_panel)
        splitter.addWidget(self.results_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([410, 950])
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("Ready. Pick Define-XML, your SDTM data and an output folder.")
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.start_conversion)

        self._restore_settings()

    # ------------------------------------------------------------------
    # Layout: sidebar
    # ------------------------------------------------------------------
    def _build_inputs(self) -> None:
        self.define_input = QLineEdit()
        self.define_input.setPlaceholderText("define.xml")
        self.define_input.editingFinished.connect(self.refresh_dataset_list)

        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Folder with SDTM .xpt files")
        self.folder_input.editingFinished.connect(self.refresh_dataset_list)

        self.xpt_input = QLineEdit()
        self.xpt_input.setPlaceholderText("One .xpt file, e.g. dm.xpt")
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("e.g. DM")

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Folder for Dataset-JSON, reports and logs")

        # Data source: segmented control (folder = batch, single XPT)
        self.folder_mode_button = QPushButton("Whole folder")
        self.single_mode_button = QPushButton("Single XPT")
        self.mode_group = QButtonGroup(self)
        for i, button in enumerate((self.folder_mode_button, self.single_mode_button)):
            button.setObjectName("segment")
            button.setCheckable(True)
            self.mode_group.addButton(button, i)
        self.folder_mode_button.setChecked(True)

        self.data_stack = QStackedWidget()
        self.mode_group.idClicked.connect(self.data_stack.setCurrentIndex)

        self.dataset_list = QListWidget()
        self.dataset_list.setMinimumHeight(140)
        self.dataset_list.setMinimumWidth(200)  # wrapping list would otherwise demand one long row
        self.dataset_list.setFlow(QListWidget.LeftToRight)
        self.dataset_list.setWrapping(True)
        self.dataset_list.setResizeMode(QListWidget.Adjust)
        self.dataset_list.setGridSize(QSize(92, 28))  # even columns of dataset chips
        self.dataset_list.setAccessibleName("Datasets to convert")
        self.dataset_list.itemChanged.connect(self._update_selection_count)
        self.selection_count = QLabel("Pick a folder and Define-XML to list datasets")
        self.selection_count.setObjectName("muted")
        select_all = self._link_button("All", lambda: self._set_all_checked(True))
        select_none = self._link_button("None", lambda: self._set_all_checked(False))

        folder_page = QWidget()
        folder_layout = QVBoxLayout(folder_page)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.addLayout(self._picker_row(self.folder_input, self.browse_xpt_folder, "Browse folder"))
        count_row = QHBoxLayout()
        count_row.addWidget(self.selection_count, 1)
        count_row.addWidget(select_all)
        count_row.addWidget(select_none)
        folder_layout.addLayout(count_row)
        folder_layout.addWidget(self.dataset_list, 1)
        self.excluded_note = QLabel("")  # why some datasets are greyed out
        self.excluded_note.setObjectName("warning")
        self.excluded_note.setWordWrap(True)
        self.excluded_note.hide()
        folder_layout.addWidget(self.excluded_note)

        single_page = QWidget()
        single_layout = QVBoxLayout(single_page)
        single_layout.setContentsMargins(0, 0, 0, 0)
        single_layout.addLayout(self._picker_row(self.xpt_input, self.browse_xpt_file, "Browse file"))
        domain_row = QHBoxLayout()
        domain_row.addWidget(QLabel("Dataset name"))
        domain_row.addWidget(self.domain_input, 1)
        single_layout.addLayout(domain_row)
        single_layout.addStretch(1)

        self.data_stack.addWidget(folder_page)
        self.data_stack.addWidget(single_page)

        self.validate_checkbox = QCheckBox("Validate against Dataset-JSON v1.1 schema")
        self.validate_checkbox.setChecked(True)

        self.convert_button = QPushButton("Convert to Dataset-JSON")
        self.convert_button.setObjectName("primary")
        self.convert_button.setToolTip("Ctrl+Enter")
        self.convert_button.clicked.connect(self.start_conversion)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()

        self.open_folder_button = QPushButton("Open output folder")
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.clear_fields_button = QPushButton("Reset")
        self.clear_fields_button.clicked.connect(self.clear_fields)

        # Assemble
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 14, 20, 16)
        layout.setSpacing(12)

        layout.addWidget(self._card("1  Define-XML", self._picker_row(self.define_input, self.browse_define_file, "Browse")))

        segment_row = QHBoxLayout()
        segment_row.setSpacing(0)
        segment_row.addWidget(self.folder_mode_button)
        segment_row.addWidget(self.single_mode_button)
        data_body = QVBoxLayout()
        data_body.addLayout(segment_row)
        data_body.addWidget(self.data_stack, 1)
        layout.addWidget(self._card("2  SDTM data", data_body), 1)

        output_body = QVBoxLayout()
        output_body.addLayout(self._picker_row(self.output_input, self.browse_output_folder, "Browse"))
        output_body.addWidget(self.validate_checkbox)
        layout.addWidget(self._card("3  Output", output_body))

        layout.addWidget(self.convert_button)
        layout.addWidget(self.progress)
        secondary = QHBoxLayout()
        secondary.addWidget(self.open_folder_button, 1)
        secondary.addWidget(self.clear_fields_button)
        layout.addLayout(secondary)

        privacy = QLabel("Runs fully offline. No data leaves this computer.")
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setObjectName("sidebarScroll")
        self.sidebar_scroll.setWidget(sidebar)
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setMinimumWidth(390)  # fits path + Browse button at 100-150% scaling
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Heading stays put; only the steps below it scroll
        header = QWidget()
        header.setObjectName("sidebarHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 14)
        header_layout.setSpacing(2)
        title = QLabel("dsjson")
        title.setObjectName("appTitle")
        subtitle = QLabel("SDTM XPT + Define-XML to CDISC Dataset-JSON v1.1")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        self.sidebar_panel = QWidget()
        panel_layout = QVBoxLayout(self.sidebar_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        panel_layout.addWidget(header)
        panel_layout.addWidget(self.sidebar_scroll, 1)

    def _card(self, title: str, body) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("stepTitle")
        layout.addWidget(label)
        if isinstance(body, QWidget):
            layout.addWidget(body)
        else:
            layout.addLayout(body, 1)
        return card

    def _picker_row(self, line_edit: QLineEdit, callback, text: str) -> QHBoxLayout:
        row = QHBoxLayout()
        button = QPushButton(text)
        button.clicked.connect(callback)
        row.addWidget(line_edit, 1)
        row.addWidget(button)
        return row

    def _link_button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("link")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    # ------------------------------------------------------------------
    # Layout: results area
    # ------------------------------------------------------------------
    def _build_results(self) -> None:
        self.results_panel = QWidget()
        self.results_panel.setObjectName("results")
        layout = QVBoxLayout(self.results_panel)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        # Stat cards
        stats = QGridLayout()
        stats.setSpacing(10)
        self.stat_values: dict[str, QLabel] = {}
        for col, (key, caption) in enumerate(
            [("datasets", "Datasets"), ("passed", "Passed"), ("failed", "Failed"), ("records", "Records"), ("seconds", "Total time")]
        ):
            frame = QFrame()
            frame.setObjectName("stat")
            box = QVBoxLayout(frame)
            box.setContentsMargins(14, 10, 14, 10)
            value = QLabel("–")
            value.setObjectName("statValue")
            label = QLabel(caption)
            label.setObjectName("statCaption")
            box.addWidget(value)
            box.addWidget(label)
            self.stat_values[key] = value
            stats.addWidget(frame, 0, col)
        layout.addLayout(stats)

        # Dataset picker for Preview / Columns / Validation (hidden on Summary and Logs)
        self.dataset_bar = QWidget()
        picker = QHBoxLayout(self.dataset_bar)
        picker.setContentsMargins(0, 0, 0, 0)
        picker.addStretch(1)
        self.dataset_combo = QComboBox()
        self.dataset_combo.setMinimumWidth(200)
        self.dataset_combo.setAccessibleName("Dataset to inspect")
        self.dataset_combo.currentTextChanged.connect(self.load_dataset)
        self.open_json_button = QPushButton("Open JSON file")
        self.open_json_button.clicked.connect(self.open_current_json)
        self.open_json_button.setEnabled(False)
        picker.addWidget(QLabel("Dataset"))
        picker.addWidget(self.dataset_combo)
        picker.addWidget(self.open_json_button)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)

        # Summary
        self.summary_table = QTableWidget(0, len(SUMMARY_HEADERS))
        self.summary_table.setHorizontalHeaderLabels(SUMMARY_HEADERS)
        self._style_table(self.summary_table)
        self.summary_table.setSortingEnabled(True)
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.itemSelectionChanged.connect(self.on_summary_selection)
        self.summary_table.cellDoubleClicked.connect(lambda *_: self.tabs.setCurrentWidget(self.preview_page))
        self.summary_empty = QLabel("No results yet. Run a conversion to see one row per dataset here.")
        self.summary_empty.setObjectName("muted")
        self.summary_empty.setAlignment(Qt.AlignCenter)
        self.summary_stack = QStackedWidget()
        self.summary_stack.addWidget(self.summary_empty)
        self.summary_stack.addWidget(self.summary_table)

        # Preview (all rows): click a column name to sort, its funnel (or right-click) to filter
        self.preview_model, self.preview_proxy, self.preview_view = self._filter_table()
        self.preview_view.horizontalHeader().sortIndicatorChanged.connect(self._update_preview_info)
        self.filter_summary = QLabel("")  # active filters and sort, in words
        self.filter_summary.setTextFormat(Qt.RichText)
        self.filter_summary.setWordWrap(True)
        self.clear_filters_button = self._link_button("Clear filters", self.clear_preview_filters)
        self.clear_filters_button.hide()
        self.clear_sort_button = self._link_button("Clear sort", self.clear_preview_sort)
        self.clear_sort_button.hide()
        self.preview_info = QLabel("")
        self.preview_info.setObjectName("muted")
        self.preview_page = QWidget()
        preview_layout = QVBoxLayout(self.preview_page)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_summary, 1)
        filter_row.addWidget(self.clear_filters_button)
        filter_row.addWidget(self.clear_sort_button)
        filter_row.addWidget(self.preview_info)
        preview_layout.addLayout(filter_row)
        preview_layout.addWidget(self.preview_view, 1)

        # Columns metadata
        self.columns_table = QTableWidget(0, len(COLUMN_HEADERS))
        self.columns_table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self._style_table(self.columns_table)
        self.columns_table.horizontalHeader().setStretchLastSection(True)

        # Validation report + logs
        self.validation_status = QLabel("")
        self.validation_status.setObjectName("sectionTitle")
        self.validation_status.setTextFormat(Qt.RichText)
        self.open_report_button = self._link_button("Open report file", self.open_current_report)
        self.open_report_button.hide()
        self.validation_model, self.validation_proxy, self.validation_view = self._filter_table()
        self.validation_model.foreground = (
            lambda row, col: (FAIL_COLOR if row[0] == "Error" else WARN_COLOR) if col == 0 else None
        )
        self.validation_empty = QLabel("")
        self.validation_empty.setObjectName("muted")
        self.validation_empty.setAlignment(Qt.AlignCenter)
        self.validation_empty.setWordWrap(True)
        self.validation_stack = QStackedWidget()
        self.validation_stack.addWidget(self.validation_empty)
        self.validation_stack.addWidget(self.validation_view)
        validation_page = QWidget()
        validation_layout = QVBoxLayout(validation_page)
        validation_layout.setContentsMargins(8, 8, 8, 8)
        status_row = QHBoxLayout()
        status_row.addWidget(self.validation_status, 1)
        status_row.addWidget(self.open_report_button)
        validation_layout.addLayout(status_row)
        validation_layout.addWidget(self.validation_stack, 1)
        self.report_path: Path | None = None

        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("mono")
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(20000)
        clear_logs = self._link_button("Clear logs", self.log_output.clear)
        logs_page = QWidget()
        logs_layout = QVBoxLayout(logs_page)
        logs_layout.setContentsMargins(8, 8, 8, 8)
        logs_top = QHBoxLayout()
        logs_top.addStretch(1)
        logs_top.addWidget(clear_logs)
        logs_layout.addLayout(logs_top)
        logs_layout.addWidget(self.log_output, 1)

        self.tabs.addTab(self.summary_stack, "Summary")
        self.tabs.addTab(self.preview_page, "Data preview")
        self.tabs.addTab(self.columns_table, "Columns")
        self.tabs.addTab(validation_page, "Validation report")
        self.tabs.addTab(logs_page, "Logs")
        self.dataset_pages = (self.preview_page, self.columns_table, validation_page)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._on_tab_changed(self.tabs.currentIndex())
        policy = self.dataset_bar.sizePolicy()
        policy.setRetainSizeWhenHidden(True)  # tabs do not jump when the picker hides
        self.dataset_bar.setSizePolicy(policy)
        layout.addWidget(self.dataset_bar)
        layout.addWidget(self.tabs, 1)

        # "Loading <dataset>" card shown over the tabs while a large dataset is read
        self.loading_overlay = QFrame(self.tabs)
        self.loading_overlay.setObjectName("loadingOverlay")
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 24, 36, 24)
        self.loading_title = QLabel("")
        self.loading_title.setObjectName("sectionTitle")
        self.loading_title.setAlignment(Qt.AlignCenter)
        self.loading_detail = QLabel("")
        self.loading_detail.setObjectName("muted")
        self.loading_detail.setAlignment(Qt.AlignCenter)
        loading_bar = QProgressBar()
        loading_bar.setRange(0, 0)  # busy indicator
        loading_bar.setTextVisible(False)
        loading_bar.setFixedWidth(220)
        card_layout.addWidget(self.loading_title)
        card_layout.addWidget(self.loading_detail)
        card_layout.addWidget(loading_bar, 0, Qt.AlignCenter)
        overlay_layout.addWidget(card)
        self.loading_overlay.hide()

    def _on_tab_changed(self, index: int) -> None:
        self.dataset_bar.setVisible(self.tabs.widget(index) in self.dataset_pages)

    def _filter_table(self):
        """Read-only table with Excel-style header: click to sort, funnel or right-click to filter."""
        model = RowsTableModel(self)
        proxy = RowsFilterProxy(self)
        proxy.setSourceModel(model)
        view = QTableView()
        header = FilterHeader(view)
        view.setHorizontalHeader(header)
        view.setModel(proxy)
        self._style_table(view)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        header.setToolTip("Click a column name to sort. Click the funnel or right-click to filter.")
        header.setSortIndicator(-1, Qt.AscendingOrder)
        header.setSortIndicatorClearable(True)  # click: ascending, descending, then file order again
        header.setResizeContentsPrecision(200)  # fit widths on 200 rows, not 1000: 5x faster on big data
        view.setSortingEnabled(True)
        header.filter_requested.connect(lambda col, pos: self.open_column_filter(view, col, pos))
        return model, proxy, view

    @staticmethod
    def _style_table(table) -> None:
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.verticalHeader().setDefaultSectionSize(26)
        table.setWordWrap(False)

    # ------------------------------------------------------------------
    # Pickers
    # ------------------------------------------------------------------
    def browse_define_file(self) -> None:
        with self._blurred():
            path, _ = QFileDialog.getOpenFileName(self, "Select Define-XML", self._start_dir(self.define_input), "XML Files (*.xml);;All Files (*.*)")
        if path:
            self.define_input.setText(path)
            self.refresh_dataset_list()

    def browse_xpt_folder(self) -> None:
        with self._blurred():
            path = QFileDialog.getExistingDirectory(self, "Select XPT Folder", self._start_dir(self.folder_input))
        if path:
            self.folder_input.setText(path)
            self.refresh_dataset_list()

    def browse_xpt_file(self) -> None:
        with self._blurred():
            path, _ = QFileDialog.getOpenFileName(self, "Select XPT File", self._start_dir(self.xpt_input), "XPT Files (*.xpt);;All Files (*.*)")
        if path:
            self.xpt_input.setText(path)
            self.domain_input.setText(Path(path).stem.upper())

    def browse_output_folder(self) -> None:
        with self._blurred():
            path = QFileDialog.getExistingDirectory(self, "Select Output Folder", self._start_dir(self.output_input))
        if path:
            self.output_input.setText(path)

    @staticmethod
    def _start_dir(field: QLineEdit) -> str:
        text = field.text().strip()
        return str(Path(text).parent if Path(text).suffix else Path(text)) if text else ""

    def refresh_dataset_list(self) -> None:
        """List XPT datasets of the folder; those described in Define-XML are ticked."""
        self.dataset_list.clear()
        folder = self.folder_input.text().strip()
        define = self.define_input.text().strip()

        self.excluded_note.hide()
        if not folder or not Path(folder).is_dir():
            self.selection_count.setText("Pick a folder and Define-XML to list datasets")
            return

        define_names = None
        if define and Path(define).exists():
            try:
                parser = DefineXMLParser(define)
                parser.parse()
                define_names = set(parser.get_dataset_names())
            except Exception as exc:
                self.append_log(f"Could not read Define-XML: {exc}")
                self.statusBar().showMessage("Could not read Define-XML. See Logs.")

        self.dataset_list.blockSignals(True)
        for name in sorted(p.stem.upper() for p in Path(folder).glob("*.xpt")):
            item = QListWidgetItem(name)
            in_define = define_names is None or name in define_names
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if in_define else Qt.Unchecked)
            if not in_define:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setToolTip("Not described in Define-XML")
            self.dataset_list.addItem(item)
        self.dataset_list.blockSignals(False)
        self._update_selection_count()

        missing = [] if define_names is None else sorted(
            self.dataset_list.item(i).text() for i in range(self.dataset_list.count())
            if self.dataset_list.item(i).text() not in define_names
        )
        if missing:
            names = ", ".join(missing[:8]) + (f" and {len(missing) - 8} more" if len(missing) > 8 else "")
            verb = "is" if len(missing) == 1 else "are"
            self.excluded_note.setText(
                f"{names} {verb} not in the selected Define-XML, so {'it' if len(missing) == 1 else 'they'} "
                "cannot be converted. Check that step 1 and step 2 are the same study."
            )
        self.excluded_note.setVisible(bool(missing))

    def _set_all_checked(self, checked: bool) -> None:
        self.dataset_list.blockSignals(True)
        for i in range(self.dataset_list.count()):
            item = self.dataset_list.item(i)
            if item.flags() & Qt.ItemIsEnabled:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.dataset_list.blockSignals(False)
        self._update_selection_count()

    def _update_selection_count(self, *_) -> None:
        total = self.dataset_list.count()
        if total == 0:
            self.selection_count.setText("No .xpt files found in this folder" if self.folder_input.text().strip() else "")
            return
        self.selection_count.setText(f"{len(self._checked_datasets())} of {total} datasets selected")

    def _checked_datasets(self) -> list[str]:
        return [
            self.dataset_list.item(i).text()
            for i in range(self.dataset_list.count())
            if self.dataset_list.item(i).checkState() == Qt.Checked
        ]

    def _batch_mode(self) -> bool:
        return self.folder_mode_button.isChecked()

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    def start_conversion(self) -> None:
        if self.worker_thread is not None:
            return  # already running

        define_path = self.define_input.text().strip()
        output_dir = self.output_input.text().strip()
        batch = self._batch_mode()
        datasets = self._checked_datasets() if batch else None
        domain = self.domain_input.text().strip().upper()
        xpt_path = self.xpt_input.text().strip()

        problem = None
        if not define_path:
            problem = ("Define-XML missing", "Choose the study's define.xml in step 1.", self.define_input)
        elif batch and not self.folder_input.text().strip():
            problem = ("Folder missing", "Choose the folder with your .xpt files in step 2.", self.folder_input)
        elif batch and not datasets:
            problem = ("No datasets selected", "Tick at least one dataset in step 2.", self.dataset_list)
        elif not batch and not xpt_path:
            problem = ("XPT file missing", "Choose an .xpt file in step 2.", self.xpt_input)
        elif not batch and not domain:
            problem = ("Dataset name missing", "Enter the dataset name, for example DM.", self.domain_input)
        elif not output_dir:
            problem = ("Output folder missing", "Choose where to write the results in step 3.", self.output_input)
        if problem:
            with self._blurred():
                QMessageBox.warning(self, problem[0], problem[1])
            problem[2].setFocus()
            return

        self._save_settings()
        self.results = []
        self.summary_table.setRowCount(0)
        self.summary_stack.setCurrentWidget(self.summary_empty)
        self.dataset_combo.clear()
        self._set_stats(None)

        self.total_jobs = len(datasets) if batch else 1
        self.done_jobs = 0
        self.progress.setRange(0, self.total_jobs)
        self.progress.setValue(0)
        self.progress.show()
        self.convert_button.setEnabled(False)
        self.convert_button.setText("Converting…")
        self.append_log(f"--- Converting {self.total_jobs} dataset(s) ---")
        self.tabs.setCurrentIndex(4)

        self.worker_thread = QThread()
        self.worker = ConversionWorker(
            define_path=define_path,
            output_dir=output_dir,
            domain=domain,
            xpt_path=xpt_path,
            data_dir=self.folder_input.text().strip() if batch else "",
            datasets=datasets,
            validate=self.validate_checkbox.isChecked(),
            log_level="INFO",
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self.append_log)
        self.worker.results_ready.connect(self.show_summary)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._clear_thread)

        self.worker_thread.start()

    def _clear_thread(self) -> None:
        self.worker_thread = None
        self.worker = None

    def show_summary(self, results: list) -> None:
        """One row per dataset in the Summary tab, plus stat cards and the dataset picker."""
        self.results = results
        report_dir = Path(self.output_input.text().strip()) / "validation_report"
        self.summary_table.setSortingEnabled(False)
        self.summary_table.setRowCount(len(results))
        bold = QFont()
        bold.setBold(True)
        for row, result in enumerate(results):
            for col, key in enumerate(SUMMARY_KEYS):
                value = self._details(result, report_dir) if key == "message" else result.get(key, "")
                item = QTableWidgetItem()
                if isinstance(value, (int, float)):
                    item.setData(Qt.DisplayRole, value)  # numeric sort
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setText("" if value is None else str(value))
                if key == "status":
                    item.setFont(bold)
                    item.setForeground(QBrush(PASS_COLOR if value == "PASS" else FAIL_COLOR if value == "FAIL" else MUTED_COLOR))
                if key == "warnings" and value:
                    item.setToolTip("Data does not fit the Define-XML type. See the Validation report tab.")
                if key == "message":
                    item.setToolTip(value)
                self.summary_table.setItem(row, col, item)
        self.summary_table.setSortingEnabled(True)
        self.summary_table.sortByColumn(0, Qt.AscendingOrder)
        self.summary_table.resizeColumnsToContents()
        self.summary_stack.setCurrentWidget(self.summary_table if results else self.summary_empty)
        self._set_stats(results)

        output_dir = Path(self.output_input.text().strip())
        self.dataset_combo.blockSignals(True)
        self.dataset_combo.clear()
        self.dataset_combo.addItems([r["dataset"] for r in results if (output_dir / f"{r['dataset']}.json").exists()])
        self.dataset_combo.setCurrentIndex(-1)
        self.dataset_combo.blockSignals(False)

    @staticmethod
    def _details(result: dict, report_dir: Path) -> str:
        """Failure reason, or what the warnings are (grouped); blank when there is nothing to say."""
        if result.get("message"):
            return result["message"]
        path = report_dir / f"{result['dataset']}_validation.json"
        if not result.get("warnings") or not path.exists():
            return ""
        report = json.loads(path.read_text(encoding="utf-8"))
        counts = Counter(
            w.get("message", "") if isinstance(w, dict) else str(w)
            for part in ("metadata", "rows")
            for w in report.get(part, {}).get("warnings", [])
        )
        parts = []
        for message, n in counts.most_common():
            m = re.fullmatch(r"Value for (\S+) expected (\w+) but got (\w+)", message)
            parts.append(
                f"{m.group(1)}: Define-XML says {m.group(2)}, {n:,} value(s) are {m.group(3)}" if m
                else f"{message} ({n:,}x)" if n > 1 else message
            )
        return "; ".join(parts)

    def _set_stats(self, results: list | None) -> None:
        if not results:
            for label in self.stat_values.values():
                label.setText("–")
            return
        done = [r for r in results if r["status"] != "SKIPPED"]
        self.stat_values["datasets"].setText(str(len(done)))
        self.stat_values["passed"].setText(str(sum(r["status"] == "PASS" for r in done)))
        self.stat_values["failed"].setText(str(sum(r["status"] == "FAIL" for r in done)))
        self.stat_values["records"].setText(f"{sum(r.get('records') or 0 for r in done):,}")
        self.stat_values["seconds"].setText(f"{sum(r.get('seconds') or 0 for r in done):.1f} s")

    def on_conversion_finished(self, success: bool, message: str) -> None:
        self.convert_button.setEnabled(True)
        self.convert_button.setText("Convert to Dataset-JSON")
        self.progress.hide()
        self.append_log(message)
        self.statusBar().showMessage(message)

        self.tabs.setCurrentIndex(0)
        if self.summary_table.rowCount():
            self.summary_table.selectRow(0)
        if not success:
            with self._blurred():
                QMessageBox.warning(self, "Finished with problems", message + "\n\nSee the Summary and Logs tabs.")

    def on_summary_selection(self) -> None:
        rows = self.summary_table.selectionModel().selectedRows()
        if rows:
            dataset = self.summary_table.item(rows[0].row(), 0).text()
            index = self.dataset_combo.findText(dataset)
            if index >= 0:
                self.dataset_combo.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Inspect one dataset
    # ------------------------------------------------------------------
    def load_dataset(self, dataset: str) -> None:
        """Fill Preview, Columns and Validation tabs for one dataset."""
        output_dir = Path(self.output_input.text().strip())
        json_path = output_dir / f"{dataset}.json"
        self.open_json_button.setEnabled(bool(dataset) and json_path.exists())
        if not dataset or not json_path.exists():
            return

        records = next((r.get("records") for r in self.results if r.get("dataset") == dataset), None)
        self.loading_title.setText(f"Loading {dataset}")
        self.loading_detail.setText(f"{records:,} records" if records else "")
        self.loading_overlay.setGeometry(self.tabs.rect())
        self.loading_overlay.raise_()
        self.loading_overlay.show()
        self.setCursor(Qt.WaitCursor)
        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)  # paint the overlay before the work starts
        try:
            self.show_dataset_json(json.loads(json_path.read_text(encoding="utf-8")))
            self._show_validation(output_dir / "validation_report" / f"{dataset}_validation.json")
        except Exception as exc:
            with self._blurred():
                QMessageBox.critical(self, "Unable to open Dataset-JSON", f"{json_path}\n\n{exc}")
        finally:
            self.loading_overlay.hide()
            self.unsetCursor()

    def show_dataset_json(self, dataset_json: dict) -> None:
        self.current_dataset_json = dataset_json
        columns = dataset_json.get("columns", [])
        rows = dataset_json.get("rows", [])

        headers = [c.get("name", "") for c in columns]
        tooltips = [f"{c.get('name', '')}: {c.get('label', '')}\nType: {c.get('dataType', '')}" for c in columns]
        header = self.preview_view.horizontalHeader()
        self.preview_proxy.clear_filters()
        header.filtered.clear()
        header.setSortIndicator(-1, Qt.AscendingOrder)
        self.preview_model.set_table(headers, rows, tooltips)
        self.preview_view.resizeColumnsToContents()
        self._update_preview_info()

        self.columns_table.setSortingEnabled(False)
        self.columns_table.setRowCount(len(columns))
        for r, c in enumerate(columns):
            values = [r + 1, c.get("name"), c.get("label"), c.get("dataType"), c.get("length"), c.get("keySequence"), c.get("itemOID")]
            for col, value in enumerate(values):
                item = QTableWidgetItem()
                if isinstance(value, int):
                    item.setData(Qt.DisplayRole, value)  # numeric sort
                else:
                    item.setText("" if value is None else str(value))
                self.columns_table.setItem(r, col, item)
        self.columns_table.resizeColumnsToContents()

        self.statusBar().showMessage(
            f"{dataset_json.get('name')} – {dataset_json.get('label')}: {len(rows):,} records, {len(columns)} columns"
        )

    def _show_validation(self, report_path: Path) -> None:
        """Errors and warnings of the selected dataset as a sortable, filterable table."""
        self.validation_proxy.clear_filters()
        self.validation_view.horizontalHeader().filtered.clear()
        self.report_path = report_path if report_path.exists() else None
        self.open_report_button.setVisible(self.report_path is not None)
        if self.report_path is None:
            self.validation_model.set_table(VALIDATION_HEADERS, [])
            self.validation_status.setText("No validation report")
            self.validation_empty.setText(
                "Validation was switched off for this run. Tick the option in step 3 and convert again."
            )
            self.validation_stack.setCurrentWidget(self.validation_empty)
            return

        report = json.loads(report_path.read_text(encoding="utf-8"))
        issues: list[list] = []
        for part, check in (("metadata", "Metadata (schema)"), ("rows", "Rows")):
            section = report.get(part, {})
            for severity, key in (("Error", "errors"), ("Warning", "warnings")):
                for issue in section.get(key, []):
                    if isinstance(issue, dict):
                        issues.append([severity, check, str(issue.get("path") or ""), issue.get("message", "")])
                    else:
                        issues.append([severity, check, "", str(issue)])
        self.validation_model.set_table(VALIDATION_HEADERS, issues)

        summary = report.get("summary", {})
        passed = report.get("status") == "PASS"
        status, color = ("PASS", PASS_COLOR) if passed else ("FAIL", FAIL_COLOR)
        self.validation_status.setText(
            f"<span style='color:{color.name()}'>{status}</span> &nbsp; "
            f"{summary.get('errors', 0)} errors, {summary.get('warnings', 0)} warnings"
        )
        if issues:
            self.validation_view.resizeColumnsToContents()
            self.validation_stack.setCurrentWidget(self.validation_view)
        else:
            self.validation_empty.setText("No errors or warnings. Matches the Dataset-JSON v1.1 schema and Define-XML.")
            self.validation_stack.setCurrentWidget(self.validation_empty)

    def open_current_report(self) -> None:
        if self.report_path and self.report_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.report_path)))

    # ------------------------------------------------------------------
    # Excel-style sort and filter
    # ------------------------------------------------------------------
    def open_column_filter(self, view: QTableView, column: int, pos) -> None:
        """Value list for one column, opened from the header funnel or a right-click."""
        proxy = view.model()
        self.setCursor(Qt.WaitCursor)
        try:
            values = proxy.distinct_values(column)
        finally:
            self.unsetCursor()
        name = proxy.sourceModel().headerData(column, Qt.Horizontal)
        popup = ColumnFilterPopup(name, values, proxy.column_filters.get(column), self)
        popup.applied.connect(lambda chosen: self._apply_column_filter(view, column, chosen))
        popup.sort_requested.connect(lambda order: self._sort_view(view, column, order))
        popup.adjustSize()
        screen = self.screen().availableGeometry()
        popup.move(min(pos.x(), screen.right() - popup.width()), min(pos.y(), screen.bottom() - popup.height()))
        self._set_blur(True)
        popup.closed.connect(lambda: self._set_blur(False))
        popup.show()

    @staticmethod
    def _sort_view(view: QTableView, column: int, order) -> None:
        """order None clears the sort (file order)."""
        if order is None:
            view.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        else:
            view.sortByColumn(column, order)

    def _apply_column_filter(self, view: QTableView, column: int, chosen) -> None:
        proxy = view.model()
        self.setCursor(Qt.WaitCursor)
        try:
            proxy.set_column_filter(column, chosen)
        finally:
            self.unsetCursor()
        view.horizontalHeader().filtered = set(proxy.column_filters)
        view.horizontalHeader().viewport().update()
        self._update_preview_info()

    def clear_preview_filters(self) -> None:
        self.preview_proxy.clear_filters()
        self.preview_view.horizontalHeader().filtered.clear()
        self.preview_view.horizontalHeader().viewport().update()
        self._update_preview_info()

    def clear_preview_sort(self) -> None:
        self._sort_view(self.preview_view, -1, None)

    def _update_preview_info(self, *_) -> None:
        """Bar above the preview: active filters and sort in words, with links to clear them."""
        proxy, model = self.preview_proxy, self.preview_model
        header = self.preview_view.horizontalHeader()
        shown, total = proxy.rowCount(), model.rowCount()

        parts = []
        for column, allowed in sorted(proxy.column_filters.items()):
            name = model.headerData(column, Qt.Horizontal)
            values = sorted(v or BLANK_LABEL for v in allowed)
            listed = ", ".join(values[:3]) + (f" +{len(values) - 3} more" if len(values) > 3 else "")
            parts.append(f"<b>{html.escape(name)}</b> = {html.escape(listed)}")
        sorted_by = header.sortIndicatorSection()
        is_sorted = 0 <= sorted_by < model.columnCount()
        if is_sorted:
            direction = "ascending" if header.sortIndicatorOrder() == Qt.AscendingOrder else "descending"
            parts.append(f"sorted by <b>{html.escape(model.headerData(sorted_by, Qt.Horizontal))}</b> ({direction})")

        if parts:
            self.filter_summary.setText(" &nbsp;·&nbsp; ".join(parts))
        elif total:
            self.filter_summary.setText("Click a column name to sort. Click its funnel or right-click it to filter.")
        else:
            self.filter_summary.setText("")
        self.clear_filters_button.setVisible(bool(proxy.column_filters))
        self.clear_sort_button.setVisible(is_sorted)
        self.preview_info.setText(f"{shown:,} of {total:,} rows" if proxy.column_filters else f"{total:,} rows" if total else "")

    # ------------------------------------------------------------------
    # Background blur behind popups and dialogs
    # ------------------------------------------------------------------
    def _set_blur(self, on: bool) -> None:
        if on:
            effect = QGraphicsBlurEffect(self)
            effect.setBlurRadius(5)
            effect.setBlurHints(QGraphicsBlurEffect.PerformanceHint)
            self.centralWidget().setGraphicsEffect(effect)
        else:
            self.centralWidget().setGraphicsEffect(None)

    @contextmanager
    def _blurred(self):
        self._set_blur(True)
        try:
            yield
        finally:
            self._set_blur(False)

    def open_current_json(self) -> None:
        dataset = self.dataset_combo.currentText()
        if dataset:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.output_input.text().strip()) / f"{dataset}.json")))

    def open_output_folder(self) -> None:
        folder = self.output_input.text().strip()
        if folder and Path(folder).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            with self._blurred():
                QMessageBox.information(self, "No output folder", "Choose an existing output folder in step 3 first.")

    # ------------------------------------------------------------------
    # Logs, settings, reset
    # ------------------------------------------------------------------
    def append_log(self, message: str) -> None:
        """Add a log line (warnings amber, errors red) and drive the progress bar."""
        color = (FAIL_COLOR if ("ERROR" in message or "failed" in message.lower())
                 else WARN_COLOR if "WARNING" in message else TEXT_COLOR).name()
        self.log_output.appendHtml(f"<span style='color:{color}; white-space:pre'>{html.escape(message)}</span>")

        started = re.search(r"\[(\w+)\] START", message)
        if started and self.progress.isVisible():
            self.statusBar().showMessage(f"Converting {started.group(1)} ({self.done_jobs + 1} of {self.total_jobs})…")
        if self.progress.isVisible() and re.search(r"\] (DONE \||Conversion failed)", message):
            self.done_jobs += 1
            self.progress.setValue(self.done_jobs)

    def _save_settings(self) -> None:
        for key, field in self._fields().items():
            self.settings.setValue(key, field.text())
        self.settings.setValue("batch_mode", self._batch_mode())

    def _restore_settings(self) -> None:
        for key, field in self._fields().items():
            field.setText(self.settings.value(key, "", type=str))
        if not self.settings.value("batch_mode", True, type=bool):
            self.single_mode_button.setChecked(True)
            self.data_stack.setCurrentIndex(1)
        self.refresh_dataset_list()

    def _fields(self) -> dict[str, QLineEdit]:
        return {
            "define": self.define_input,
            "folder": self.folder_input,
            "xpt": self.xpt_input,
            "domain": self.domain_input,
            "output": self.output_input,
        }

    def clear_fields(self) -> None:
        for field in self._fields().values():
            field.clear()
        self.dataset_list.clear()
        self._update_selection_count()
        self.results = []
        self.summary_table.setRowCount(0)
        self.summary_stack.setCurrentWidget(self.summary_empty)
        self.dataset_combo.clear()
        self.preview_model.set_table([], [])
        self.preview_proxy.clear_filters()
        self._update_preview_info()
        self.columns_table.setRowCount(0)
        self.validation_model.set_table([], [])
        self.validation_status.clear()
        self.open_report_button.hide()
        self.log_output.clear()
        self._set_stats(None)
        self._save_settings()
        self.statusBar().showMessage("Reset.")
