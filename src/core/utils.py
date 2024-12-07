import configparser
import hashlib
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pdfplumber


def read_config(config_path: Path):
    """
    Uses ConfigParser to get the contents of the config.ini file.
    """
    # Check to see if the config file exists
    if not config_path.exists:
        raise ValueError(
            "Please create and populate a config.txt file in the root directory."
        )

    # Open the config file
    config = configparser.ConfigParser()
    config.read(config_path)

    return config


def open_file_in_os(fpath: Path):
    try:
        name = os.name
        if name == "nt":
            args = ["start", "", str(fpath)]
            subprocess.run(args, shell=True, check=True)
        elif name == "posix":
            args = ["open", str(fpath)]
            subprocess.run(args, shell=False, check=True)
        else:
            raise ValueError("Unsupported OS type %s" % name)
    except Exception:
        print(f"{fpath} could not be opened. It may be open already.")


def find_line_startswith(lines: list[str], search_str: str, start=0) -> tuple[int, str]:
    """
    Uses str.startswith method to return the first line containing the search string.
    """
    for i, line in enumerate(lines[start:]):
        if line.startswith(search_str):
            return i + start, line
    raise ValueError("Parameter %s not found in lines." % search_str)


def find_regex_in_line(lines: list[str], search_str: str) -> tuple[int, str, str]:
    """
    Uses re.search method to return the first line containing the search string.
    Also returns the pattern match.
    """
    search_re = re.compile(search_str)
    for i, line in enumerate(lines):
        result = re.search(search_re, line)
        if result:
            return i, line, result[0]
    raise ValueError("Parameter %s not found in lines." % search_str)


def find_param_in_line(
    lines: list[str], search_str: str, start=0, case_sensitive=True
) -> tuple[int, str]:
    """
    Uses 'in' method to return the first line containing the search string.
    """
    if case_sensitive:
        for i, line in enumerate(lines[start:]):
            if search_str in line:
                return i + start, line
        raise ValueError("Parameter %s not found in lines." % search_str)
    else:
        for i, line in enumerate(lines[start:]):
            if search_str.lower() in line.lower():
                return i + start, line
        raise ValueError("Parameter %s not found in lines." % search_str)


def find_line_re_search(lines: list[str], search_str: str) -> tuple[int, str]:
    """
    Uses re.search to return the first line containing the search string.
    """
    regex = re.compile(search_str)
    for i, line in enumerate(lines):
        if re.search(regex, line):
            return i, line
    raise ValueError("Regex %s not found in lines." % search_str)


def get_absolute_date(mmdd: str, start_date: datetime, end_date: datetime) -> datetime:
    """
    Convert MM/DD date string to a full datetime object, accounting for year wraparounds.

    Args:
        mmdd (str): Date string in MM/DD format.
        start_date (datetime): Start date of the statement period.
        end_date (datetime): End date of the statement period.

    Returns:
        datetime: The full datetime object for the given MM/DD.
    """
    # Extract start and end years
    statement_days = (end_date - start_date).days
    possible_years = {
        start_date.year,
        start_date.year + 1,
        end_date.year,
        end_date.year - 1,
    }

    # Generate guesses for MM/DD with each possible year
    guesses = []
    for year in possible_years:
        try:
            guesses.append(datetime.strptime(f"{mmdd}/{year}", r"%m/%d/%Y"))
        except ValueError:
            # Probably guessed a leap day for a non-lear year
            continue

    # Find the guess closest to the statement period
    best_guess = min(
        guesses,
        key=lambda date: min(
            abs((date - start_date).days), abs((date - end_date).days)
        ),
    )

    # Ensure the guess is within a reasonable range
    if (
        abs((best_guess - start_date).days) <= statement_days
        or abs((best_guess - end_date).days) <= statement_days
    ):
        return best_guess

    raise ValueError(f"Could not resolve a valid date for MM/DD: {mmdd}")


def remove_stop_words(description: str, stop_words=None) -> str:
    """
    Remove spurious words from a description.

    Args:
        description (str): Input description string.
        stop_words (list[str]): List of words to remove (case-insensitive). Defaults to a predefined list.

    Returns:
        str: The cleaned description with stop words removed.
    """
    if stop_words is None:
        stop_words = {"purchase", "pos", "dbt", "recur-purch"}  # , "return"}

    # Filter out stop words
    clean_words = [
        word for word in description.split() if word.lower() not in stop_words
    ]
    return " ".join(clean_words)


def convert_amount_to_float(amount_str: str) -> float:
    """
    Parses USD amount strings of various formats into positive or negative float.
    $12.34   -> +12.34
    -$12.34  -> -12.34
    ($12.34) -> -12.34
    $12.34CR -> -12.34
    """
    # Remove commas, dollar signs, and spaces
    amount_str = amount_str.replace(",", "")
    amount_str = amount_str.replace("$", "")
    amount_str = amount_str.replace(" ", "")

    # Find whether the amount is negative
    parens = all([paren in amount_str for paren in ["(", ")"]])
    minus = "-" in amount_str
    credit = "CR" in amount_str
    negative = any([parens, minus, credit])

    # Remove negative indicators
    amount_str = amount_str.replace("(", "")
    amount_str = amount_str.replace(")", "")
    amount_str = amount_str.replace("-", "")
    amount_str = amount_str.replace("CR", "")

    # Get the final amount
    amount = float(amount_str)
    if negative:
        amount = -amount

    return amount


def hash_file(fpath: Path) -> str:
    """
    Hashes the byte contents of a file to compare to db values
    and prevent duplicate import.
    """
    with fpath.open("rb") as f:
        contents = f.read()
    md5hash = hashlib.md5(contents).hexdigest()
    return md5hash


class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.PDF = None
        self.pages = None
        self.text = None
        self.lines_raw = None
        self.lines = None

    def __enter__(self):
        """
        Open the PDF document using context manager.
        """
        self.PDF = pdfplumber.open(self.fpath)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the PDF document upon exiting the context.
        """
        if self.PDF:
            self.PDF.close()
            self.PDF = None

    def __del__(self):
        """
        Ensure the PDF document is closed when the object is deleted.
        """
        if self.PDF:
            self.PDF.close()

    def extract_text_simple(self) -> str:
        """Extracts text using a fast algoritm for all pages of the pdf.

        Raises:
            ValueError: Error while reading PDF

        Returns:
            str: Entire pdf extracted with simple algorithm

        Notes:
            Text is stored as self.text_simple
        """
        if self.PDF is None:
            raise ValueError("PDF not opened properly")
        self.text_simple = "\n".join(
            [page.extract_text_simple() or "" for page in self.PDF.pages]
        )
        return self.text_simple

    def extract_lines_simple(self) -> list[str]:
        """Extracts lines of whitespace-normalized text extracted via simple algoritm.

        Returns:
            list[str]: Lines of text with normalized whitespace

        Notes:
            Text is stored as self.text_simple
            Lines are stored as self.lines_simple
        """
        if self.pages is None:
            self.extract_text_simple()
        self.lines_simple = [
            " ".join(word for word in line.split())
            for line in self.text_simple.splitlines()
            if line.strip()
        ]
        return self.lines_simple

    def extract_layout_pages(self) -> list[str]:
        """Extracts all pages of text of the PDF using a slower layout-based algorithm.

        Raises:
            ValueError: Error while reading PDF

        Returns:
            list[str]: Pages of layout formatted text

        Notes:
            Pages of layout format text are stored as self.pages
        """
        if self.PDF is None:
            raise ValueError("PDF not opened properly")
        self.pages = [page.extract_text(layout=True) or "" for page in self.PDF.pages]
        return self.pages

    def extract_text(self) -> str:
        """Extracts pages carefully then joins them into a single string.

        Returns:
            str: Joined text in layout format

        Notes:
            Pages of layout format text are stored as self.pages
            Joined text is stored as self.text
        """
        if self.pages is None:
            self.extract_layout_pages()
        self.text = "\n".join(self.pages)
        return self.text

    def extract_lines_raw(self) -> list[str]:
        """Extracts non-empty lines of text while maintaining layout format.

        Returns:
            list[str]: Non-empty lines of text in layout format

        Notes:
            Pages of layout format text are stored as self.pages
            Joined text is stored as self.text
            Raw lines are stored as self.lines_raw
        """
        if self.text is None:
            self.extract_text()
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        return self.lines_raw

    def extract_lines_clean(self) -> list[str]:
        """Extracts lines of text with normalized whitespace.

        Returns:
            list[str]: Lines of text with normalized whitespace

        Notes:
            Pages of layout format text are stored as self.pages
            Joined text is stored as self.text
            Raw lines are stored as self.lines_raw
            Cleaned lines are stored as self.lines_clean
        """
        if self.lines_raw is None:
            self.extract_lines_raw()
        self.lines_clean = [" ".join(line.split()) for line in self.lines_raw]
        return self.lines_clean
