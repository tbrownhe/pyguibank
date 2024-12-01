from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from loguru import logger


### Exceptions
class ValidationError(Exception):
    pass


### Data structures
@dataclass
class Transaction:
    posting_date: datetime
    amount: float
    balance: float
    desc: str
    transaction_date: Optional[datetime] = None


@dataclass
class Account:
    account_num: str
    start_balance: float
    end_balance: float
    transactions: List[Transaction]
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    statement_id: Optional[int] = None

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
        if self.account_id is None or not isinstance(self.account_id, int):
            errors.append("account_id must be an integer")
        if self.account_name is None or not isinstance(self.account_name, str):
            errors.append("account_name must be a string")
        if errors:
            raise ValidationError("\n".join(errors))

    def validate_complete(self):
        """Validate all fields for final processing."""
        self.validate_initial()
        self.validate_account_info()
        if self.statement_id is None or not isinstance(self.statement_id, int):
            raise ValidationError("statement_id must be an integer")


@dataclass
class Statement:
    start_date: datetime
    end_date: datetime
    accounts: List[Account]
    stid: Optional[int] = None
    fpath: Optional[Path] = None
    dpath: Optional[Path] = None
    md5hash: Optional[str] = None

    def add_md5hash(self, md5hash: str):
        if not isinstance(md5hash, str):
            raise ValidationError("md5hash must be a str")
        self.md5hash = md5hash

    def add_dpath(self, dpath: Path):
        self.dpath = dpath


### Validation framework
VALIDATION_CHECKS: List[Callable[[Statement], List[str]]] = []


def register_validation(check: Callable[[Statement], List[str]]):
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
    errors = []
    if statement.stid is None:
        errors.append("StatementTypeID cannot be None")
    if statement.fpath is None:
        errors.append("Statement fpath cannot be None")
    return errors


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
