from datetime import datetime


def parse_transactions(array: list[list[str]]) -> list[tuple]:
    """
    Converts the raw transaction text into an organized list of transactions.
    """
    # Separate the columns and data
    columns = array[2]
    data = array[3:]

    # Select the columns to include in the transaction list
    colnames = [
        "Effective Date",
        "Loan Type",
        "Transaction Type",
        "Amount",
        "Balance",
    ]
    col_indx = [columns.index(col) for col in colnames]

    transactions = []
    for row in data:
        # Get the date, which is already a datetime object
        date = row[col_indx[0]]
        assert isinstance(date, datetime)
        date = date.strftime(r"%Y-%m-%d")

        # Get the description
        loan_type = row[col_indx[1]]
        tran_type = row[col_indx[2]]
        description = " ".join([loan_type, tran_type])

        # Get the amount
        amount = -float(row[col_indx[3]])

        # Get the balance
        balance = -float(row[col_indx[4]])

        # Assemble the transaction
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


def parse(
    sheets: dict[str, list[list]]
) -> tuple[list[datetime], dict[str, list[tuple]]]:
    """
    Parse FedLoan Servicing statement .xlsx
    """
    account = "FEDLOAN"
    array = sheets["Sheet 1"]
    transactions = parse_transactions(array)
    date_range = get_statement_dates(transactions)
    data = {account: transactions}
    return date_range, data
