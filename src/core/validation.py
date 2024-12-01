from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional


### Exceptions
class StatementValidationError(Exception):
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
    account_name: Optional[str] = None


@dataclass
class Statement:
    start_date: datetime
    end_date: datetime
    accounts: List[Account]
    stid: Optional[int] = None


### Validation framework
VALIDATION_CHECKS: List[Callable[[Statement], List[str]]] = []


def register_validation(check: Callable[[Statement], List[str]]):
    VALIDATION_CHECKS.append(check)


def validate_statement(statement: Statement):
    errors = []
    for check in VALIDATION_CHECKS:
        errors.extend(check(statement))
    if errors:
        raise StatementValidationError("\n".join(errors))


### Validation functions


def validate_metadata(statement: Statement) -> list[str]:
    errors = []
    if statement.stid is None:
        errors.append("StatementTypeID cannot be None")
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
                    f"Transaction date {transaction.date} is outside the statement"
                    f" date range {statement.start_date} - {statement.end_date}"
                )

            # Transaction date (if available) must be within 1 week of the posting date
            if transaction.transaction_date:
                if not isinstance(transaction.transaction_date, datetime):
                    errors.append(f"Invalid date: {transaction.transaction_date}")
                if (
                    abs((transaction.transaction_date - transaction.posting_date).days)
                    > 7
                ):
                    errors.append(
                        f"Transaction date {transaction.transaction_date} is more than 7 days"
                        " from posting date {transaction.posting_date}"
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