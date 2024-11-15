import configparser
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path


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
