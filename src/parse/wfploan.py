# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta
from typing import Union
from parse.utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    Account Number NNNNNNNNNNNN
    """
    search_str = "Account Number "
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = rline.split()[0].strip()
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    dateline looks like:
    PO BOX 5169 Statement Date 03/29/22
    There is no statement start date listed. Use end_date - 30days
    """
    # Declare the search pattern and dateformat
    date_format = r"%m/%d/%y"
    search_str = "Statement Date "
    _, date_line = find_param_in_line(lines, search_str)

    date_line_r = date_line.split(search_str)[-1]
    date_str = date_line_r.split()[0]
    end_date = datetime.strptime(date_str, date_format)
    start_date = end_date - timedelta(days=30)
    date_range = [start_date, end_date]
    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Prior Principal Balance $21,000.00
    """
    search_str = "Prior Principal Balance "
    _, balance_line = find_line_startswith(lines, search_str)
    balance_line_r = balance_line.split(search_str)[-1]
    balance_str = balance_line_r.split()[0]
    balance = -convert_amount_to_float(balance_str)
    return balance


def get_transaction_lines(lines: list[str]) -> Union[list[str], None]:
    """
    Returns only lines that contain transaction information
    """
    leading_date = re.compile(r"^\d{2}/\d{2}/\d{2}\s")
    transaction_lines = []
    for line in lines:
        if "No transactions within this billing cycle" in line:
            return None

        # Skip lines without leading date
        if not re.search(leading_date, line):
            continue

        # Skip the ending balance line
        if "Ending Principal Balance" in line:
            continue

        if "$" in line:
            # Normal Transaction
            transaction_lines.append(line)
            continue

    return transaction_lines


def parse_transactions(
    date_range: list[datetime],
    balance: float,
    transaction_lines: Union[list[str], None],
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    The format of the loan statement splits the total payment into
    principle payment and interest payment, instead of simple listing
    the total payment as positive and the interest fee as negative.
    Correct this.
        Prior Principal Balance $21,000.00
        03/18/22 INTEREST PAYMENT $271.88
        03/18/22 PRINCIPAL PAYMENT $416.02
        03/29/22 Ending Principal Balance $20,583.98*
    """
    # Deal with statements with no transactions
    if transaction_lines is None:
        return []

    # Uniquely identify the lines
    if len(transaction_lines) > 2:
        raise ValueError("More than two transaction lines found.")
    _, interest_line = find_param_in_line(transaction_lines, "INTEREST PAYMENT")
    _, principle_line = find_param_in_line(transaction_lines, "PRINCIPAL PAYMENT")

    # Get the payment date
    date_str = interest_line.split()[0]
    date = datetime.strptime(date_str, r"%m/%d/%y")
    date = date.strftime(r"%Y-%m-%d")

    # Parse the amounts
    interest_str = interest_line.split()[-1]
    principle_str = principle_line.split()[-1]
    interest = convert_amount_to_float(interest_str)
    principle = convert_amount_to_float(principle_str)

    # Get the total payment and interest fee
    payment = principle + interest
    fee = -interest

    # Build the transactions
    balance += fee
    description = "INTEREST FEE"
    fee_transaction = (date, fee, balance, description)
    balance += payment
    description = "MONTHLY PAYMENT"
    pay_transaction = (date, payment, balance, description)

    transactions = [fee_transaction, pay_transaction]
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
