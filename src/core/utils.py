import configparser
import hashlib
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from loguru import logger


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


def get_absolute_date(MMDD: str, date_range: list[datetime]) -> datetime:
    """
    Convert MM/DD date string like 02/23 to datetime.
    Correct for year wraparound like 12/29, 12/31, 01/01
    """
    MM = MMDD.split("/")[0]
    start_year = date_range[0].year
    end_year = date_range[1].year
    if int(MM) == 1 and end_year > start_year:
        MMDDYYYY = MMDD + "/" + str(end_year)
    else:
        MMDDYYYY = MMDD + "/" + str(start_year)
    date = datetime.strptime(MMDDYYYY, r"%m/%d/%Y")
    return date


def remove_unimportant_words(description: str) -> str:
    """
    Delete spurious words from Descriptions
    """
    rm_words = ["purchase", "pos", "dbt", "recur-purch", "return"]
    clean_words = [word for word in description.split() if word.lower() not in rm_words]
    clean_desc = " ".join(clean_words)
    return clean_desc


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
