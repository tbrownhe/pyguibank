from datetime import datetime

from core.utils import convert_amount_to_float


def get_account_number(array: list[list[str]]) -> str:
    """
    Retrieve the account number from the statement
    20220801 254779 31,928 202,208,010,000
    """
    columns = array[0]
    row = array[1]
    transaction_id = row[columns.index("Transaction ID")]
    account = transaction_id.split()[1]
    return account


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
    colnames = ["Posting Date", "Description", "Amount", "Balance"]
    col_indx = [columns.index(col) for col in colnames]

    date_format = r"%m/%d/%Y"
    for row in data:
        # Get the transaction date
        date_str = row[col_indx[0]]
        date = datetime.strptime(date_str, date_format)
        date = date.strftime(r"%Y-%m-%d")

        # Get the description
        description = row[col_indx[1]]

        # Get the amount
        amount_str = row[col_indx[2]]
        amount = convert_amount_to_float(amount_str)

        # Get the balance
        balance_str = row[col_indx[3]]
        balance = -convert_amount_to_float(balance_str)

        # Build the transaction
        transaction = (date, amount, balance, description)
        transactions.append(transaction)

    return transactions


def get_statement_dates(transactions: list[tuple]) -> list[datetime]:
    """
    Obtain the statement date range from the transaction list
    """
    date_list = [datetime.strptime(item[0], r"%Y-%m-%d") for item in transactions]
    start_date = min(date_list)
    end_date = max(date_list)
    date_range = [start_date, end_date]
    return date_range


def parse(array: list[list[str]]) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse lines of OCCU Credit Card statement PDF.
    """
    account = get_account_number(array)
    # No need for get_starting_balance()
    # No need for get_transaction_lines()
    transactions = parse_transactions(array)
    date_range = get_statement_dates(transactions)
    data = {account: transactions}
    return date_range, data
