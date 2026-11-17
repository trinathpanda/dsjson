"""Entry point for the dsjson desktop application."""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from desktop_app.main_window import MainWindow


def main() -> int:
    """Start the dsjson desktop application."""
    app = QApplication(sys.argv)
    app.setOrganizationName("dsjson")
    app.setApplicationName("dsjson")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)  # stylesheet is dark; same look whatever the Windows theme
    app.setStyle("Fusion")  # same look on every Windows version; stylesheet in main_window
    app.setFont(QFont("Segoe UI", 10))

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())