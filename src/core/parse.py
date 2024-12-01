import csv
import importlib
import re
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

import openpyxl
from loguru import logger

from .interfaces import IParser
from .query import statement_types
from .utils import PDFReader
from .validation import Statement, StatementValidationError, validate_statement

T = TypeVar("T")


class BaseRouter(Generic[T]):
    """Provides parser routing logic common to all parsers.

    Args:
        Generic (T): T adopts the type passed to it when a child class inherits this class
    """

    def __init__(self, fpath: Path, hard_fail=True):
        self.fpath = fpath
        self.hard_fail = hard_fail

    def select_parser(self, db_path: Path, text: str, extension="") -> tuple[int, str]:
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
            assert isinstance(pattern, str)
            if all(
                re.search(re.escape(search_str), text_lower)
                for search_str in pattern.lower().split("&&")
            ):
                assert isinstance(stid, int)
                assert isinstance(entry_point, str)
                return stid, entry_point
        logger.error(
            "Statement type not recognized. Update StatementTypes and parsing scripts."
        )
        raise ValueError("Statement type not recognized.")

    def extract_statement(
        self, stid: int, entry_point: str, input_data: T
    ) -> Statement:
        # Dynamically load the parser and use it to extract the statement data
        parser = self.load_parser(entry_point)
        statement = self.run_parser(parser, input_data)

        # Attach additional metadata
        statement.fpath = self.fpath
        statement.stid = stid

        # Validate and return statement data
        self.validate_statement(statement, parser)
        return statement

    def load_parser(self, entry_point: str) -> Callable[[T], Statement]:
        """
        Load a parser dynamically and validate its signature.

        Args:
            entry_point (str): Entry point for the parser.

        Returns:
            Callable[[T], Statement]: A validated parser function.
        """
        if ":" not in entry_point:
            raise ValueError(f"Invalid entry point format: {entry_point}")

        module_name, func_name = entry_point.split(":")
        if module_name.startswith("."):
            # Treat as relative import
            package = __name__.rsplit(".", 1)[0]
            module_name = package + module_name

        try:
            module = importlib.import_module(module_name)
            parser = getattr(module, func_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not load parser {entry_point}: {e}") from e

        if not callable(parser):
            raise ValueError(f"Parser at {entry_point} is not callable.")

        if not isinstance(parser, IParser):
            raise TypeError(f"{parser} must implement IParser")

        return parser

    def run_parser(self, parser: IParser, input_data: T) -> Statement:
        """
        Run the parser and enforce return type.

        Args:
            parser (IParser): The parser class that must conform to IParser.
            input_data (T): Input data (e.g., PDFReader, CSV array, etc.).

        Returns:
            Statement: The parsed statement data.
        """
        result = parser().parse(input_data)
        if not isinstance(result, Statement):
            raise TypeError(
                f"{parser.__name__} did not return a Statement. Check its parse() method."
            )
        return result

    def validate_statement(self, statement: Statement, parser: str) -> None:
        try:
            validate_statement(statement, self.hard_fail)
        except StatementValidationError as e:
            logger.error(
                f"Validation failed for statement imported using"
                f" parser '{parser}': {e}"
            )
            raise


class PDFRouter(BaseRouter[PDFReader]):
    """_summary_

    Args:
        BaseRouter (PDFReader): _description_
    """

    def __init__(self, db_path: Path, fpath: Path, **kwargs):
        super().__init__(fpath, **kwargs)
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> Statement:
        """Opens the PDF file, determines its type, and routes its reader
        to the appropriate parsing module.

        Returns:
            Statement: Statement contents in the dataclass
        """
        with PDFReader(self.fpath) as reader:
            text = reader.extract_text()
            stid, entry_point = self.select_parser(self.db_path, text, extension=".pdf")
            statement = self.extract_statement(stid, entry_point, reader)
        return statement


class CSVRouter(BaseRouter[list[list[str]]]):
    ENCODING = "utf-8-sig"

    def __init__(self, db_path: Path, fpath: Path, **kwargs):
        super().__init__(fpath, **kwargs)
        self.db_path = db_path
        self.fpath = fpath

    def parse(self) -> Statement:
        """Opens the CSV file, determines its type, and routes its contents
        to the appropriate parsing script.

        Returns:
            Statement: Statement contents in the dataclass
        """
        # Get the raw data from the csv
        text = self.read_csv_as_text()
        array = self.read_csv_as_array()

        # Extract the statement data
        stid, entry_point = self.select_parser(self.db_path, text, extension=".csv")
        statement = self.extract_statement(stid, entry_point, array)
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
    def __init__(self, db_path: Path, fpath: Path, **kwargs):
        super().__init__(fpath, **kwargs)
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
        stid, entry_point = self.select_parser(self.db_path, text, extension=".xlsx")
        statement = self.extract_statement(stid, entry_point, sheets)
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


### Router registration framework
ROUTERS: dict[str, type[BaseRouter]] = {}


def register_router(extension: str, router_class: type[BaseRouter]):
    ROUTERS[extension] = router_class


register_router(".pdf", PDFRouter)
register_router(".csv", CSVRouter)
register_router(".xlsx", XLSXRouter)


def parse_any(db_path: Path, fpath: Path, **kwargs) -> Statement:
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
        router = ROUTERS[suffix](db_path, fpath, **kwargs)
        return router.parse()
    raise ValueError(f"Unsupported file extension: {suffix}")
