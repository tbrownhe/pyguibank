import csv
import re
from pathlib import Path
from typing import Any

import openpyxl
import pdftotext
from loguru import logger

from . import parsecsv, parsepdf, parsexlsx
from .query import statement_types


def select_parser(db_path: Path, text: str, extension="") -> tuple[int, str]:
    """_summary_

    Args:
        db_path (Path): Path to database
        text (str): Plaintext contents of statement
        extension (str, optional): Extension of statement file. Defaults to "".

    Raises:
        ValueError: Statement is not recognized. A parser likely needs to be built.

    Returns:
        tuple[int, str]: StatementTypeID and parser name from StatementTypes.Parser
    """
    data, _ = statement_types(db_path, extension=extension)
    text_lower = text.lower()
    for STID, pattern, parser in data:
        if all(
            re.search(re.escape(search_str), text_lower)
            for search_str in pattern.lower().split("&&")
        ):
            return STID, parser
    logger.error(
        "Statement type not recognized. Update StatementTypes and parsing scripts."
    )
    raise ValueError("Statement type not recognized.")


def route_data_to_parser(
    parser: str, parsers: dict, input_data: Any
) -> tuple[dict[str, Any], dict[str, list]]:
    """Called by multiple file routing classes.
    Selects a parsing module from the dict based on the parser str
    then passes the data variable to it and returns the output of the parser

    Args:
        parser (str): Parser name from StatementTypes.Parser
        parsers (dict): Class attribute dict from the xRouter classes
        input_data (Any): PDFReader, list[list[str]], dict[str, list], etc...

    Raises:
        ValueError: Parser could not be found for this statement

    Returns:
        tuple[dict[str, Any], dict[str, list]]: metadata dict and data dict from parser
    """
    if parser not in parsers:
        available_parsers = ", ".join(parsers.keys())
        logger.error(
            f"Parser name '{parser}' must be added to the registry. "
            f"Available parsers: {available_parsers}"
        )
        raise ValueError(f"Parser '{parser}' not found.")
    return parsers[parser](input_data)


class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.text = None
        self.lines_raw = None
        self.lines = None
        self.read_pdf()

    def read_pdf(self):
        """
        Reads and processes the PDF file, storing text and lines in the instance.
        """
        with self.fpath.open("rb") as f:
            doc = pdftotext.PDF(f, physical=True)
        self.text = "\n".join(doc)
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        self.lines = [" ".join(line.split()) for line in self.lines_raw]


class PDFRouter:
    # Add parsing modules here as the project grows
    PARSERS = {
        "occubank": parsepdf.occubank.parse,
        "citi": parsepdf.citi.parse,
        "usbank": parsepdf.usbank.parse,
        "occucc": parsepdf.occucc.parse,
        "wfper": parsepdf.wfper.parse,
        "wfbus": parsepdf.wfbus.parse,
        "wfploan": parsepdf.wfploan.parse,
        "fidelity401k": parsepdf.fidelity401k.parse,
        "fidelityhsa": parsepdf.fidelityhsa.parse,
        "hehsa": parsepdf.hehsa.parse,
        "transamerica": parsepdf.transamerica.parse,
        "vanguard": parsepdf.vanguard.parse,
    }

    def __init__(self, db_path: Path, fpath: Path):
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> tuple[dict[str, Any], dict[str, list]]:
        """Opens the PDF file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            tuple[dict[str, Any], dict[str, list]]: metadata and data from the statement
        """
        reader = PDFReader(self.fpath)
        STID, parser = select_parser(reader.text, extension=".pdf")
        metadata, data = self.parse_switch(parser, reader)
        metadata["StatementTypeID"] = STID
        return metadata, data

    def parse_switch(self, parser: str, pdf_reader: PDFReader):
        """Dynamically route to the correct parsing function using PDFReader."""
        try:
            return route_data_to_parser(parser, self.PARSERS, pdf_reader)
        except Exception:
            logger.exception(f"Error while parsing PDF with parser '{parser}':")
            raise


class CSVRouter:
    # Add parsing modules here as the project grows
    PARSERS = {
        "occuauto": parsecsv.occuauto.parse,
        "amazonper": parsecsv.amazonper.parse,
        "amazonbus": parsecsv.amazonbus.parse,
    }

    def __init__(self, db_path: Path, fpath: Path):
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> tuple[dict[str, Any], dict[str, list]]:
        """Opens the CSV file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            tuple[dict[str, Any], dict[str, list]]: metadata and data from the statement
        """
        text = self.read_csv_as_text()
        self.array = self.read_csv_as_array()

        # Determine which parsing script to use
        STID, parser = select_parser(self.db_path, text, extension=".csv")
        metadata, data = self.parse_switch(parser)
        metadata["StatementTypeID"] = STID
        return metadata, data

    def read_csv_as_text(self):
        """Reads the CSV file and returns its contents as plain text."""
        with self.fpath.open("r", encoding="utf-8-sig") as f:
            return f.read()

    def read_csv_as_array(self):
        """Reads the CSV file and returns its contents as a list of rows."""
        array = []
        with self.fpath.open("r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                array.append(row)
        return array

    def parse_switch(self, parser: str):
        """Dynamically route to the correct parsing function."""
        try:
            return route_data_to_parser(parser, self.PARSERS, self.array)
        except Exception:
            logger.exception(f"Error while parsing CSV with parser '{parser}':")
            raise


class XLSXRouter:
    # Add parsing modules here as the project grows
    PARSERS = {"fedloan": parsexlsx.fedloan.parse}

    def __init__(self, db_path: Path, fpath: Path):
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> tuple[dict[str, Any], dict[str, list]]:
        """Opens the XLSX file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            tuple[dict[str, Any], dict[str, list]]: metadata and data from the statement
        """
        sheets = self.read_xlsx()
        text = self.plaintext(sheets)
        STID, parser = select_parser(self.db_path, text, extension=".xlsx")
        metadata, data = self.parse_switch(parser, sheets)
        metadata["StatementTypeID"] = STID
        return metadata, data

    def plaintext(self, sheets):
        """Convert all workbook data to plaintext"""
        text = "\n".join(
            "\n".join(", ".join(str(cell) for cell in row if cell) for row in sheet)
            for sheet in sheets.values()
        )
        return text

    def read_xlsx(self) -> dict[str, list]:
        """Load the worksheets, skipping any blank rows"""
        workbook = openpyxl.load_workbook(self.fpath)
        sheets = {
            sheet.title: [row for row in sheet.values if any(row)]
            for sheet in workbook.worksheets
        }
        return sheets

    def parse_switch(self, parser: str, sheets: dict[str, list]):
        """Dynamically route to the correct parsing function."""
        try:
            return route_data_to_parser(parser, self.PARSERS, sheets)
        except Exception:
            logger.exception(f"Error while parsing XLSX with parser '{parser}':")
            raise


# Definte routers for extensibility
ROUTERS = {
    ".pdf": PDFRouter,
    ".csv": CSVRouter,
    ".xlsx": XLSXRouter,
}


def parse(db_path: Path, fpath: Path) -> tuple[dict[str, Any], dict[str, list[tuple]]]:
    """Routes the file to the appropriate parser based on its extension.

    Args:
        db_path (Path): Path to database file
        fpath (Path): Statement file to be parsed

    Raises:
        ValueError: Unsupported file extension

    Returns:
        tuple[dict[str, Any], dict[str, list[tuple]]]: metadata and data dicts
    """
    suffix = fpath.suffix.lower()
    if suffix in ROUTERS:
        router = ROUTERS[suffix](db_path, fpath)
        return router.parse()
    raise ValueError(f"Unsupported file extension: {suffix}")
