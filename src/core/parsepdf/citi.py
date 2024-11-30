import re
from datetime import datetime

from loguru import logger

from ..utils import (
    PDFReader,
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)
from ..validation import Account, Statement, Transaction


class CitiParser:
    HEADER_DATE = r"%m/%d/%y"
    LEADING_DATE = re.compile(r"^\d{2}/\d{2}\s")
    TRANSACTION_DATE = re.compile(r"\d{2}/\d{2}")
    AMOUNT = re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

    def __init__(self, reader: PDFReader):
        reader.remove_white_space()
        self.reader = reader

    def parse(self) -> Statement:
        """
        Main entry point to parse the statement.
        """
        logger.trace("Parsing Citi statement")
        statement = self.extract_statement()
        return statement

    def extract_statement(self) -> Statement:
        self.get_statement_dates()
        accounts = self.extract_accounts()
        return Statement(
            start_date=self.start_date, end_date=self.end_date, accounts=accounts
        )

    def get_statement_dates(self) -> tuple[datetime, datetime]:
        """
        Extract the start and end dates from the statement.
        `Billing Period:12/04/20-01/05/21 TTY-hearing-impaired services..`
        """
        _, dateline = find_line_startswith(self.reader.lines, "Billing Period:")
        parts = dateline.split(":")[1].split()[0]
        self.start_date, self.end_date = [
            datetime.strptime(date, self.HEADER_DATE) for date in parts.split("-")
        ]

    def extract_accounts(self) -> list[Account]:
        """One account per Citi statement"""
        return [self.extract_account()]

    def extract_account(self) -> Account:
        """Extract account level data"""
        account_num = self.get_account_number()
        self.get_statement_balances()
        transaction_lines = self.get_transaction_lines()
        transactions = self.parse_transaction_lines(transaction_lines)
        return Account(
            account_num=account_num,
            start_balance=self.start_balance,
            end_balance=self.end_balance,
            transactions=transactions,
        )

    def get_account_number(self) -> str:
        """
        Retrieve the account number from the statement.
        """
        search_str = "Account number ending in:"
        _, line = find_param_in_line(self.reader.lines, search_str)
        account_num = line.split(search_str)[-1].split()[0].strip()
        return account_num

    def get_statement_balances(self) -> None:
        """
        Extract the starting balance from the statement.
        `Previous balance $0.00`
        `New balance as of 01/05/21: $123.45
        """
        patterns = ["Previous balance ", "New balance "]
        balances = []

        for pattern in patterns:
            try:
                _, balance_line = find_param_in_line(self.reader.lines, pattern)
                balance_str = balance_line.split()[-1]
                balance = -convert_amount_to_float(balance_str)
                balances.append(balance)
            except ValueError as e:
                raise ValueError(
                    f"Failed to extract balance for pattern '{pattern}': {e}"
                )

        if len(balances) != 2:
            raise ValueError("Could not extract both starting and ending balances.")

        self.start_balance, self.end_balance = balances

    def get_transaction_lines(self) -> list[str]:
        """
        Extract lines containing transaction information.
        Example line:
        `12/20 12/20 BESTBUYCOM806399323439 888-BESTBUY MN $39.99`

        - Lines must start with a date (`self.LEADING_DATE`) and include an amount (`self.AMOUNT`).
        - Multi-line transactions are concatenated until an amount is found or the next transaction starts.
        """

        def has_date(line: str) -> bool:
            """Check if a line starts with a valid date."""
            return bool(re.search(self.LEADING_DATE, line))

        def has_amount(line: str) -> bool:
            """Check if a line contains an amount."""
            return bool(re.search(self.AMOUNT, line))

        # Identify indices of potential transaction start lines
        transaction_indices = [
            i for i, line in enumerate(self.reader.lines) if has_date(line)
        ]

        transaction_lines = []
        max_lookahead = 5

        # Process each potential transaction line
        for i in transaction_indices:
            line = self.reader.lines[i]

            # Look ahead for multi-line transactions
            for k in range(1, max_lookahead + 1):
                if has_amount(line):
                    break
                next_index = i + k
                if (
                    next_index >= len(self.reader.lines)
                    or next_index in transaction_indices
                ):
                    # Stop if end of document or next transaction start is reached
                    break
                next_line = self.reader.lines[next_index]
                line = f"{line} {next_line}"

            if has_amount(line):
                transaction_lines.append(line)

        return transaction_lines

    def parse_transaction_lines(
        self, transaction_lines: list[str]
    ) -> list[Transaction]:
        """
        Convert raw transaction lines into structured data.
        """
        transactions = []
        balance = float(self.start_balance)

        for line in transaction_lines:
            words = line.split()

            # Convert leading mm/dd to full datetime
            mmdd = words.pop(0)
            transaction_date = get_absolute_date(mmdd, self.start_date, self.end_date)

            # If there is a second date, it is the posting date
            if words and re.search(self.TRANSACTION_DATE, words[0]):
                mmdd = words.pop(0)
                posting_date = get_absolute_date(mmdd, self.start_date, self.end_date)
            else:
                # The leading date is the posting date
                posting_date = transaction_date
                transaction_date = None

            # Extract the first amount-like string
            i_amount, amount_str = [
                (i, word)
                for i, word in enumerate(words)
                if re.search(self.AMOUNT, word)
            ][0]
            amount = -convert_amount_to_float(amount_str)

            # Update running balance
            balance = round(balance + amount, 2)

            # Extract the description
            desc = " ".join(words[:i_amount])

            # Append the transaction
            transactions.append(
                Transaction(
                    transaction_date=transaction_date,
                    posting_date=posting_date,
                    amount=amount,
                    balance=balance,
                    desc=desc,
                )
            )

        return transactions


def parse(reader: PDFReader) -> Statement:
    citiparser = CitiParser(reader)
    return citiparser.parse()
