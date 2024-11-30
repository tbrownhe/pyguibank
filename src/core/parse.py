import csv
import importlib
import re
from pathlib import Path
from typing import Any, Union, Callable

import openpyxl
from loguru import logger

from . import parsecsv, parsepdf, parsexlsx
from .query import statement_types
from .utils import PDFReader
from .validation import Statement, StatementValidationError, validate_statement


def load_parser(entry_point: str) -> Any:
    """Loads a parser dynamically from its entry point."""
    try:
        module_path, func_name = entry_point.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Failed to load parser: {entry_point}") from e


def select_parser(db_path: Path, text: str, extension="") -> tuple[int, str]:
    """Pulls parser search strings from database, then does pattern matching to
    find the StatementTypeID and parser name for this statement.

    Args:
        db_path (Path): Path to database
        text (str): Plaintext contents of statement
        extension (str, optional): Extension of statement file. Defaults to "".

    Raises:
        ValueError: Statement is not recognized. A parser likely needs to be built.

    Returns:
        tuple[int, str]: StatementTypeID and Parser from StatementTypes
    """
    data, _ = statement_types(db_path, extension=extension)
    text_lower = text.lower()
    for stid, pattern, entry_point in data:
        if all(
            re.search(re.escape(search_str), text_lower)
            for search_str in pattern.lower().split("&&")
        ):
            return stid, entry_point
    logger.error(
        "Statement type not recognized. Update StatementTypes and parsing scripts."
    )
    raise ValueError("Statement type not recognized.")


def route_data_to_parser(parser: str, parsers: dict, input_data: Any) -> Statement:
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
        Statement: All statement data stored in a validated dataclass
    """
    if parser not in parsers:
        available_parsers = ", ".join(parsers.keys())
        logger.error(
            f"Parser name '{parser}' must be added to the registry. "
            f"Available parsers: {available_parsers}"
        )
        raise ValueError(f"Parser '{parser}' not found.")
    return parsers[parser](input_data)


class BaseRouter:
    def __init__(self, parsers: dict):
        self.parsers = parsers

    def parse_switch(
        self,
        parser: str,
        input_data: Union[PDFReader, list[list[str]], dict[str, list]],
    ) -> Statement:
        """Send the input data to the correct parser based on the
        PARSERS dict passed from child classes

        Args:
            parser (str): name of parsing module from StatementTypes.Parsers
            input_data (Any): PDFReader, csv array, or xlsx sheets

        Returns:
            Statement: Contents of parsed statement
        """
        try:
            return route_data_to_parser(parser, self.parsers, input_data)
        except Exception:
            logger.exception(
                f"Error while parsing with parser '{parser}'"
                f"and input type '{type(input_data).__name__}':"
            )
            raise

    def validate(self, statement: Statement, parser: str):
        try:
            validate_statement(statement)
        except StatementValidationError as e:
            logger.error(
                f"Validation failed for statement imported using"
                f" parser '{parser}': {e}"
            )
            raise


class PDFRouter(BaseRouter):
    def __init__(self, db_path: Path, fpath: Path):
        # Add parsing modules here as the project grows
        parsers = {
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
        super().__init__(parsers)
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> tuple[int, Statement]:
        """Opens the PDF file, determines its type, and routes its reader
        to the appropriate parsing module.

        Returns:
            Statement: Statement contents in the dataclass
        """
        with PDFReader(self.fpath) as reader:
            text = reader.extract_text()
            stid, entry_point = select_parser(self.db_path, text, extension=".pdf")
            parser = self.load_and_validate_parser(entry_point)
            statement = self.run_parser(parser, reader)

        # Validate and return statement data
        statement.stid = stid
        self.validate(statement, parser)
        return statement

    def load_and_validate_parser(
        self, entry_point: str
    ) -> Callable[[PDFReader], Statement]:
        """
        Load a parser and validate its signature.

        Args:
            entry_point (str): Entry point for the parser.

        Returns:
            Callable[[PDFReader], Statement]: A validated parser function.
        """
        parser = load_parser(entry_point)
        if not callable(parser):
            raise ValueError(f"Parser at {entry_point} is not callable.")
        return parser

    def run_parser(
        self, parser: Callable[[PDFReader], Statement], reader: PDFReader
    ) -> Statement:
        """
        Run the parser and enforce return type.

        Args:
            parser (Callable[[PDFReader], Statement]): The parser function.
            reader (PDFReader): The PDFReader instance.

        Returns:
            Statement: The parsed statement data.
        """
        result = parser(reader)
        if not isinstance(result, Statement):
            raise TypeError(f"Parser did not return a Statement: {parser.__name__}")
        return result


class CSVRouter(BaseRouter):
    ENCODING = "utf-8-sig"

    def __init__(self, db_path: Path, fpath: Path):
        # Add parsing modules here as the project grows
        parsers = {
            "occuauto": parsecsv.occuauto.parse,
            "amazonper": parsecsv.amazonper.parse,
            "amazonbus": parsecsv.amazonbus.parse,
        }
        super().__init__(parsers)
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> Statement:
        """Opens the CSV file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            Statement: Statement contents in the dataclass
        """
        text = self.read_csv_as_text()
        array = self.read_csv_as_array()

        # Determine which parsing script to use
        stid, parser = select_parser(self.db_path, text, extension=".csv")
        statement = self.parse_switch(parser, array)

        # Validate and return statement data
        statement.stid = stid
        self.validate(statement, parser)
        return statement

    def read_csv_as_text(self) -> str:
        """Reads the CSV file and returns its contents as plain text."""
        with self.fpath.open("r", encoding=self.ENCODING) as f:
            text = f.read()
        return text

    def read_csv_as_array(self) -> list[list[str]]:
        """Reads the CSV file and returns its contents as a list of rows."""
        array = []
        with self.fpath.open("r", encoding=self.ENCODING) as f:
            reader = csv.reader(f)
            for row in reader:
                array.append(row)
        return array


class XLSXRouter(BaseRouter):
    def __init__(self, db_path: Path, fpath: Path):
        # Add parsing modules here as the project grows
        parsers = {"fedloan": parsexlsx.fedloan.parse}
        super().__init__(parsers)
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> Statement:
        """Opens the XLSX file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            Statement: Statement contents in the dataclass
        """
        sheets = self.read_xlsx()
        text = self.plain_text(sheets)
        stid, parser = select_parser(self.db_path, text, extension=".xlsx")
        statement = self.parse_switch(parser, sheets)

        # Validate and return statement data
        statement.stid = stid
        self.validate(statement, parser)
        return statement

    def plain_text(self, sheets) -> str:
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


# Definte routers for extensibility
ROUTERS = {
    ".pdf": PDFRouter,
    ".csv": CSVRouter,
    ".xlsx": XLSXRouter,
}


def parse(db_path: Path, fpath: Path) -> Statement:
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
