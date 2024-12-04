from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Any
import hashlib
from loguru import logger


### Exceptions
class ValidationError(Exception):
    pass


### Data structures
@dataclass
class Transaction:
    transaction_date: datetime
    posting_date: datetime
    amount: float
    desc: str = ""
    balance: Optional[float] = None
    md5: Optional[str] = None

    @classmethod
    def sort_and_compute_balances(
        cls, transactions: list["Transaction"], start_balance: float
    ) -> list["Transaction"]:
        """
        Sorts transactions by posting date and computes running balances.

        Args:
            transactions (list[Transaction]): List of transactions to process.
            start_balance (float): The starting balance for the account.

        Returns:
            list[Transaction]: Transactions sorted by posting date with computed balances.
        """
        if not transactions:
            return transactions

        sorted_transactions = sorted(transactions, key=lambda t: t.posting_date)

        # Check if all transactions already have balances
        if all(isinstance(t.balance, float) for t in sorted_transactions):
            logger.debug("Balances are already populated; skipping recalculation.")
            return sorted_transactions

        current_balance = start_balance
        for transaction in sorted_transactions:
            current_balance = round(current_balance + transaction.amount, 2)
            transaction.balance = current_balance

        return sorted_transactions

    @classmethod
    def hash_transactions(
        cls, account_id: int, transactions: List["Transaction"]
    ) -> List["Transaction"]:
        """
        Generates and appends MD5 hashes for the transactions.
        """
        if any(not isinstance(t.balance, float) for t in transactions):
            raise ValueError("All transactions must have valid balances to hash.")

        md5_set = set()
        for transaction in transactions:
            attempt = 0
            while True:
                # Build the hash string
                hash_str = "".join(
                    [
                        str(account_id),
                        transaction.posting_date.strftime(r"%Y-%m-%d"),
                        f"{transaction.amount:.2f}",
                        f"{transaction.balance:.2f}",
                        transaction.desc,
                        str(attempt),
                    ]
                )
                md5 = hashlib.md5(hash_str.encode()).hexdigest()

                if md5 not in md5_set:
                    md5_set.add(md5)
                    break

                logger.warning(
                    f"Hash collision detected for transaction '{transaction.desc}'. Retrying..."
                )
                attempt += 1

            transaction.md5 = md5

        return transactions

    @classmethod
    def to_db_rows(
        cls, statement_id: int, account_id: int, transactions: List["Transaction"]
    ) -> list[dict[str, Any]]:
        """
        Converts the Transaction instance to a tuple compatible with database insertion.

        Returns:
            tuple: A tuple of the transaction's fields in the required order.
        """
        rows = []
        for t in transactions:
            if not t.balance:
                raise ValueError(
                    f"Transaction {t.desc} is missing a balance and cannot be inserted."
                )
            if not t.md5:
                raise ValueError(
                    f"Transaction {t.desc} is missing an MD5 hash and cannot be inserted."
                )
            rows.append(
                {
                    "StatementID": statement_id,
                    "AccountID": account_id,
                    "Date": t.posting_date.strftime(r"%Y-%m-%d"),
                    "Amount": t.amount,
                    "Balance": t.balance,
                    "Description": t.desc,
                    "MD5": t.md5,
                }
            )
        return rows

    @classmethod
    def validate_balances(cls, transactions: list["Transaction"]) -> list[str]:
        """
        Validates that all transactions have valid balances.
        """
        errors = [
            f"Invalid balance for transaction: {t.desc}"
            for t in transactions
            if not isinstance(t.balance, float)
        ]
        return errors

    @classmethod
    def validate_complete(cls, transactions: list["Transaction"]) -> list[str]:
        """
        Validates all attributes of a list of Transaction objects.

        Args:
            transactions (list[Transaction]): List of transactions to validate.

        Returns:
            list[str]: A list of validation error messages. Empty if all are valid.
        """
        errors = []

        for i, t in enumerate(transactions):
            # Validate transaction_date
            if not isinstance(t.transaction_date, datetime):
                errors.append(
                    f"Transaction {i + 1}: 'transaction_date' must be a datetime, got {type(t.transaction_date).__name__}."
                )

            # Validate posting_date
            if not isinstance(t.posting_date, datetime):
                errors.append(
                    f"Transaction {i + 1}: 'posting_date' must be a datetime, got {type(t.posting_date).__name__}."
                )

            # Validate amount
            if not isinstance(t.amount, (int, float)):
                errors.append(
                    f"Transaction {i + 1}: 'amount' must be a number, got {type(t.amount).__name__}."
                )

            # Validate desc
            if not isinstance(t.desc, str):
                errors.append(
                    f"Transaction {i + 1}: 'desc' must be a string, got {type(t.desc).__name__}."
                )

            # Validate balance
            if t.balance is not None and not isinstance(t.balance, (int, float)):
                errors.append(
                    f"Transaction {i + 1}: 'balance' must be a number or None, got {type(t.balance).__name__}."
                )

            # Validate md5
            if t.md5 is not None and not isinstance(t.md5, str):
                errors.append(
                    f"Transaction {i + 1}: 'md5' must be a string or None, got {type(t.md5).__name__}."
                )

        return errors


@dataclass
class Account:
    account_num: str
    start_balance: float
    end_balance: float
    transactions: list[Transaction]
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    statement_id: Optional[int] = None

    def process_transactions(self):
        """
        Sort transactions and calculate balances. Updates the end balance.
        """
        if self.transactions is None:
            raise ValueError("Transactions must be populated before processing.")

        self.transactions = Transaction.sort_and_compute_balances(
            self.transactions, self.start_balance
        )

    def add_account_info(self, account_id: int, account_name: str):
        if not isinstance(account_id, int):
            raise ValidationError("account_id must be an int")
        if not isinstance(account_name, str):
            raise ValidationError("account_name must be a string")
        self.account_id = account_id
        self.account_name = account_name

    def add_statement_id(self, statement_id: int):
        if not isinstance(statement_id, int):
            raise ValidationError("statement_id must be an int")
        self.statement_id = statement_id

    def validate_initial(self):
        """Validate fields required before assigning account_id and account_name."""
        errors = []

        errors.extend(Transaction.validate_balances(self.transactions))

        if not isinstance(self.account_num, str):
            errors.append("account_num must be a string")
        if not isinstance(self.start_balance, float):
            errors.append("start_balance must be a float")
        if not isinstance(self.end_balance, float):
            errors.append("end_balance must be a float")
        if errors:
            raise ValidationError("\n".join(errors))

    def validate_account_info(self):
        """Validate fields required before assigning statement_id."""
        errors = []
        if not isinstance(self.account_id, int):
            errors.append("account_id must be an integer")
        if not isinstance(self.account_name, str):
            errors.append("account_name must be a string")
        if errors:
            raise ValidationError("\n".join(errors))

    def validate_complete(self):
        """Validate all fields for final processing."""
        # self.validate_initial()
        # self.validate_account_info()
        if not isinstance(self.statement_id, int):
            raise ValidationError("statement_id must be an integer")


@dataclass
class Statement:
    start_date: datetime
    end_date: datetime
    accounts: list[Account]
    stid: Optional[int] = None
    fpath: Optional[Path] = None
    dpath: Optional[Path] = None
    md5hash: Optional[str] = None

    def add_metadata(self, fpath: Path, stid: int):
        if not isinstance(fpath, Path):
            raise ValidationError("fpath must be a Path")
        if not isinstance(stid, int):
            raise ValidationError("stid must be int")
        self.fpath = fpath
        self.stid = stid

    def add_md5hash(self, md5hash: str):
        if not isinstance(md5hash, str):
            raise ValidationError("md5hash must be a str")
        self.md5hash = md5hash

    def add_dpath(self, dpath: Path):
        self.dpath = dpath

    def validate_metadata(self) -> list[str]:
        errors = []
        if not isinstance(self.fpath, Path):
            errors.append("fpath must be a Path")
        if not isinstance(self.stid, int):
            errors.append("stid must be int")
        return errors


### Validation framework
VALIDATION_CHECKS: list[Callable[[Statement], list[str]]] = []


def register_validation(check: Callable[[Statement], list[str]]):
    VALIDATION_CHECKS.append(check)


def validate_statement(statement: Statement, hard_fail: bool):
    errors = []
    for check in VALIDATION_CHECKS:
        errors.extend(check(statement))
    if errors:
        if hard_fail:
            raise ValidationError("\n".join(errors))
        else:
            logger.debug(errors)


### Validation functions
def validate_metadata(statement: Statement) -> list[str]:
    return statement.validate_metadata()


def validate_transactions(statement: Statement) -> list[str]:
    errors = []
    for account in statement.accounts:
        for transaction in account.transactions:
            # Posting date must be within the satement date range
            if not isinstance(transaction.posting_date, datetime):
                errors.append(f"Invalid date: {transaction.posting_date}")
            if (transaction.posting_date < statement.start_date) or (
                transaction.posting_date > statement.end_date
            ):
                errors.append(
                    f"Transaction date {transaction.posting_date} is outside the statement"
                    f" date range {statement.start_date} - {statement.end_date}"
                )

            # Transaction date (if available) must be within 30 days of the posting date
            # `04/17 05/05 ROSAN JAMAICA LIMITED MONTEGO BAY`
            if transaction.transaction_date:
                if not isinstance(transaction.transaction_date, datetime):
                    errors.append(f"Invalid date: {transaction.transaction_date}")
                if (
                    abs((transaction.transaction_date - transaction.posting_date).days)
                    > 30
                ):
                    errors.append(
                        f"Transaction date {transaction.transaction_date} is more than 7 days"
                        f" from posting date {transaction.posting_date}"
                    )

            # Amount, balance, and description must exist with correct type
            if not isinstance(transaction.amount, float):
                errors.append(f"Invalid amount: {transaction.amount}")
            if not isinstance(transaction.balance, float):
                errors.append(f"Invalid balance: {transaction.balance}")
            if not isinstance(transaction.desc, str):
                errors.append(f"Invalid description: {transaction.desc}")
            if transaction.desc.strip() == "":
                errors.append(f"Empty description: {transaction}")

    return errors


def validate_balances(statement: Statement) -> list[str]:
    errors = []
    for account in statement.accounts:
        # Ensure transaction amounts add up to statement balance difference
        balance_change = account.end_balance - account.start_balance
        sum_amounts = sum(transaction.amount for transaction in account.transactions)
        discrepancy = abs(balance_change - sum_amounts)
        if discrepancy > 0.01:
            errors.append(
                f"Validation failed for account '{account.account_num}'. "
                f"Balance change ({balance_change:.2f}) does not match "
                f"sum of transactions ({sum_amounts:.2f}). Discrepancy: {discrepancy:.2f}"
            )

    return errors


# Register validation checks
register_validation(validate_metadata)
register_validation(validate_transactions)
register_validation(validate_balances)
# register_validation(some_new_check)
