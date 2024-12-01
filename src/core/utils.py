import configparser
import hashlib
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pdfplumber
from loguru import logger

# import pdftotext


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


def find_line_startswith(lines: list[str], search_str: str) -> tuple[int, str]:
    """
    Uses str.startswith method to return the first line containing the search string.
    """
    for i, line in enumerate(lines):
        if line.startswith(search_str):
            return i, line
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
    lines: list[str], search_str: str, case_sensitive=True
) -> tuple[int, str]:
    """
    Uses 'in' method to return the first line containing the search string.
    """
    if case_sensitive:
        for i, line in enumerate(lines):
            if search_str in line:
                return i, line
        raise ValueError("Parameter %s not found in lines." % search_str)
    else:
        for i, line in enumerate(lines):
            if search_str.lower() in line.lower():
                return i, line
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


def hash_transactions(transactions: list[tuple]) -> list[tuple]:
    """
    Appends the MD5 hash of the transaction contents to the last element of each row.
    This statement is only called for transactions within one statement.
    Assume statements do not contain duplicate transactions.
    If a duplicate md5 is found, modify the description and rehash.
    Description is always the last item in the row.

    transactions = (account_id, date, amount, balance, description)
    """
    md5_list = []
    hashed_transactions = []
    for row in transactions:
        md5 = hashlib.md5(str(row).encode()).hexdigest()
        while md5 in md5_list:
            logger.debug("Modifying description to ensure unique hash.")
            description = row[-1] + " "
            row = row[:-1] + (description,)
            md5 = hashlib.md5(str(row).encode()).hexdigest()
        md5_list.append(md5)
        hashed_transactions.append(row + (md5,))
    return hashed_transactions


def hash_file(fpath: Path) -> str:
    """
    Hashes the byte contents of a file to compare to db values
    and prevent duplicate import.
    """
    with fpath.open("rb") as f:
        contents = f.read()
    md5hash = hashlib.md5(contents).hexdigest()
    return md5hash


def standardize_fname(fpath: Path, parser: str, date_range) -> str:
    """
    Creates consistent fname
    """
    new_fname = (
        "_".join(
            [
                parser,
                date_range[0].strftime(r"%Y%m%d"),
                date_range[1].strftime(r"%Y%m%d"),
            ]
        )
        + fpath.suffix.lower()
    )
    return new_fname


class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.doc = None
        self.text = None
        self.lines_raw = None
        self.lines = None

    def __enter__(self):
        """
        Open the PDF document using context manager.
        """
        self.doc = pdfplumber.open(self.fpath)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the PDF document upon exiting the context.
        """
        if self.doc:
            self.doc.close()
            self.doc = None

    def __del__(self):
        """
        Ensure the PDF document is closed when the object is deleted.
        """
        if self.doc:
            self.doc.close()

    def extract_text(self) -> str:
        if self.doc is None:
            raise ValueError("PDF not opened properly")
        self.text = "\n".join(
            [page.extract_text_simple() or "" for page in self.doc.pages]
        )
        return self.text

    def remove_empty_lines(self) -> list[str]:
        if self.text is None:
            self.extract_text()
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        return self.lines_raw

    def remove_white_space(self) -> list[str]:
        if self.lines_raw is None:
            self.remove_empty_lines()
        self.lines = [" ".join(line.split()) for line in self.lines_raw]
        return self.lines


"""
class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.text = None
        self.lines_raw = None
        self.lines = None
        self.read_pdf()

    def read_pdf(self):
        with self.fpath.open("rb") as f:
            self.doc = pdftotext.PDF(f, physical=True)
        self.text = "\n".join(self.doc)
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        self.lines = [" ".join(line.split()) for line in self.lines_raw]
"""
