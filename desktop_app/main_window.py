"""Main window for the dsjson desktop application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
        self.setMinimumSize(850, 600)

        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None

        self.domain_input = QComboBox()
        self.domain_input.setEditable(True)
        self.domain_input.addItems(["DM", "AE", "IE", "CO"])

        self.xpt_input = QLineEdit()
        self.define_input = QLineEdit()
        self.output_input = QLineEdit()

        self.validate_checkbox = QCheckBox("Run Dataset-JSON validation")
        self.validate_checkbox.setChecked(True)

        self.convert_button = QPushButton("Convert to Dataset-JSON")
        self.convert_button.clicked.connect(self.start_conversion)

        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

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
        form_layout.addRow("XPT File:", self._file_picker_row(self.xpt_input, self.browse_xpt_file))
        form_layout.addRow("Define-XML:", self._file_picker_row(self.define_input, self.browse_define_file))
        form_layout.addRow("Output Folder:", self._file_picker_row(self.output_input, self.browse_output_folder))
        form_layout.addRow("", self.validate_checkbox)

        input_group.setLayout(form_layout)
        main_layout.addWidget(input_group)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        log_group = QGroupBox("Status / Logs")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)

        main_layout.addWidget(log_group)

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

            # If domain field is empty or unchanged, infer from file name.
            inferred_domain = Path(file_path).stem.upper()
            if inferred_domain:
                self.domain_input.setCurrentText(inferred_domain)

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

    def start_conversion(self) -> None:
        """Start background conversion."""
        domain = self.domain_input.currentText().strip().upper()
        xpt_path = self.xpt_input.text().strip()
        define_path = self.define_input.text().strip()
        output_dir = self.output_input.text().strip()
        validate = self.validate_checkbox.isChecked()

        if not self._validate_ui_inputs(domain, xpt_path, define_path, output_dir):
            return

        self.convert_button.setEnabled(False)
        self.append_log(f"[{domain}] Conversion request submitted")

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
            QMessageBox.warning(self, "Missing Domain", "Please enter a domain, for example DM.")
            return False

        if not xpt_path:
            QMessageBox.warning(self, "Missing XPT File", "Please select an XPT file.")
            return False

        if not define_path:
            QMessageBox.warning(self, "Missing Define-XML", "Please select a Define-XML file.")
            return False

        if not output_dir:
            QMessageBox.warning(self, "Missing Output Folder", "Please select an output folder.")
            return False

        return True

    def on_conversion_finished(self, success: bool, message: str) -> None:
        """Handle conversion completion."""
        self.convert_button.setEnabled(True)

        if success:
            self.append_log(message)
            QMessageBox.information(self, "Conversion Completed", message)
        else:
            self.append_log(message)
            QMessageBox.critical(self, "Conversion Failed", message)

    def append_log(self, message: str) -> None:
        """Append message to the log area."""
        self.log_output.append(message)

    def clear_logs(self) -> None:
        """Clear log window."""
        self.log_output.clear()