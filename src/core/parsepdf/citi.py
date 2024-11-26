import re
from datetime import datetime
from typing import Any, List, Tuple

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
        self.statement_dates()
        accounts = self.extract_accounts()
        return Statement(
            start_date=self.start_date, end_date=self.end_date, accounts=accounts
        )

    def statement_dates(self) -> None:
        """
        Extract the start and end dates from the statement.
        """
        _, dateline = find_line_startswith(self.reader.lines_clean, "Billing Period")
        parts = dateline.split()
        self.start_date, self.end_date = [
            datetime.strptime(date, self.DATE_FORMAT) for date in parts[2].split("-")
        ]

    def extract_accounts(self) -> List[Account]:
        """One account per Citi statement"""
        account_num = self.get_account_number()
        start_balance = self.get_starting_balance()
        try:
            self.extract_metadata()
            self.extract_transactions()
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            raise

    def extract_metadata(self) -> None:
        """
        Extract metadata such as account number, date range, and starting balance.
        """

    def extract_transactions(self) -> None:
        """
        Parse and extract transactions from the statement.
        """
        transaction_lines = self.get_transaction_lines()
        self.transactions = self.parse_transaction_lines(transaction_lines)

    def get_account_number(self) -> str:
        """
        Retrieve the account number from the statement.
        """
        search_str = "Account number ending in:"
        _, line = find_param_in_line(self.reader.lines, search_str)
        account = line.split(search_str)[-1].split()[0].strip()
        return account

    def get_starting_balance(self) -> float:
        """
        Extract the starting balance from the statement.
        """
        search_str = "Previous balance " "New balance "
        _, balance_line = find_param_in_line(self.reader.lines, search_str)
        balance_str = balance_line.split(search_str)[-1].split()[0]
        return -convert_amount_to_float(balance_str)

    def get_transaction_lines(self) -> List[str]:
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

    def parse_transaction_lines(self, transaction_lines: List[str]) -> List[Tuple]:
        """
        Convert raw transaction lines into structured data.
        """
        transactions = []
        date_pattern = re.compile(r"\d{2}/\d{2}")

        for line in transaction_lines:
            words = line.split()
            date_str = words.pop(0)
            date = get_absolute_date(
                date_str, [self.metadata["StartDate"], self.metadata["EndDate"]]
            )
            date = date.strftime(r"%Y-%m-%d")

            if re.search(date_pattern, words[0]):
                words.pop(0)

            i_amount, amount_str = [
                (i, word) for i, word in enumerate(words) if "$" in word
            ][-1]
            amount = -convert_amount_to_float(amount_str)

            # Update running balance
            self.balance = round(self.balance + amount, 2)

            description = " ".join(words[:i_amount])
            transactions.append((date, amount, self.balance, description))

        return transactions


def parse(reader: PDFReader) -> Statement:
    citiparser = CitiParser(reader)
    return citiparser.parse()
