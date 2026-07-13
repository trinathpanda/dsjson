"""Entry point for the dsjson desktop application."""

import sys

from PySide6.QtWidgets import QApplication

from desktop_app.main_window import MainWindow


def main() -> int:
    """Start the dsjson desktop application."""
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())