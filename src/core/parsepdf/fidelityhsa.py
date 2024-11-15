from datetime import datetime

from ..core.utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    find_regex_in_line,
)


def get_account_number(lines: list[str]) -> str:
    """
    Retrieve the account  number from the statement
    Envelope #aksdjfhaklsdjfh Account Number: NNN-NNNNNN
    """
    search_str = "Account Number: "
    _, line = find_param_in_line(lines, search_str)
    rline = line.split(search_str)[-1]
    account = rline.split()[0]
    return account


def get_statement_dates(lines: list[str]) -> list[datetime]:
    """
    Parse the lines into datetime and return variable date_range
    December 1, 2021 - December 31, 2021
    """
    # Declare the search pattern and dateformat
    date_format = r"%B %d, %Y"
    wordy_date_pattern = r"[ADFJMNOS]\w*\s\d{1,2}\,\s\d{4}\s-\s"
    _, date_line, _ = find_regex_in_line(lines, wordy_date_pattern)
    date_strs = [word.strip() for word in date_line.split("-")]

    start_date = datetime.strptime(date_strs[0], date_format)
    end_date = datetime.strptime(date_strs[1], date_format)

    date_range = [start_date, end_date]

    return date_range


def get_starting_balance(lines: list[str]) -> float:
    """
    Get the starting balance, which looks like:
    Beginning Account Value $7,531.16 $6,607.91
    """
    search_str = "Beginning Account Value "
    _, balance_line = find_line_startswith(lines, search_str)
    balance_line = balance_line.replace("-", "0")
    balance_line_r = balance_line.split(search_str)[-1]
    balance_str = balance_line_r.split()[0]
    balance = convert_amount_to_float(balance_str)
    return balance


def parse_transactions(
    date_range: list[datetime], balance: float, lines: list[str]
) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    Note that dashes indicate zero for this period. Second value is for YTD.
    Additions - 900.00
    Subtractions - -471.10
    Change in Investment Value * 224.30 718.65
    """
    date = date_range[-1].strftime(r"%Y-%m-%d")

    search_strs = ["Additions", "Subtractions", "Change in Investment Value"]
    transactions = []
    for search_str in search_strs:
        # Get the line and convert the value for this month to an amount
        try:
            _, line = find_line_startswith(lines, search_str)
        except Exception:
            continue
        line = line.replace(" - ", " 0.00 ").replace("*", "")
        line_r = line.split(search_str)[-1]
        amount_str = line_r.split()[0]
        amount = convert_amount_to_float(amount_str)

        # Skip this transaction if the amount is zero
        if amount == 0:
            continue

        balance = round(balance + amount, 2)
        description = search_str

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
    # Skip get_transaction_lines() and go directly to parsing
    transactions = parse_transactions(date_range, balance, lines)
    data = {account: transactions}
    return date_range, data
