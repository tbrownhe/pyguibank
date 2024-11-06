# -*- coding: utf-8 -*-
import re
from datetime import datetime

from parsers.utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement

    The line looks like this:
    Member Since 2020 Account number ending in: 6402 Customer Service 1-888-766-CIT...
    """
    search_str = "Account number ending in:"
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = rline.split()[0].strip()
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    dateline looks like:
    Billing Period: 02/04/21-03/03/21 TTY-hearing....
    """
    # Declare the search pattern and dateformat
    date_format = r"%m/%d/%y"
    _, dateline = find_line_startswith(lines, "Billing Period")

    parts = dateline.split()
    datespl = parts[2].split("-")
    start_date = datetime.strptime(datespl[0], date_format)
    end_date = datetime.strptime(datespl[1], date_format)
    date_range = [start_date, end_date]
    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Previous balance $1,014.71
    """
    search_str = "Previous balance "
    _, balance_line = find_param_in_line(lines, search_str)
    balance_line_r = balance_line.split(search_str)[-1]
    balance_str = balance_line_r.split()[0]
    balance = -convert_amount_to_float(balance_str)
    return balance


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information
    """
    # Get the indices of lines that start with a date.
    # These are each the first line of a transaction record.
    leading_date = re.compile(r"^\d{2}/\d{2}\s")
    transaction_indx = [
        i for i, line in enumerate(lines) if re.search(leading_date, line)
    ]

    transaction_lines = []
    for i in transaction_indx:
        # Get the first part of the transaction
        line = lines[i]

        # Deal with last transaction
        if i == transaction_indx[-1]:
            transaction_lines.append(line)
            continue

        if "$" in line:
            # Normal Transaction
            transaction_lines.append(line)
            continue

        # Lookahead for end of multi-line transactions
        k = 0
        while True:
            k += 1

            if k > 5:
                raise ValueError("Transaction end point not found: %s" % line)

            if i + k in transaction_indx:
                # The next line is a new transaction
                break

            # Get the next line
            next_line = lines[i + k]

            if "$" in line and "$" not in next_line:
                # We already found the end of the transaction
                break

            if "Foreign Fee" in line:
                break

            # Append the next line to the transaction line and continue
            line = " ".join([line, next_line])

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

        # The first item is the date
        date_str = words.pop(0)
        date = get_absolute_date(date_str, date_range)
        date = date.strftime(r"%Y-%m-%d")

        # Skip the second date if there is one
        if re.search(date_format, words[0]):
            words.pop(0)

        # Get the word containing the transaction amount
        i_amount, amount_str = [
            (i, word) for i, word in enumerate(words) if "$" in word
        ][-1]
        amount = -convert_amount_to_float(amount_str)

        # Compute the balance after this transaction
        balance = round(balance + amount, 2)

        # Assemble the description.
        # Warning: Sometimes there is spurious text after the amount.
        description = " ".join(words[:i_amount])

        # Build the transaction list
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list]]:
    """
    Parse lines of CITIstatement PDF to obtain structured transaction data
    """
    # Get the statement dates, starting balance, and raw transaction lines
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    balance = get_starting_balance(lines)
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, balance, transaction_lines)
    data = {account: transactions}
    return date_range, data
