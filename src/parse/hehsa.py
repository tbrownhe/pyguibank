# -*- coding: utf-8 -*-
import re
from datetime import datetime
from parse.utils import (
    find_param_in_line,
    find_regex_in_line,
    find_line_startswith,
    convert_amount_to_float,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    firstname lastname Account Number: NNNNNNN
    """
    search_str = "Account Number: "
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = rline.split()[0]
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    Address information Period: 12/01/18 through 12/31/18
    """
    # Declare the search pattern and dateformat
    date_format = r"%m/%d/%y"
    date_pattern = r"Period: \d{2}/\d{2}/\d{2}"
    _, date_line, _ = find_regex_in_line(lines, date_pattern)
    date_line_r = date_line.split("Period:")[-1]
    date_strs = date_line_r.split("through")
    start_date_str = date_strs[0].strip()
    end_date_str = date_strs[1].strip()

    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)

    date_range = [start_date, end_date]

    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Beginning Balance $ 2,070.06
    """
    search_str = "Beginning Balance "
    _, balance_line = find_line_startswith(lines, search_str)
    balance_str = balance_line.split(search_str)[-1]
    balance = convert_amount_to_float(balance_str)
    return balance


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information
    """
    leading_date = re.compile(r"^\d{2}/\d{2}/\d{4}\s")
    transaction_lines = []
    for line in lines:
        # Skip lines without a leading date
        if not re.search(leading_date, line):
            continue

        transaction_lines.append(line)

    return transaction_lines


def parse_transactions(balance: float, transaction_lines: list[str]) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    date_format = r"%m/%d/%Y"
    transactions = []
    for line in transaction_lines:
        # Split the line into a list of words
        words = line.split()

        # Get the date
        date_str = words[0]
        date = datetime.strptime(date_str, date_format)
        date = date.strftime(r"%Y-%m-%d")

        # Get the amount and balance
        amount_str = words[-2]
        balance_str = words[-1]
        amount = convert_amount_to_float(amount_str)
        balance = convert_amount_to_float(balance_str)

        # Get the description
        description = " ".join(words[1:-2])
        if description == "":
            description = "Interest"

        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse lines of Fidelity HSA PDF.
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    balance = get_starting_balance(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(balance, transaction_lines)
    data = {account: transactions}
    return date_range, data
