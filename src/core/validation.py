import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pdfplumber

# import pdftotext


@dataclass
class Transaction:
    date: datetime
    amount: float
    balance: float
    desc: str


@dataclass
class Account:
    account_num: str
    # account_name: str
    start_balance: float
    end_balance: float
    transactions: List[Transaction] = field(default_factory=list)


@dataclass
class Statement:
    # statement_type_id: int
    start_date: datetime
    end_date: datetime
    accounts: List[Account] = field(default_factory=list)


class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.doc = None
        self.text = None
        self.lines_raw = None
        self.lines = None

    def __enter__(self):
        """
        Open the PDF document using context manager.
        """
        self.doc = pdfplumber.open(self.fpath)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Close the PDF document upon exiting the context.
        """
        if self.doc:
            self.doc.close()
            self.doc = None

    def __del__(self):
        """
        Ensure the PDF document is closed when the object is deleted.
        """
        if self.doc:
            self.doc.close()

    def extract_text(self) -> str:
        if self.doc is None:
            raise ValueError("PDF not opened properly")
        self.text = "\n".join(
            [page.extract_text_simple() or "" for page in self.doc.pages]
        )
        return self.text

    def remove_empty_lines(self) -> list[str]:
        if self.text is None:
            self.extract_text()
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        return self.lines_raw

    def remove_white_space(self) -> list[str]:
        if self.lines_raw is None:
            self.remove_empty_lines()
        self.lines = [" ".join(line.split()) for line in self.lines_raw]
        return self.lines


"""
class PDFReader:
    def __init__(self, fpath: Path):
        self.fpath = fpath
        self.text = None
        self.lines_raw = None
        self.lines = None
        self.read_pdf()

    def read_pdf(self):
        with self.fpath.open("rb") as f:
            self.doc = pdftotext.PDF(f, physical=True)
        self.text = "\n".join(self.doc)
        self.lines_raw = [line for line in self.text.splitlines() if line.strip()]
        self.lines = [" ".join(line.split()) for line in self.lines_raw]
"""


def validate_transactions(transactions: list[tuple]):
    for transaction in transactions:
        date, amount, balance, description = transaction
        if not isinstance(date, datetime) or not re.match(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError(f"Invalid date: {date}")
        if not isinstance(amount, float):
            raise ValueError(f"Invalid amount: {amount}")
        if not isinstance(balance, float):
            raise ValueError(f"Invalid balance: {balance}")
        if not isinstance(description, str):
            raise ValueError(f"Invalid description: {description}")
        if description.strip() == "":
            raise ValueError(f"Empty description: {transaction}")
