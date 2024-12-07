import sys
from pathlib import Path

from loguru import logger
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

from core.parse import parse_any
from core.utils import PDFReader, read_config
from core.orm import create_database


class TestImportApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Import Environment")
        self.resize(800, 600)

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
        self.extract_tables_button = QPushButton("Extract Tables")
        self.extract_tables_button.clicked.connect(self.extract_tables)
        layout.addWidget(self.extract_tables_button)

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
            with PDFReader(fpath) as reader:
                self.display_raw_output(fpath, reader)

        except Exception as e:
            logger.exception("Import failed:")
            # Display any errors in the output display
            self.output_display.append(f"Error: {str(e)}")

    def display_raw_output(self, fpath: Path, reader: PDFReader):
        # Display parsed data in the output display
        reader.extract_lines_simple()
        reader.extract_lines_clean()
        self.output_display.clear()

        self.output_display.append(f"File: {fpath}")
        self.output_display.append(f"Metadata:")
        for key, value in reader.PDF.metadata.items():
            self.output_display.append(f"  {key}: {value}")

        self.output_display.append(f"Annotations:")
        for page in reader.PDF.pages:
            for annot in page.annots:
                title = annot.get("title")
                value = annot["data"]["V"].decode("utf-8") if annot["data"]["V"] else ""
                self.output_display.append(f"  {title}: {value}")

        self.output_display.append("\n\nSimple Extraction Lines:\n" + 60 * "=")
        self.output_display.append("\n".join(reader.lines_simple))

        self.output_display.append("\n\nPage Layout Text:\n" + 60 * "=")
        for page_no, page in enumerate(reader.pages):
            self.output_display.append(f"Page No:{page_no}")
            self.output_display.append(f"{page}")

        self.output_display.append("\n\nLayout Lines:\n" + 60 * "=")
        self.output_display.append("\n".join(reader.lines_raw))

        self.output_display.append("\n\nWhitespace Normalized Lines:\n" + 60 * "=")
        self.output_display.append("\n".join(reader.lines_clean))

    def extract_tables(self):
        try:
            fpath = self.select_file()
            if not fpath:
                return
            fpath = Path(fpath).resolve()

            # Parse the selected file
            with PDFReader(fpath) as reader:
                self.display_table_output(fpath, reader)

        except Exception as e:
            logger.exception("Import failed:")
            # Display any errors in the output display
            self.output_display.append(f"Error: {str(e)}")

    def display_table_output(self, fpath: Path, reader: PDFReader):
        table_settings = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        }
        self.output_display.clear()
        self.output_display.append(f"File: {fpath}")
        for page_no, page in enumerate(reader.doc.pages):
            self.output_display.append(f"Page No: {page_no}")
            tables = page.extract_tables(table_settings=table_settings)
            for table_no, table in enumerate(tables):
                self.output_display.append(f"Table No: {table_no}")
                for row in table:
                    line = " ".join((" ".join(row)).split())
                    self.output_display.append(f"{line}")

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
            Session = create_database(self.db_path)
            statement = parse_any(Session, fpath, hard_fail=False)

            # Display parsed data in the output display
            self.output_display.clear()
            self.output_display.append(f"File: {statement.fpath}")
            self.output_display.append(f"StatementTypeID: {statement.stid}")
            self.output_display.append(f"Start Date: {statement.start_date}")
            self.output_display.append(f"End Date: {statement.end_date}")
            for account in statement.accounts:
                self.output_display.append(f"  Account Number: {account.account_num}")
                self.output_display.append(f"  Start Balance: {account.start_balance}")
                self.output_display.append(f"  End Balance: {account.end_balance}")
                self.output_display.append(f"  Transactions:")
                for transaction in account.transactions:
                    self.output_display.append(
                        f"    {transaction.transaction_date} {transaction.posting_date}"
                        f" {transaction.amount} {transaction.balance} {transaction.desc}"
                    )

        except Exception as e:
            logger.exception("Import failed:")
            # Display any errors in the output display
            self.output_display.append(f"Error: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = TestImportApp()
    main_window.show()
    sys.exit(app.exec_())
