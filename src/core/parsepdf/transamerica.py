from datetime import datetime

from ..utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    find_regex_in_line,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    600157 00000 Transphorm 401(k) Plan $NNNN.NN
    """
    search_str = " 401(k) Plan "
    _, line = find_param_in_line(lines, search_str, case_sensitive=False)
    words = line.split()
    account = words[0]
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range:
    Summary for July 1, 2021 - September 30, 2021 be allocated among investment
    """
    # Declare the search pattern and dateformat
    date_format = r"%B %d, %Y"
    wordy_date_pattern = r"Summary for [ADFJMNOS]\w*\s\d{1,2}\,\s\d{4}"
    _, date_line, _ = find_regex_in_line(lines, wordy_date_pattern)
    parts = date_line.split(" - ")
    start_date_str = " ".join(parts[0].split()[-3:])
    end_date_str = " ".join(parts[1].split()[:3])

    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)
    date_range = [start_date, end_date]

    return date_range


def get_transaction_lines(lines: list[str]) -> list[str]:
    """
    Returns only lines that contain transaction information.
    """
    _, line = find_line_startswith(lines, "Totals ")
    transaction_lines = [line]
    return transaction_lines


def parse_transactions(
    date_range: list[datetime], transaction_lines: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    Fund Balance Money In Money Out Transfers Credits/Fees Gain/Loss Balance Units
    Totals $573.67 $980.52 $0.00 $0.00 -$0.77 -$18.58 $1,534.84 100%
    """
    # Parse out the single compressed row of transaction data
    line = transaction_lines[0]
    words = line.split()
    all_columns = [
        "Stocks",
        "Beginning Balance",
        "Contributions",
        "Withdrawals",
        "Transfers",
        "Credits and Fees",
        "Change in Market Value",
        "Ending Balance",
        "Allocation",
    ]
    summary = {}
    for i, col in enumerate(all_columns):
        summary[col] = words[i]

    # Get the starting balance from the dict
    balance = convert_amount_to_float(summary["Beginning Balance"])

    # Use the statement end date for all transactions
    date = date_range[-1].strftime(r"%Y-%m-%d")

    # Convert only relevant entries into transactions
    columns = [
        "Contributions",
        "Withdrawals",
        "Transfers",
        "Credits and Fees",
        "Change in Market Value",
    ]
    transactions = []
    for col in columns:
        amount = convert_amount_to_float(summary[col])

        # Skip transactions with amount = 0
        if amount == 0:
            continue

        balance = round(balance + amount, 2)
        description = col
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def parse(lines: list[str]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse Transamerica 401k statement PDF.
    """
    account = get_account_number(lines)
    date_range = get_statement_dates(lines)
    # Skip get_balance(), we get it for free in parse_transactions()
    transaction_lines = get_transaction_lines(lines)
    transactions = parse_transactions(date_range, transaction_lines)
    data = {account: transactions}
    return date_range, data
