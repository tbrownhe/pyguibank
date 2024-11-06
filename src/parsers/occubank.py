# -*- coding: utf-8 -*-
import re
from datetime import datetime

from parsers.utils import (
    convert_amount_to_float,
    find_line_re_search,
    find_param_in_line,
    get_absolute_date,
    remove_unimportant_words,
)


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    datelines looks like:
    FROM 02/01/16
    TO 02/29/16
    """
    # Declare the search pattern and dateformat
    _, from_line = find_line_re_search(lines, r"FROM \d{2}/\d{2}/\d{2}")
    _, to_line = find_line_re_search(lines, r"TO \d{2}/\d{2}/\d{2}")
    date_format = r"%m/%d/%y"

    # Parse the lines into datetime and return variable sdates
    start_date_str = from_line.split()[1]
    end_date_str = to_line.split()[1]
    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)
    date_range = [start_date, end_date]
    return date_range


def split_by_account(lines: list[str]) -> dict[str, list[str]]:
    """
    Retrieve account number(s) from statement.
    """
    i_sav, sav_line = find_param_in_line(lines, "PRIMARY SAVINGS")
    i_chk, chk_line = find_param_in_line(lines, "REMARKABLE CHECKING")
    i_loan, _ = find_param_in_line(lines, "PERSONAL CREDIT LINE")

    lines_sav = lines[i_sav:i_chk]
    lines_chk = lines[i_chk:i_loan] if i_loan else lines[i_chk:]

    account_sav = sav_line.split()[0]
    account_chk = chk_line.split()[0]

    account_dict = {account_sav: lines_sav, account_chk: lines_chk}

    return account_dict


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information
    """
    leading_date = re.compile(r"^\d{2}/\d{2}\s")
    transaction_list = []
    for line in lines:
        # Skip lines without a leading date
        if not re.search(leading_date, line):
            continue

        words = line.split()
        if "$" in words[-2] and "$" in words[-1]:
            # Normal transaction line
            transaction_list.append(line)
            continue

    return transaction_list


def parse_transactions(
    date_range: list[datetime], transaction_list: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    transactions = []
    for line in transaction_list:
        # Split the line into a list of words
        words = line.split()

        # The first item is the date
        date_str = words[0]
        date = get_absolute_date(date_str, date_range)
        date = date.strftime(r"%Y-%m-%d")

        # Amount and Balance are the -2 and -1 words in the line.
        amount = convert_amount_to_float(words[-2])
        balance = convert_amount_to_float(words[-1])

        # Remove pound sign if present
        if words[1] == "#":
            words.pop(1)

        # The description is everything in between
        description = " ".join(words[1:-2])
        description = remove_unimportant_words(description)

        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list]]:
    """
    Parse lines of OCCU statement PDF to obtain structured transaction data.
    """
    date_range = get_statement_dates(lines)
    account_dict = split_by_account(lines)
    data = {}
    for account, account_lines in reversed(account_dict.items()):
        transaction_lines = get_transaction_lines(account_lines)
        transactions = parse_transactions(date_range, transaction_lines)
        data[account] = transactions
    return date_range, data
