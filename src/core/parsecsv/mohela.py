from datetime import datetime

from loguru import logger

from ..interfaces import IParser
from ..utils import convert_amount_to_float
from ..validation import Account, Statement, Transaction


class Parser(IParser):
    STATEMENT_TYPE = "MOHELA Loan Servicing"
    HEADER_DATE = r"%m/%d/%Y"

    def parse(self, array: list[list[str]]) -> Statement:
        """Entry point

        Args:
            array (list[list[str]]): Array of data from csv

        Returns:
            Statement: Statement dataclass
        """
        logger.trace(f"Parsing {self.STATEMENT_TYPE} statement")

        try:
            # Correct Date column
            # '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">Date'
            array[0][0] = array[0][0].split(">")[-1]

            self.array = array
            return self.extract_statement()
        except Exception as e:
            logger.error(f"Error parsing {self.STATEMENT_TYPE} statement: {e}")
            raise

    def extract_statement(self) -> Statement:
        """Extracts all statement data

        Returns:
            Statement: Statement dataclass
        """
        account = self.extract_account()
        if not account:
            raise ValueError("No accounts were extracted from the statement.")

        return Statement(
            start_date=account.transactions[0].posting_date,
            end_date=account.transactions[-1].posting_date,
            accounts=[account],
        )

    def extract_account(self) -> Account:
        """
        Extracts account-level data, including balances and transactions.

        Returns:
            Account: The extracted account as a dataclass instance.

        Raises:
            ValueError: If account number is invalid or data extraction fails.
        """
        # Extract account number
        account_num = "MOHELA Student Loan"

        # Parse transactions
        try:
            transactions = self.parse_transactions()
        except Exception as e:
            raise ValueError(
                f"Failed to parse transactions for account {account_num}: {e}"
            )

        return Account(
            account_num=account_num,
            start_balance=0.0,
            end_balance=transactions[-1].balance,
            transactions=transactions,
        )

    def parse_transactions(self) -> list[Transaction]:
        """Convert raw transaction rows into structured data.

        Returns:
            list[tuple]: Unsorted transaction array
        """
        # Convert the array to list of dict
        data = []
        for row in self.array[1:]:
            entry = {}
            for i, col in enumerate(self.array[0]):
                if not col:
                    continue
                if col == "Date":
                    entry[col] = datetime.strptime(row[i], self.HEADER_DATE)
                else:
                    entry[col] = row[i]
            data.append(entry)

        transactions = []
        balance = 0
        for entry in sorted(data, key=lambda x: x["Date"]):

            # Melt table into individual transactions
            total = -convert_amount_to_float(entry["Total"])
            interest = convert_amount_to_float(entry["Interest"])

            balance += total
            transactions.append(
                Transaction(
                    transaction_date=entry["Date"],
                    posting_date=entry["Date"],
                    amount=total,
                    desc=entry["Description"],
                    balance=round(balance, 2),
                )
            )

            if interest != 0:
                balance += interest
                transactions.append(
                    Transaction(
                        transaction_date=entry["Date"],
                        posting_date=entry["Date"],
                        amount=interest,
                        desc="INTEREST",
                        balance=round(balance, 2),
                    )
                )

        return transactions
