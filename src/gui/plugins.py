from pathlib import Path

from loguru import logger
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.orm import sessionmaker

from core.config import read_config
from core.parse import parse_any
from core.utils import PDFReader, PluginManager


def display_nested_dict(output_display: QTextEdit, nested_dict: dict, level=0):
    """
    Recursively displays a nested dictionary in an indented format.

    Args:
        output_display: A callable (e.g., self.output_display.append) for displaying output.
        nested_dict (dict): The dictionary to display.
        level (int): Current level of indentation.
    """
    for key, value in nested_dict.items():
        if isinstance(value, dict):
            # If the value is a dictionary, recurse
            output_display.append("  " * (level + 1) + f"{key}:")
            display_nested_dict(output_display, value, level + 1)
        else:
            # Otherwise, display the key-value pair
            output_display.append("  " * (level + 1) + f"{key}: {value}")


class ParseTestDialog(QDialog):
    def __init__(
        self, Session: sessionmaker, plugin_manager: PluginManager, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("PDF Parsing Troubleshooter")
        self.resize(800, 600)

        self.Session = Session
        self.plugin_manager = plugin_manager

        # Layout
        layout = QVBoxLayout(self)

        # Buttons
        self.read_pdf_button = QPushButton("Read PDF")
        self.read_pdf_button.clicked.connect(self.read_pdf)
        layout.addWidget(self.read_pdf_button)

        self.extract_tables_button = QPushButton("Extract Tables")
        self.extract_tables_button.clicked.connect(self.extract_tables)
        layout.addWidget(self.extract_tables_button)

        self.test_import_button = QPushButton("Import and Parse File")
        self.test_import_button.clicked.connect(self.test_import)
        layout.addWidget(self.test_import_button)

        # Output Display
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Courier New"))
        layout.addWidget(self.output_display)

        # Load configuration
        self.config = read_config()
        self.db_path = Path(self.config.get("DATABASE", "db_path")).resolve()
        self.import_dir = self.config.get("IMPORT", "import_dir")

    def select_file(self) -> Path:
        """Open a file dialog to select a file."""
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_filter = "Supported Files (*.csv *.pdf *.xlsx);;All Files (*)"
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Select a File", self.import_dir, file_filter, options=options
        )
        return Path(fpath).resolve() if fpath else None

    def display_output(self, text: str):
        """Append text to the output display."""
        self.output_display.append(text)

    def read_pdf(self):
        """Read and display raw PDF content."""
        try:
            fpath = self.select_file()
            if not fpath:
                return

            with PDFReader(fpath) as reader:
                self.display_raw_output(fpath, reader)
        except Exception as e:
            logger.exception("Error reading PDF:")
            self.display_output(f"Error: {e}")

    def display_raw_output(self, fpath: Path, reader: PDFReader):
        """Display raw output from the PDFReader."""
        self.output_display.clear()
        self.display_output(f"File: {fpath}")

        # Metadata
        self.display_output("\nMetadata:\n" + "=" * 60)
        for key, value in reader.PDF.metadata.items():
            self.display_output(f"{key}: {value}")

        # Annotations
        self.display_output("\nAnnotations:\n" + "=" * 60)
        for i, page in enumerate(reader.PDF.pages):
            for annot in page.annots:
                self.display_output(f"Annotation {i}:")
                self.display_nested_dict(annot)

        # Simple Text Extraction
        self.display_output("\nSimple Extraction Lines:\n" + "=" * 60)
        self.display_output("\n".join(reader.extract_lines_simple()))

        # Layout Lines
        self.display_output("\nLayout Text:\n" + "=" * 60)
        self.display_output(reader.extract_text_layout())

    def display_nested_dict(self, nested_dict: dict, level=0):
        """Recursively display nested dictionaries."""
        for key, value in nested_dict.items():
            if isinstance(value, dict):
                self.display_output("  " * level + f"{key}:")
                self.display_nested_dict(value, level + 1)
            else:
                self.display_output("  " * level + f"{key}: {value}")

    def extract_tables(self):
        """Extract and display tables from a PDF."""
        try:
            fpath = self.select_file()
            if not fpath:
                return

            with PDFReader(fpath) as reader:
                self.display_table_output(fpath, reader)
        except Exception as e:
            logger.exception("Error extracting tables:")
            self.display_output(f"Error: {e}")

    def display_table_output(self, fpath: Path, reader: PDFReader):
        """Display table data extracted from a PDF."""
        self.output_display.clear()
        self.display_output(f"File: {fpath}")

        table_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}
        for page_no, page in enumerate(reader.PDF.pages):
            self.display_output(f"Page {page_no}:\n" + "=" * 20)
            tables = page.extract_tables(table_settings=table_settings)
            for table_no, table in enumerate(tables):
                self.display_output(f"Table {table_no}:")
                for row in table:
                    self.display_output(" | ".join(row))

    def test_import(self):
        """Test parsing a file and display results."""
        try:
            fpath = self.select_file()
            if not fpath:
                return

            # Return the statement object
            statement = parse_any(
                self.Session, self.plugin_manager, fpath, hard_fail=False
            )

            # Display results
            self.output_display.clear()
            self.display_output(f"File: {statement.fpath}")
            self.display_output(f"StatementTypeID: {statement.stid}")
            self.display_output(f"Start Date: {statement.start_date}")
            self.display_output(f"End Date: {statement.end_date}")
            for account in statement.accounts:
                self.display_output(f"  Account Number: {account.account_num}")
                self.display_output(f"  Start Balance: {account.start_balance}")
                self.display_output(f"  End Balance: {account.end_balance}")
                self.display_output("  Transactions:")
                for transaction in account.transactions:
                    self.display_output(
                        f"    {transaction.transaction_date} {transaction.posting_date}"
                        f" {transaction.amount} {transaction.balance} {transaction.desc}"
                    )
        except Exception as e:
            logger.exception("Error importing file:")
            self.display_output(f"Error: {e}")
