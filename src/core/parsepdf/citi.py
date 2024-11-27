import re
from datetime import datetime
from typing import Any

from loguru import logger

from ..utils import (
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)
from ..validation import (
    Account,
    PDFReader,
    Statement,
    Transaction,
    validate_transactions,
)


class CitiParser:
    DATE_FORMAT = r"%m/%d/%y"

    def __init__(self, reader: PDFReader):
        reader.remove_white_space()
        self.reader = reader

    def parse(self) -> Statement:
        """
        Main entry point to parse the statement.
        """
        logger.trace("Starting parsing for Citi statement")
        return self.extract_statement()

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
            datetime.strptime(date, self.DATE_FORMAT) for date in parts.split("-")
        ]

    def extract_accounts(self) -> list[Account]:
        """One account per Citi statement"""
        return [self.extract_account()]

    def extract_account(self) -> Account:
        """Extract account level data"""
        account_num = self.get_account_number()
        self.get_statement_balances()
        transactions = self.extract_transactions()
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

    def extract_transactions(self) -> list[Transaction]:
        """
        Parse and extract transactions from the statement.
        """
        transaction_lines = self.get_transaction_lines()
        return self.parse_transaction_lines(transaction_lines)

    def get_transaction_lines(self) -> list[str]:
        """
        Extract lines containing transaction information.
        """
        leading_date = re.compile(r"^\d{2}/\d{2}\s")
        transaction_indices = [
            i
            for i, line in enumerate(self.reader.lines)
            if re.search(leading_date, line)
        ]
        transaction_lines = []

        for i in transaction_indices:
            line = self.reader.lines[i]
            if i == transaction_indices[-1] or "$" in line:
                transaction_lines.append(line)
                continue

            # Handle multi-line transactions
            k = 0
            while True:
                k += 1
                if k > 5 or i + k in transaction_indices:
                    break
                next_line = self.reader.lines[i + k]
                if "$" in line and "$" not in next_line:
                    break
                line = f"{line} {next_line}"

            transaction_lines.append(line)

        return transaction_lines

    def parse_transaction_lines(
        self, transaction_lines: list[str]
    ) -> list[Transaction]:
        """
        Convert raw transaction lines into structured data.
        """
        transactions = []
        date_pattern = re.compile(r"\d{2}/\d{2}")
        balance = float(self.start_balance)

        for line in transaction_lines:
            words = line.split()
            date_str = words.pop(0)
            date = get_absolute_date(date_str, [self.start_date, self.end_date])
            # date = date.strftime(r"%Y-%m-%d")

            if re.search(date_pattern, words[0]):
                words.pop(0)

            i_amount, amount_str = [
                (i, word) for i, word in enumerate(words) if "$" in word
            ][0]
            amount = -convert_amount_to_float(amount_str)

            # Update running balance
            balance = round(balance + amount, 2)

            desc = " ".join(words[:i_amount])
            transaction = Transaction(
                date=date, amount=amount, balance=balance, desc=desc
            )
            transactions.append(transaction)

        return transactions


def parse(reader: PDFReader) -> Statement:
    citiparser = CitiParser(reader)
    return citiparser.parse()
