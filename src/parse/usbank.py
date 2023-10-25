# -*- coding: utf-8 -*-
import re
from datetime import datetime

from parse.utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement

    The line looks like this:
    Open Date: 12/24/2014 Closing Date: 01/23/2015 Account: nnnn nnnn nnnn nnnn
    """
    search_str = "Account: "
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = "".join(rline.split())
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    dateline looks like:
    Open Date: 12/24/2014    Closing Date: 01/23/2015
    """
    date_format = r"%m/%d/%Y"
    open_str = r"Open Date: "
    close_str = r"Closing Date: "

    _, date_line = find_line_startswith(lines, open_str)
    parts = date_line.split(open_str)
    start_date_str = parts[1].split()[0]
    parts = date_line.split(close_str)
    end_date_str = parts[1].split()[0]

    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)
    date_range = [start_date, end_date]
    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Minimum Payment Due $103.00 Previous Balance + $3,123.84
    """
    _, balance_line = find_param_in_line(lines, "Previous Balance ")
    balance_str = [word for word in balance_line.split() if "$" in word][-1]
    balance = -convert_amount_to_float(balance_str)
    return balance


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information
    """
    leading_date = re.compile(r"^\d{2}/\d{2}\s")
    transaction_lines = []
    for i, line in enumerate(lines):
        # Skip lines without a leading date
        if not re.search(leading_date, line):
            continue

        if "$" in line:
            # Normal transaction line
            transaction_lines.append(line)
            continue

    return transaction_lines


def parse_transactions(
    date_range: list[datetime], balance: float, transaction_list: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    date_format = re.compile(r"\d{2}/\d{2}")
    transactions = []
    for line in transaction_list:
        # Split the line into a list of words
        words = line.split()

        # The first item is the posted date
        # The second item should be the transaction date
        # Remove the dates from the list of words as we go
        if re.search(date_format, words[1]):
            date = get_absolute_date(words.pop(1), date_range)
            words.pop(0)
        else:
            date = get_absolute_date(words.pop(0), date_range)
        date = date.strftime(r"%Y-%m-%d")

        # Delete intermittent transaction reference number
        if words[0].isdigit() and len(words[0]) == 4:
            words.pop(0)

        # Amount is always the last word
        amount = -convert_amount_to_float(words[-1])
        balance = round(balance + amount, 2)

        # Description is everything in between dates and amount.
        description = " ".join(words[0:-1])

        # Combine them all into a list of lists called transactions
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines):
    """
    Parse lines of US Bank statement PDF to obtain structured transaction data
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    balance = get_starting_balance(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, balance, transaction_lines)
    data = {account: transactions}
    return date_range, data
