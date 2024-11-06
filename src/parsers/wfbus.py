# -*- coding: utf-8 -*-
import re
from datetime import datetime

from parsers.utils import (
    convert_amount_to_float,
    find_param_in_line,
    find_regex_in_line,
    get_absolute_date,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    Statement period activity summary   Account number: 5557133609
    """
    search_str = "Account number: "
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = rline.split()[0]
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range.
    The dates must be inferred from lines like these:
    August 24, 2021 - Page 1 of 5
    Beginning balance on 7/27
    Ending balance on 8/24
    """
    # Get the statement end year from the long format date
    wordy_date_pattern = r"[ADFJMNOS]\w*\s\d{1,2}\,\s\d{4}"
    _, _, wordy_date_str = find_regex_in_line(lines, wordy_date_pattern)
    wordy_date = datetime.strptime(wordy_date_str, r"%B %d, %Y")
    YYYY = wordy_date.year

    # Get the statement start and end dates in short format
    start_str = r"Beginning balance on \d{1,2}/\d{1,2}"
    end_str = r"Ending balance on \d{1,2}/\d{1,2}"
    _, _, start_pattern = find_regex_in_line(lines, start_str)
    _, _, end_pattern = find_regex_in_line(lines, end_str)
    start_date_str = start_pattern.split()[-1]
    end_date_str = end_pattern.split()[-1]

    # Convert to datetime assuming bonth have the same year
    date_format = r"%m/%d/%Y"
    start_date = datetime.strptime(start_date_str + "/" + str(YYYY), date_format)
    end_date = datetime.strptime(end_date_str + "/" + str(YYYY), date_format)

    # Correct the start_date year if there has been a rollover
    if start_date > end_date:
        start_date = datetime.strptime(
            start_date_str + "/" + str(YYYY - 1), date_format
        )

    date_range = [start_date, end_date]

    return date_range


def get_transaction_pages(lines: list[str]) -> list[list[str]]:
    """
    Returns only lines that contain transaction information.
    Note, the amounts are in a complex fixed-width column format that
    changes from page to page. Need to save the transaction lines
    as well as the column headers to parse them out later.
    """
    re_transaction = re.compile(r"^\s\s+\d{1,2}/\d{1,2}\s\s+")
    # re_columns = re.compile(r"^\s\s+Date\s+.*Description", re.IGNORECASE)
    columns = ["Date", "Description", "Credits", "Debits", "balance"]
    transaction_pages = []
    transaction_lines = []

    for line in lines:
        # Split the document by page of transactions
        if all([column in line.split() for column in columns]):
            # This is the column header for this page
            if len(transaction_lines) > 0:
                transaction_pages.append(transaction_lines)
            transaction_lines = [line]
            continue

        # Get the transations on this page
        if re.search(re_transaction, line):
            transaction_lines.append(line)
            continue

    # Append the last page of transactions
    if len(transaction_lines) > 0:
        transaction_pages.append(transaction_lines)

    return transaction_pages


def get_indices(
    header: str, column: str, buffer_left: int, buffer_right: int
) -> dict[str, int]:
    """
    Returns a dict representing the string index of column positions
    """
    indices = {
        "L": max(0, header.find(column) + buffer_left),
        "R": header.find(column) + len(column) + buffer_right,
    }
    return indices


def column_slices(header: str) -> dict[str, slice]:
    """
    Calculates the slice of each line representing each column.
    """
    # Define the settings used to measure position of the column names
    column_prop = {
        "Date": {"just": "L", "buffer_left": -2, "buffer_right": 2},
        "Number": {"just": "L", "buffer_left": -1, "buffer_right": 2},
        "Description": {"just": "L", "buffer_left": 0, "buffer_right": 0},
        "Credits": {"just": "L", "buffer_left": -4, "buffer_right": 1},
        "Debits": {"just": "L", "buffer_left": -2, "buffer_right": 2},
        "balance": {"just": "L", "buffer_left": -2, "buffer_right": 2},
    }

    # Deal with sometimes-vanishing check number column
    if "Number" not in header:
        column_prop.pop("Number")

    # Get the fixed-width positions of the column names
    name_indx = {}
    for col, props in column_prop.items():
        name_indx[col] = get_indices(
            header, col, props["buffer_left"], props["buffer_right"]
        )

    # Get the full-width column indices based on the column name indices
    columns = list(column_prop.keys())
    slices = {}
    for i, col in enumerate(columns):
        if column_prop[col]["just"] == "L":
            # Column spans left-most indices of current and next column names
            left = name_indx[col]["L"]
            if i == len(columns) - 1:
                right = -1
            else:
                right = name_indx[columns[i + 1]]["L"]
        else:
            # Column spans right-most indices of current and next column names
            right = name_indx[col]["R"]
            if i == 0:
                left = 0
            else:
                left = name_indx[columns[i - 1]]["R"]
        slices[col] = slice(left, right)
    return slices


def parse_transaction_page(page: list[str], date_range: list[datetime]) -> list[tuple]:
    """
    Parse an individual page of transactions.
    Each page has a fixed-width column format, but column widths change from page to
    page, so indices need to be updated dynamically.
    """
    header = page[0]
    lines = page[1:]

    # Get a dict containing slices for each column
    slices = column_slices(header)

    # Parse the lines
    transactions = []
    for line in lines:
        # Get the transaction date
        date_str = line[slices["Date"]].strip()
        date = get_absolute_date(date_str, date_range)
        date = date.strftime(r"%Y-%m-%d")

        # Get the description
        description = line[slices["Description"]]
        description = " ".join(description.split())
        description = re.sub(
            r"Recurring Payment authorized on \d{1,2}/\d{1,2} ", "", description
        )
        description = re.sub(
            r"Purchase authorized on \d{1,2}/\d{1,2} ", "", description
        )

        # Get the addition
        addn_str = line[slices["Credits"]].strip()
        addn = 0.0 if addn_str == "" else convert_amount_to_float(addn_str)

        # Get the subtraction
        subt_str = line[slices["Debits"]].strip()
        subt = 0.0 if subt_str == "" else convert_amount_to_float(subt_str)

        # Combine additions and subtraction
        amount = round(addn - subt, 2)

        # Get the EOD balance, if present on this line
        balance_str = line[slices["balance"]].strip()
        balance = "nan" if balance_str == "" else convert_amount_to_float(balance_str)

        # Build the transaction
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def backwards_fill_balance(transactions: list[tuple]) -> list[tuple]:
    """
    Backwards fill EOD balances so each transaction has a balance.
    Balance is third column in the tuple.
    (date, amount, balance, description)
    """
    # Deal with edge case first
    balance_final = transactions[-1][2]
    if balance_final == "nan":
        raise ValueError("Final transaction does not have a balance value.")

    # Backfill balance
    for row in reversed(range(len(transactions))):
        balance = transactions[row][2]
        if balance != "nan":
            # EOD balance
            continue
        amount_next = transactions[row + 1][1]
        balance_next = transactions[row + 1][2]
        balance = round(balance_next - amount_next, 2)
        transactions[row] = transactions[row][:2] + (balance,) + (transactions[row][3],)
    return transactions


def parse_transactions(
    date_range: list[datetime], transaction_pages: list[list[str]]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    # Define the columns and their justification
    transactions = []
    for page in transaction_pages:
        transactions.extend(parse_transaction_page(page, date_range))

    transactions = backwards_fill_balance(transactions)

    return transactions


def parse(lines_raw, lines):
    """
    Parse lines of Wells Fargo statement PDF to obtain structured transaction data
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    # No need for get_starting_balance()
    transaction_pages = get_transaction_pages(lines_raw)
    transactions = parse_transactions(date_range, transaction_pages)
    data = {account: transactions}
    return date_range, data
