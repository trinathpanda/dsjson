"""Main window for the dsjson desktop application."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.worker import ConversionWorker


class MainWindow(QMainWindow):
    """Simple desktop UI for dsjson conversion."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("DSJSON Converter")
        self.setMinimumSize(950, 700)

        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None

        self.latest_dataset_json_path: Path | None = None
        self.latest_validation_report_path: Path | None = None

        # Input fields
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Enter domain, e.g. DM")

        self.xpt_input = QLineEdit()
        self.define_input = QLineEdit()
        self.output_input = QLineEdit()

        self.validate_checkbox = QCheckBox("Run Dataset-JSON validation")
        self.validate_checkbox.setChecked(True)

        # Buttons
        self.convert_button = QPushButton("Convert to Dataset-JSON")
        self.convert_button.clicked.connect(self.start_conversion)

        self.open_dataset_json_button = QPushButton("Open Dataset-JSON")
        self.open_dataset_json_button.clicked.connect(self.open_dataset_json)
        self.open_dataset_json_button.setEnabled(False)

        self.open_validation_report_button = QPushButton("Open Validation Report")
        self.open_validation_report_button.clicked.connect(self.open_validation_report)
        self.open_validation_report_button.setEnabled(False)

        self.clear_logs_button = QPushButton("Clear Logs")
        self.clear_logs_button.clicked.connect(self.clear_logs)

        self.clear_fields_button = QPushButton("Clear Fields")
        self.clear_fields_button.clicked.connect(self.clear_fields)

        # Output tabs
        self.tabs = QTabWidget()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.dataset_table = QTableWidget()
        self.dataset_table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.validation_output = QTextEdit()
        self.validation_output.setReadOnly(True)

        self.tabs.addTab(self.log_output, "Logs")
        self.tabs.addTab(self.dataset_table, "Dataset-JSON Preview")
        self.tabs.addTab(self.validation_output, "Validation Report")

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the window layout."""
        central_widget = QWidget()
        main_layout = QVBoxLayout()

        header = QLabel("DSJSON Converter")
        header.setStyleSheet("font-size: 22px; font-weight: bold;")

        subtitle = QLabel(
            "Convert SDTM XPT + Define-XML into CDISC Dataset-JSON locally."
        )
        subtitle.setStyleSheet("font-size: 12px; color: gray;")

        main_layout.addWidget(header)
        main_layout.addWidget(subtitle)

        input_group = QGroupBox("Input")
        form_layout = QFormLayout()

        form_layout.addRow("Domain:", self.domain_input)
        form_layout.addRow(
            "XPT File:",
            self._file_picker_row(self.xpt_input, self.browse_xpt_file),
        )
        form_layout.addRow(
            "Define-XML:",
            self._file_picker_row(self.define_input, self.browse_define_file),
        )
        form_layout.addRow(
            "Output Folder:",
            self._file_picker_row(self.output_input, self.browse_output_folder),
        )
        form_layout.addRow("", self.validate_checkbox)

        input_group.setLayout(form_layout)
        main_layout.addWidget(input_group)

        button_layout_1 = QHBoxLayout()
        button_layout_1.addWidget(self.convert_button)
        button_layout_1.addWidget(self.open_dataset_json_button)
        button_layout_1.addWidget(self.open_validation_report_button)

        button_layout_2 = QHBoxLayout()
        button_layout_2.addWidget(self.clear_logs_button)
        button_layout_2.addWidget(self.clear_fields_button)

        main_layout.addLayout(button_layout_1)
        main_layout.addLayout(button_layout_2)

        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout()
        output_layout.addWidget(self.tabs)
        output_group.setLayout(output_layout)

        main_layout.addWidget(output_group)

        note = QLabel(
            "Data protection note: This desktop app runs locally. "
            "No SDTM data is uploaded to any server."
        )
        note.setStyleSheet("font-size: 11px; color: #555;")
        main_layout.addWidget(note)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _file_picker_row(self, line_edit: QLineEdit, browse_callback) -> QWidget:
        """Create a row with a text field and Browse button."""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(browse_callback)

        layout.addWidget(line_edit)
        layout.addWidget(browse_button)

        widget.setLayout(layout)
        return widget

    def browse_xpt_file(self) -> None:
        """Select XPT file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select XPT File",
            "",
            "XPT Files (*.xpt);;All Files (*.*)",
        )

        if file_path:
            self.xpt_input.setText(file_path)

            inferred_domain = Path(file_path).stem.upper()
            if inferred_domain:
                self.domain_input.setText(inferred_domain)

    def browse_define_file(self) -> None:
        """Select Define-XML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Define-XML File",
            "",
            "XML Files (*.xml);;All Files (*.*)",
        )

        if file_path:
            self.define_input.setText(file_path)

    def browse_output_folder(self) -> None:
        """Select output folder."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            "",
        )

        if folder_path:
            self.output_input.setText(folder_path)
            self._set_latest_paths_from_inputs()
            self._update_open_buttons_state()

    def start_conversion(self) -> None:
        """Start background conversion."""
        domain = self.domain_input.text().strip().upper()
        xpt_path = self.xpt_input.text().strip()
        define_path = self.define_input.text().strip()
        output_dir = self.output_input.text().strip()
        validate = self.validate_checkbox.isChecked()

        if not self._validate_ui_inputs(domain, xpt_path, define_path, output_dir):
            return

        self.convert_button.setEnabled(False)
        self.open_dataset_json_button.setEnabled(False)
        self.open_validation_report_button.setEnabled(False)

        self.latest_dataset_json_path = None
        self.latest_validation_report_path = None

        self.append_log(f"[{domain}] Conversion request submitted")
        self.tabs.setCurrentWidget(self.log_output)

        self.worker_thread = QThread()
        self.worker = ConversionWorker(
            domain=domain,
            xpt_path=xpt_path,
            define_path=define_path,
            output_dir=output_dir,
            validate=validate,
            log_level="INFO",
        )

        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    def _validate_ui_inputs(
        self,
        domain: str,
        xpt_path: str,
        define_path: str,
        output_dir: str,
    ) -> bool:
        """Validate visible UI fields."""
        if not domain:
            QMessageBox.warning(
                self,
                "Missing Domain",
                "Please enter a domain, for example DM.",
            )
            return False

        if not xpt_path:
            QMessageBox.warning(
                self,
                "Missing XPT File",
                "Please select an XPT file.",
            )
            return False

        if not define_path:
            QMessageBox.warning(
                self,
                "Missing Define-XML",
                "Please select a Define-XML file.",
            )
            return False

        if not output_dir:
            QMessageBox.warning(
                self,
                "Missing Output Folder",
                "Please select an output folder.",
            )
            return False

        return True

    def on_conversion_finished(self, success: bool, message: str) -> None:
        """Handle conversion completion."""
        self.convert_button.setEnabled(True)

        if success:
            self._set_latest_paths_from_inputs()
            self._update_open_buttons_state()

            self.append_log(message)
            QMessageBox.information(self, "Conversion Completed", message)
        else:
            self.open_dataset_json_button.setEnabled(False)
            self.open_validation_report_button.setEnabled(False)

            self.append_log(message)
            QMessageBox.critical(self, "Conversion Failed", message)

    def _set_latest_paths_from_inputs(self) -> None:
        """Set latest output file paths based on current domain and output folder."""
        domain = self.domain_input.text().strip().upper()
        output_dir = self.output_input.text().strip()

        if not domain or not output_dir:
            self.latest_dataset_json_path = None
            self.latest_validation_report_path = None
            return

        output_path = Path(output_dir)

        self.latest_dataset_json_path = output_path / f"{domain}.json"
        self.latest_validation_report_path = (
            output_path / "validation_report" / f"{domain}_validation.json"
        )

    def _update_open_buttons_state(self) -> None:
        """Enable/disable open buttons based on latest output files."""
        dataset_exists = (
            self.latest_dataset_json_path is not None
            and self.latest_dataset_json_path.exists()
        )

        report_exists = (
            self.latest_validation_report_path is not None
            and self.latest_validation_report_path.exists()
        )

        self.open_dataset_json_button.setEnabled(dataset_exists)
        self.open_validation_report_button.setEnabled(report_exists)

    def open_dataset_json(self) -> None:
        """Open latest Dataset-JSON inside the UI as a table."""
        dataset_json_path = self.latest_dataset_json_path

        if dataset_json_path is None or not dataset_json_path.exists():
            QMessageBox.warning(
                self,
                "Dataset-JSON Not Found",
                "No latest Dataset-JSON file found. Please run conversion first.",
            )
            return

        try:
            with dataset_json_path.open("r", encoding="utf-8") as file:
                dataset_json = json.load(file)

            self._load_dataset_json_table(dataset_json)
            self.tabs.setCurrentWidget(self.dataset_table)

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Unable to Open Dataset-JSON",
                f"Failed to open Dataset-JSON:\n{exc}",
            )

    def _load_dataset_json_table(self, dataset_json: dict) -> None:
        """Load Dataset-JSON rows into the preview table."""
        columns = dataset_json.get("columns", [])
        rows = dataset_json.get("rows", [])

        column_names = []

        for column in columns:
            name = column.get("name", "")
            label = column.get("label", "")

            if label and label != name:
                column_names.append(f"{name}\n{label}")
            else:
                column_names.append(str(name))

        self.dataset_table.clear()
        self.dataset_table.setColumnCount(len(column_names))
        self.dataset_table.setRowCount(len(rows))
        self.dataset_table.setHorizontalHeaderLabels(column_names)

        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                self.dataset_table.setItem(row_index, col_index, item)

        self.dataset_table.resizeColumnsToContents()

    def open_validation_report(self) -> None:
        """Open latest validation report inside the UI."""
        validation_report_path = self.latest_validation_report_path

        if validation_report_path is None or not validation_report_path.exists():
            QMessageBox.warning(
                self,
                "Validation Report Not Found",
                "No latest validation report found. Please run conversion first.",
            )
            return

        try:
            with validation_report_path.open("r", encoding="utf-8") as file:
                validation_report = json.load(file)

            pretty_report = json.dumps(
                validation_report,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

            self.validation_output.setPlainText(pretty_report)
            self.tabs.setCurrentWidget(self.validation_output)

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Unable to Open Validation Report",
                f"Failed to open validation report:\n{exc}",
            )

    def append_log(self, message: str) -> None:
        """Append message to the log area."""
        self.log_output.append(message)

    def clear_logs(self) -> None:
        """Clear log window."""
        self.log_output.clear()

    def clear_fields(self) -> None:
        """Clear all user input fields and output tabs."""
        self.domain_input.clear()
        self.xpt_input.clear()
        self.define_input.clear()
        self.output_input.clear()

        self.latest_dataset_json_path = None
        self.latest_validation_report_path = None

        self.log_output.clear()
        self.validation_output.clear()

        self.dataset_table.clear()
        self.dataset_table.setRowCount(0)
        self.dataset_table.setColumnCount(0)

        self.open_dataset_json_button.setEnabled(False)
        self.open_validation_report_button.setEnabled(False)
        self.convert_button.setEnabled(True)

        self.tabs.setCurrentWidget(self.log_output)