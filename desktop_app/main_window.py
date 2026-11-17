"""Main window for the dsjson desktop application.

Layout: input sidebar (left) | results area (right), split by a draggable splitter.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSettings,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QUrl,
)
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
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
from desktop_app.worker import ConversionWorker

SUMMARY_HEADERS = ["Dataset", "Status", "Records", "Columns", "Errors", "Warnings", "Time (s)", "Message"]
SUMMARY_KEYS = ["dataset", "status", "records", "columns", "errors", "warnings", "seconds", "message"]
COLUMN_HEADERS = ["#", "Name", "Label", "Data type", "Length", "Key seq.", "Item OID"]

PASS_COLOR = QColor("#15803D")
FAIL_COLOR = QColor("#B91C1C")
MUTED_COLOR = QColor("#64748B")

# One place for the look: navy primary on light slate, 4.5:1+ text contrast
STYLE = """
QMainWindow, QWidget#results { background: #F8FAFC; }
QWidget { color: #0F172A; }
QWidget#sidebar { background: #FFFFFF; }
QScrollArea#sidebarScroll { border: none; border-right: 1px solid #CBD5E1; background: #FFFFFF; }
QLabel#appTitle { font-size: 17pt; font-weight: 600; color: #1E3A8A; }
QLabel#muted { color: #475569; }
QLabel#stepTitle { font-size: 10.5pt; font-weight: 600; color: #1E3A8A; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 600; color: #1E3A8A; }
QFrame#card, QFrame#stat { background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; }
QLabel#statValue { font-size: 17pt; font-weight: 600; color: #1E3A8A; }
QLabel#statCaption { color: #475569; }
QLineEdit, QComboBox {
    background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 5px 8px; min-height: 20px;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid #1E40AF; }
QPushButton {
    background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 5px 12px; min-height: 22px;
}
QPushButton:hover { background: #E9EEF6; }
QPushButton:focus { border: 2px solid #1E40AF; }
QPushButton:disabled { color: #94A3B8; background: #F1F5F9; }
QPushButton#primary {
    background: #1E40AF; color: #FFFFFF; border: none; font-size: 11pt; font-weight: 600; padding: 9px; min-height: 26px;
}
QPushButton#primary:hover { background: #1E3A8A; }
QPushButton#primary:focus { border: 2px solid #F59E0B; }
QPushButton#primary:disabled { background: #94A3B8; }
QPushButton#segment { border-radius: 0; padding: 6px 10px; }
QPushButton#segment:checked { background: #1E40AF; color: #FFFFFF; border-color: #1E40AF; font-weight: 600; }
QPushButton#link { border: none; background: transparent; color: #1E40AF; padding: 2px 4px; min-height: 16px; }
QPushButton#link:hover { text-decoration: underline; }
QListWidget { border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; }
QTabWidget::pane { border: 1px solid #CBD5E1; border-radius: 6px; background: #FFFFFF; top: -1px; }
QTabBar::tab { padding: 8px 16px; color: #475569; background: transparent; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #1E40AF; border-bottom: 2px solid #1E40AF; font-weight: 600; }
QTabBar::tab:hover { color: #1E3A8A; }
QTableView, QTableWidget {
    background: #FFFFFF; alternate-background-color: #F8FAFC; gridline-color: #E2E8F0; border: none;
    selection-background-color: #DBEAFE; selection-color: #0F172A;
}
QHeaderView { background: #FFFFFF; }
QTableCornerButton::section { background: #F1F5F9; border: none; border-bottom: 1px solid #CBD5E1; }
QScrollBar { background: #F1F5F9; }
QHeaderView::section {
    background: #F1F5F9; border: none; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #CBD5E1;
    padding: 5px 6px; font-weight: 600; color: #334155;
}
QPlainTextEdit#mono { font-family: Consolas, "Cascadia Mono", monospace; font-size: 9.5pt; background: #FFFFFF; border: none; }
QProgressBar { border: 1px solid #CBD5E1; border-radius: 5px; background: #F1F5F9; max-height: 10px; }
QProgressBar::chunk { background: #1E40AF; border-radius: 4px; }
QSplitter::handle { background: #E2E8F0; }
QStatusBar { background: #FFFFFF; border-top: 1px solid #CBD5E1; color: #475569; }
"""


class RowsTableModel(QAbstractTableModel):
    """Read-only table over Dataset-JSON rows; Qt only asks for visible cells, so 100k+ rows stay fast."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._headers: list[str] = []
        self._tooltips: list[str] = []
        self._rows: list[list] = []

    def set_table(self, headers: list[str], rows: list[list], tooltips: list[str] | None = None) -> None:
        self.beginResetModel()
        self._headers, self._rows, self._tooltips = headers, rows, tooltips or headers
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt API)
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802 (Qt API)
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            value = self._rows[index.row()][index.column()]
            return "" if value is None else str(value)
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

        self.setWindowTitle("DSJSON Converter")
        self.setMinimumSize(1000, 640)
        self.resize(1360, 860)
        self.setStyleSheet(STYLE)
        palette = self.palette()  # checkbox / selection accent = primary, not the Windows accent
        palette.setColor(QPalette.Highlight, QColor("#1E40AF"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        self.setPalette(palette)

        self.settings = QSettings("dsjson", "DSJSON Converter")
        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None
        self.results: list[dict] = []
        self.current_dataset_json: dict | None = None

        self._build_inputs()
        self._build_results()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar_scroll)
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
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel("DSJSON Converter")
        title.setObjectName("appTitle")
        subtitle = QLabel("SDTM XPT + Define-XML to CDISC Dataset-JSON v1.1")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

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

        # Dataset picker shared by Preview / Columns / Validation
        picker = QHBoxLayout()
        title = QLabel("Results")
        title.setObjectName("sectionTitle")
        self.dataset_combo = QComboBox()
        self.dataset_combo.setMinimumWidth(200)
        self.dataset_combo.setAccessibleName("Dataset to inspect")
        self.dataset_combo.currentTextChanged.connect(self.load_dataset)
        self.open_json_button = QPushButton("Open JSON file")
        self.open_json_button.clicked.connect(self.open_current_json)
        self.open_json_button.setEnabled(False)
        picker.addWidget(title)
        picker.addStretch(1)
        picker.addWidget(QLabel("Dataset"))
        picker.addWidget(self.dataset_combo)
        picker.addWidget(self.open_json_button)
        layout.addLayout(picker)

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

        # Preview (all rows, filterable)
        self.preview_model = RowsTableModel(self)
        self.preview_proxy = QSortFilterProxyModel(self)
        self.preview_proxy.setSourceModel(self.preview_model)
        self.preview_proxy.setFilterKeyColumn(-1)
        self.preview_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.preview_view = QTableView()
        self.preview_view.setModel(self.preview_proxy)
        self._style_table(self.preview_view)
        self.preview_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.preview_filter = QLineEdit()
        self.preview_filter.setPlaceholderText("Filter rows (press Enter), e.g. 01-701-1015")
        self.preview_filter.setClearButtonEnabled(True)
        self.preview_filter.returnPressed.connect(self.apply_preview_filter)
        self.preview_filter.textChanged.connect(lambda t: t or self.apply_preview_filter())
        self.preview_info = QLabel("")
        self.preview_info.setObjectName("muted")
        self.preview_page = QWidget()
        preview_layout = QVBoxLayout(self.preview_page)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.preview_filter, 1)
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
        self.validation_output = QPlainTextEdit()
        self.validation_output.setObjectName("mono")
        self.validation_output.setReadOnly(True)
        validation_page = QWidget()
        validation_layout = QVBoxLayout(validation_page)
        validation_layout.setContentsMargins(8, 8, 8, 8)
        validation_layout.addWidget(self.validation_status)
        validation_layout.addWidget(self.validation_output, 1)

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
        layout.addWidget(self.tabs, 1)

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
        path, _ = QFileDialog.getOpenFileName(self, "Select Define-XML", self._start_dir(self.define_input), "XML Files (*.xml);;All Files (*.*)")
        if path:
            self.define_input.setText(path)
            self.refresh_dataset_list()

    def browse_xpt_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select XPT Folder", self._start_dir(self.folder_input))
        if path:
            self.folder_input.setText(path)
            self.refresh_dataset_list()

    def browse_xpt_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select XPT File", self._start_dir(self.xpt_input), "XPT Files (*.xpt);;All Files (*.*)")
        if path:
            self.xpt_input.setText(path)
            self.domain_input.setText(Path(path).stem.upper())

    def browse_output_folder(self) -> None:
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
        self.summary_table.setSortingEnabled(False)
        self.summary_table.setRowCount(len(results))
        bold = QFont()
        bold.setBold(True)
        for row, result in enumerate(results):
            for col, key in enumerate(SUMMARY_KEYS):
                value = result.get(key, "")
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

        self.setCursor(Qt.WaitCursor)
        try:
            dataset_json = json.loads(json_path.read_text(encoding="utf-8"))
            self.show_dataset_json(dataset_json)
            report_path = output_dir / "validation_report" / f"{dataset}_validation.json"
            self._show_validation(report_path)
        except Exception as exc:
            QMessageBox.critical(self, "Unable to open Dataset-JSON", f"{json_path}\n\n{exc}")
        finally:
            self.unsetCursor()

    def show_dataset_json(self, dataset_json: dict) -> None:
        self.current_dataset_json = dataset_json
        columns = dataset_json.get("columns", [])
        rows = dataset_json.get("rows", [])

        headers = [c.get("name", "") for c in columns]
        tooltips = [f"{c.get('name', '')}: {c.get('label', '')}\nType: {c.get('dataType', '')}" for c in columns]
        self.preview_filter.clear()
        self.preview_model.set_table(headers, rows, tooltips)
        self.preview_view.resizeColumnsToContents()
        self._update_preview_info()

        self.columns_table.setRowCount(len(columns))
        for r, c in enumerate(columns):
            values = [r + 1, c.get("name"), c.get("label"), c.get("dataType"), c.get("length"), c.get("keySequence"), c.get("itemOID")]
            for col, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                self.columns_table.setItem(r, col, item)
        self.columns_table.resizeColumnsToContents()

        self.statusBar().showMessage(
            f"{dataset_json.get('name')} – {dataset_json.get('label')}: {len(rows):,} records, {len(columns)} columns"
        )

    def _show_validation(self, report_path: Path) -> None:
        if not report_path.exists():
            self.validation_status.setText("No validation report (validation was switched off)")
            self.validation_output.clear()
            return
        report = json.loads(report_path.read_text(encoding="utf-8"))
        status = report.get("status", "")
        summary = report.get("summary", {})
        color = PASS_COLOR.name() if status == "PASS" else FAIL_COLOR.name()
        self.validation_status.setText(
            f"<span style='color:{color}'>{html.escape(status)}</span> &nbsp; "
            f"{summary.get('errors', 0)} errors, {summary.get('warnings', 0)} warnings"
        )
        self.validation_output.setPlainText(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    def apply_preview_filter(self) -> None:
        self.setCursor(Qt.WaitCursor)
        try:
            self.preview_proxy.setFilterFixedString(self.preview_filter.text().strip())
        finally:
            self.unsetCursor()
        self._update_preview_info()

    def _update_preview_info(self) -> None:
        shown, total = self.preview_proxy.rowCount(), self.preview_model.rowCount()
        self.preview_info.setText(f"{shown:,} of {total:,} rows" if shown != total else f"{total:,} rows")

    def open_current_json(self) -> None:
        dataset = self.dataset_combo.currentText()
        if dataset:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.output_input.text().strip()) / f"{dataset}.json")))

    def open_output_folder(self) -> None:
        folder = self.output_input.text().strip()
        if folder and Path(folder).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.information(self, "No output folder", "Choose an existing output folder in step 3 first.")

    # ------------------------------------------------------------------
    # Logs, settings, reset
    # ------------------------------------------------------------------
    def append_log(self, message: str) -> None:
        """Add a log line (warnings amber, errors red) and drive the progress bar."""
        color = "#B91C1C" if ("ERROR" in message or "failed" in message.lower()) else "#B45309" if "WARNING" in message else "#0F172A"
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
        self._update_preview_info()
        self.columns_table.setRowCount(0)
        self.validation_output.clear()
        self.validation_status.clear()
        self.log_output.clear()
        self._set_stats(None)
        self._save_settings()
        self.statusBar().showMessage("Reset.")
