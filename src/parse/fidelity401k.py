# -*- coding: utf-8 -*-
from datetime import datetime

from parse.utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    First line that contains the word 401(k)
    """
    search_str = " 401(k) "
    _, line = find_param_in_line(lines, search_str)
    return line


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    Market Value of Your Account Statement Period: 09/01/2019 to 09/30/2019
    """
    # Declare the search pattern and dateformat
    search_str = "Statement Period: "
    date_format = r"%m/%d/%Y"

    _, date_line = find_param_in_line(lines, search_str)
    date_line_r = date_line.split(search_str)[-1]

    date_strs = [word for word in date_line_r.split() if "/" in word]
    start_date = datetime.strptime(date_strs[0], date_format)
    end_date = datetime.strptime(date_strs[1], date_format)
    date_range = [start_date, end_date]

    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Beginning Balance $20,454.08
    """
    search_str = "Beginning Balance "
    _, balance_line = find_line_startswith(lines, search_str)
    balance_str = balance_line.split(search_str)[-1].strip()
    balance = convert_amount_to_float(balance_str)
    return balance


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information.
    There are only two that matter for this statement type.
    """
    transaction_lines = []
    search_strs = [
        "Your Contributions",
        "Employer Contributions",
        "Exchange In",
        "Exchange Out",
        "Change in Market Value",
    ]
    for search_str in search_strs:
        try:
            _, line = find_line_startswith(lines, search_str)
        except Exception:
            continue
        transaction_lines.append(line)
    return transaction_lines


def parse_transactions(
    date_range: list[datetime], balance: float, transaction_lines: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    date = date_range[1].strftime(r"%Y-%m-%d")

    transactions = []
    for line in transaction_lines:
        # Split the line into a list of words
        words = line.split()

        description = " ".join(words[:-1])

        amount_str = words[-1]
        amount = convert_amount_to_float(amount_str)
        balance = round(balance + amount, 2)

        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines):
    """
    Parse lines of Fidelity 401k PDF
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    balance = get_starting_balance(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, balance, transaction_lines)
    data = {account: transactions}
    return date_range, data
