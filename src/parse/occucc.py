# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta

from parse.utils import convert_amount_to_float, find_line_startswith, get_absolute_date


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    Account Number XXXX XXXX XXXX 3479 Page 1 of 4
    """
    search_str = "Account Number "
    _, line = find_line_startswith(lines, search_str)
    rline = line.split(search_str)[-1]
    account = "".join(rline.split()[:4])
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    Statement Closing Date 03/16/20 Late Payment Warning:
    Days in Billing Cycle 29 If we do not receive your minimum payment by the dat...
    """
    # Declare the search pattern and dateformat
    date_format = r"%m/%d/%y"
    close_str = "Statement Closing Date "
    ndays_str = "Days in Billing Cycle "
    _, close_line = find_line_startswith(lines, close_str)
    _, ndays_line = find_line_startswith(lines, ndays_str)

    close_line_r = close_line.split(close_str)[-1]
    ndays_line_r = ndays_line.split(ndays_str)[-1]
    end_date_str = close_line_r.split()[0]
    ndays_str = ndays_line_r.split()[0]
    ndays = int(ndays_str)

    end_date = datetime.strptime(end_date_str, date_format)
    start_date = end_date - timedelta(days=ndays - 1)

    date_range = [start_date, end_date]

    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Previous Balance 1,014.71
    """
    search_str = "Previous Balance "
    _, balance_line = find_line_startswith(lines, search_str)
    balance_line_r = balance_line.split(search_str)[-1]
    balance_str = balance_line_r.split()[0]
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

        transaction_lines.append(line)

    return transaction_lines


def parse_transactions(
    date_range: list[datetime], balance: float, transaction_lines: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    date_format = re.compile(r"\d{2}/\d{2}")
    transactions = []
    for line in transaction_lines:
        # Split the line into a list of words
        words = line.split()

        # The first item is the posted date
        # Second item is the transaction date if present
        # Remove the dates from words as we go
        if re.search(date_format, words[1]):
            date_str = words.pop(1)
            words.pop(0)
        else:
            date_str = words.pop(0)
        date = get_absolute_date(date_str, date_range)
        date = date.strftime(r"%Y-%m-%d")

        # The amount is the last item in the list
        amount_str = words[-1]
        amount = -convert_amount_to_float(amount_str)
        balance = round(balance + amount, 2)

        # Everything else is the description
        description = " ".join(words[:-1])

        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse lines of OCCU Credit Card statement PDF.
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    balance = get_starting_balance(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, balance, transaction_lines)
    data = {account: transactions}
    return date_range, data
