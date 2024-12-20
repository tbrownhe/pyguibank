from datetime import datetime
from pathlib import Path
from typing import Union

# from .db import execute_sql_query
from ..utils import convert_amount_to_float


def get_card_id(payment_instrument: str) -> Union[int, None]:
    """
    Retrieves a CardID based on the Payment Instrument Type:
        =7083
        =9525
    """
    if payment_instrument.strip() == "":
        return None

    # Get the presumed last four of the credit card used.
    last_four = payment_instrument.replace("=", "").replace('"', "")

    # Look up the AccountID for this AccountNumber
    # Note: AccountNumber is forced unique by db.
    db_path = Path("") / "pyguibank.db"
    query = "SELECT CardID FROM Cards WHERE LastFour = '%s'" % last_four
    result, _ = execute_sql_query(db_path, query)
    if len(result) == 0:
        raise ValueError(
            "LastFour = '%s' does not exist in the Cards table." % last_four
        )
    else:
        return result[0][0]


def parse_transactions(array: list[list[str]]) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    transactions = []

    # Return early if there are no transactions
    if len(array) <= 1:
        return transactions

    # Separate columns from data
    columns = array[0]
    data = array[1:]

    # Get the column indices of the relevant columns
    colnames = [
        "Payment Identifier",
        "Order ID",
        "Order Date",
        "Item Net Total",
        "Manufacturer",
        "Commodity",
        "Title",
    ]
    col_indx = [columns.index(col) for col in colnames]

    date_format = r"%m/%d/%Y"
    for row in data:
        # Get the payment account
        account_str = row[col_indx[0]]
        card_id = get_card_id(account_str)

        # Get the Order ID
        order_id = row[col_indx[1]]

        # Get the transaction date
        date_str = row[col_indx[2]]
        date = datetime.strptime(date_str, date_format)
        date = date.strftime(r"%Y-%m-%d")

        # Get the amount
        amount_str = row[col_indx[3]]
        amount = -convert_amount_to_float(amount_str)

        # Get the description
        seller = row[col_indx[4]].title()
        category = row[col_indx[5]].replace("_", " ").title()
        title = row[col_indx[6]]
        description = " ".join([seller, category, title])

        # Build the transaction
        transaction = (card_id, order_id, date, amount, description)
        transactions.append(transaction)

    return transactions


def get_statement_dates(transactions: list[tuple]) -> list[datetime]:
    """
    Obtain the statement date range from the transaction list
    """
    date_list = [datetime.strptime(item[2], r"%Y-%m-%d") for item in transactions]
    start_date = min(date_list)
    end_date = max(date_list)
    date_range = [start_date, end_date]
    return date_range


def parse(array: list[list[str]]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse lines of OCCU Credit Card statement PDF.
    """
    account = "amazonbus"
    transactions = parse_transactions(array)
    date_range = get_statement_dates(transactions)
    data = {account: transactions}
    return date_range, data
