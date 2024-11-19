import sys
from pathlib import Path

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.parse import parse, read_pdf
from core.utils import read_config


class TestImportApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Import Environment")
        self.resize(600, 400)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # Add Import button
        self.import_button = QPushButton("Read PDF")
        self.import_button.clicked.connect(self.read_pdf)
        layout.addWidget(self.import_button)

        # Add Import button
        self.import_button = QPushButton("Import and Parse File")
        self.import_button.clicked.connect(self.test_import)
        layout.addWidget(self.import_button)

        # Add text display for output
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Courier New"))
        layout.addWidget(self.output_display)

        # Load configuration
        self.config = read_config(Path("") / "config.ini")
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()
        self.import_dir = self.config.get("IMPORT", "import_dir")

    def select_file(self):
        # Open file dialog
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_filter = "Supported Files (*.csv *.pdf *.xlsx);;All Files (*)"
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Select a File", self.import_dir, file_filter, options=options
        )
        return fpath

    def read_pdf(self):
        """
        Function to handle file import and parsing.
        """
        try:
            fpath = self.select_file()
            if not fpath:
                return
            fpath = Path(fpath).resolve()

            # Parse the selected file
            text, lines_raw, lines = read_pdf(fpath)

            # Display parsed data in the output display
            self.output_display.clear()
            self.output_display.append(f"File: {fpath}")
            self.output_display.append("Verbatim Text:\n" + 60 * "=")
            self.output_display.append(f"{text}")
            self.output_display.append("\n\nRaw Lines:\n" + 60 * "=")
            self.output_display.append("\n".join(lines_raw))
            self.output_display.append("\n\nCleaned Lines:\n" + 60 * "=")
            self.output_display.append("\n".join(lines))

        except Exception as e:
            # Display any errors in the output display
            self.output_display.append(f"Error: {str(e)}")

    def test_import(self):
        """
        Function to handle file import and parsing.
        """
        try:
            fpath = self.select_file()
            if not fpath:
                return
            fpath = Path(fpath).resolve()

            # Parse the selected file
            STID, date_range, data = parse(self.db_path, fpath)

            # Display parsed data in the output display
            self.output_display.clear()
            self.output_display.append(f"File: {fpath}")
            self.output_display.append(f"STID: {STID}")
            self.output_display.append(f"Date Range: {date_range}")
            self.output_display.append("Parsed Data:")
            for account, transactions in data.items():
                self.output_display.append("Account: " + str(account))
                self.output_display.append(
                    "\n".join([str(line) for line in transactions])
                )

        except Exception as e:
            # Display any errors in the output display
            self.output_display.append(f"Error: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TestImportApp()
    main_window.show()
    sys.exit(app.exec_())
