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
    600157 00000 Transphorm 401(k) Plan $NNNN.NN
    """
    search_str = r"––"
    _, line = find_param_in_line(lines, search_str)
    words = line.split()
    account = words[-1]
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range:
    Summary for July 1, 2021 - September 30, 2021 be allocated among investment
    """
    # Declare the search pattern and dateformat
    date_format = r"%m/%d/%Y"
    search_str = "ACCOUNT SUMMARY: "
    _, date_line = find_param_in_line(lines, search_str)
    parts = [part.strip() for part in date_line.split(":")[-1].split("-")]
    start_date_str = parts[0]
    end_date_str = parts[1]

    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)
    date_range = [start_date, end_date]

    return date_range


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information.
    """
    indx_0, _ = find_line_startswith(lines, "Your Account Summary")
    indx_1, _ = find_line_startswith(lines, "Your Investments")
    transaction_lines = lines[indx_0:indx_1]
    return transaction_lines


def parse_transactions(
    date_range: list[datetime], transaction_lines: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    entries = [
        "Beginning balance",
        "Employer contributions",
        "Market gain/loss",
        "Other transactions",
        "Ending balance",
    ]

    summary = {}
    for entry in entries:
        _, line = find_param_in_line(transaction_lines, entry)
        line = line.replace(entry, "")
        amount_str = line.split()[0]
        summary[entry] = convert_amount_to_float(amount_str)

    # Get the starting balance from the dict
    balance = summary["Beginning balance"]

    # Use the statement end date for all transactions
    date = date_range[-1].strftime(r"%Y-%m-%d")

    # Convert only relevant entries into transactions
    entries = [
        "Employer contributions",
        "Market gain/loss",
        "Other transactions",
    ]
    transactions = []
    for entry in entries:
        amount = summary[entry]

        # Skip transactions with amount = 0
        if amount == 0:
            continue

        balance = round(balance + amount, 2)
        description = entry
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse Transamerica 401k statement PDF.
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, transaction_lines)
    data = {account: transactions}
    return date_range, data
