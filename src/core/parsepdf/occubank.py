import re
from datetime import datetime

from loguru import logger

from ..interfaces import IParser
from ..utils import (
    PDFReader,
    convert_amount_to_float,
    find_line_re_search,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)
from ..validation import Account, Statement, Transaction


class OCCUParser(IParser):
    HEADER_DATE = r"%m/%d/%y"
    LEADING_DATE = re.compile(r"^\d{2}/\d{2}\s")
    AMOUNT = re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

    def parse(self, reader: PDFReader) -> Statement:
        """Entry point

        Args:
            reader (PDFReader): pdfplumber child class

        Returns:
            Statement: Statement dataclass
        """
        logger.trace("Parsing OCCU Bank statement")
        self.lines = reader.extract_lines_simple()
        self.reader = reader

        return self.extract_statement()

    def extract_statement(self) -> Statement:
        """Extracts all statement data

        Returns:
            Statement: Statement dataclass
        """
        self.get_statement_dates()
        accounts = self.extract_accounts()
        return Statement(
            start_date=self.start_date, end_date=self.end_date, accounts=accounts
        )

    def get_statement_dates(self) -> None:
        """
        Parse the statement date range into datetime.

        Raises:
            ValueError: If dates cannot be parsed or are invalid.
        """
        try:
            self.dates_from_text()
        except Exception as e1:
            try:
                self.dates_from_annotations()
            except Exception as e2:
                errors = "\n".join([e1, e2])
                raise ValueError(f"Failed to parse statement dates:\n{errors}")

    def dates_from_text(self):
        """
        MEMBER STATEMENT
        MEMBERNUMBER501462
        PAGE 1 of 9
        FROM 03/01/21
        TO 03/31/21
        """
        _, from_line = find_line_re_search(self.lines, r"FROM \d{2}/\d{2}/\d{2}")
        _, to_line = find_line_re_search(self.lines, r"TO \d{2}/\d{2}/\d{2}")

        # Parse the lines into datetime and return variable sdates
        start_date_str = from_line.split()[1]
        end_date_str = to_line.split()[1]
        self.start_date = datetime.strptime(start_date_str, self.HEADER_DATE)
        self.end_date = datetime.strptime(end_date_str, self.HEADER_DATE)

    def dates_from_annotations(self):
        """Statements before 2021-03-01 store dates in annotations"""
        page = self.reader.PDF.pages[0]
        start_date_str = self.extract_from_annotations(page, "FROM_DATE")
        end_date_str = self.extract_from_annotations(page, "TO_DATE")
        self.start_date = datetime.strptime(start_date_str, self.HEADER_DATE)
        self.end_date = datetime.strptime(end_date_str, self.HEADER_DATE)

    def extract_from_annotations(self, page, pattern: str) -> str:
        """
        Extracts the value of a PDF page annotation matching a pattern.

        Args:
            page: The pdfplumber page object.
            pattern: The prefix pattern of the annotation title to search for.

        Returns:
            The value of the matching annotation as a string.

        Raises:
            KeyError: If no annotation matches the given pattern.
        """
        for annot in page.annots or []:
            title = annot.get("title")
            if title and title.startswith(pattern):
                return annot["data"]["V"].decode("utf-8")
        raise KeyError(f"Unable to find {pattern} in page annotations.")

    def extract_accounts(self) -> list[Account]:
        """Split the statement text into account sections

        Returns:
            list[Account]: List of accounts for this statement
        """
        # Determine the line number at the beginning of each section
        i_sav, sav_line = find_param_in_line(self.lines, "PRIMARY SAVINGS")
        i_chk, chk_line = find_param_in_line(
            self.lines, "REMARKABLE CHECKING", start=i_sav + 1
        )
        try:
            i_other, _ = find_line_startswith(self.lines, "XXXXX", start=i_chk + 1)
        except ValueError:
            i_other = None
        try:
            i_loan, _ = find_param_in_line(self.lines, "PERSONAL CREDIT LINE")
        except ValueError:
            i_loan = None

        i_max = min(i for i in [i_other, i_loan, len(self.lines)] if i)

        # Get the lines for each section
        lines_sav = self.lines[i_sav:i_chk]
        lines_chk = self.lines[i_chk:i_max]

        # Get the account number for each section
        account_sav = sav_line.split()[0]
        account_chk = chk_line.split()[0]

        # Create a dictionary of each account
        account_dict = {account_chk: lines_chk, account_sav: lines_sav}

        # For each account, create an Account class and return list[Account]
        accounts = []
        for account_num, lines in account_dict.items():
            accounts.append(self.extract_account(account_num, lines))

        return accounts

    def extract_account(self, account_num: str, lines: list[str]) -> Account:
        """Extract account level data

        Returns:
            Account: Account dataclass
        """
        start_balance, end_balance = self.get_statement_balances(lines)
        transaction_lines = self.get_transaction_lines(lines)
        transactions = self.parse_transaction_lines(transaction_lines)
        return Account(
            account_num=account_num,
            start_balance=start_balance,
            end_balance=end_balance,
            transactions=transactions,
        )

    def get_statement_balances(self, lines: list[str]) -> tuple[float, float]:
        """Extract the starting and ending balance from the statement.
        Example:
        XXXXXX2215 - REMARKABLE CHECKING .
        Previous Balance........................................... $x,xxx.xx
        Minimum Balance: $xxx.xx
        4 Additions...................................................... $xxx.xx
        19 Subtractions.............................................. $x,xxx.xx
        Ending Balance.............................................. $xxx.xx

        Raises:
            ValueError: Unable to extract a balance
            ValueError: Unable to extract both balances
        """
        patterns = ["Previous Balance", "Ending Balance"]
        balances = []

        for pattern in patterns:
            try:
                _, balance_line = find_param_in_line(lines, pattern)
                balance_str = balance_line.split()[-1]
                balance = convert_amount_to_float(balance_str)
                balances.append(balance)
            except ValueError as e:
                raise ValueError(
                    f"Failed to extract balance for pattern '{pattern}': {e}"
                )

        if len(balances) != 2:
            raise ValueError("Could not extract both starting and ending balances.")

        return balances

    def get_transaction_lines(self, lines: list[str]) -> list[str]:
        """Extract lines containing transaction information.

        Returns:
            list[str]: Processed lines containing dates and amounts for this statement
        """
        transaction_lines = []
        for line in lines:
            # Skip lines without a leading date
            if not re.search(self.LEADING_DATE, line):
                continue

            words = line.split()
            if "$" in words[-2] and "$" in words[-1]:
                # Normal transaction line
                transaction_lines.append(line)
                continue

        return transaction_lines

    def parse_transaction_lines(self, transaction_list: list[str]) -> list[tuple]:
        """
        Converts the raw transaction text into an organized list of transactions.
        """
        transactions = []
        for line in transaction_list:
            # Split the line into a list of words
            words = line.split()

            # The first item is the date
            date_str = words[0]
            date = get_absolute_date(date_str, self.start_date, self.end_date)

            # Amount and Balance are the -2 and -1 words in the line.
            amount = convert_amount_to_float(words[-2])
            balance = convert_amount_to_float(words[-1])

            # Remove pound sign if present
            if words[1] == "#":
                words.pop(1)

            # The description is everything in between
            desc = " ".join(words[1:-2])
            # desc = remove_stop_words(description)

            transactions.append(
                Transaction(
                    transaction_date=date,
                    posting_date=date,
                    amount=amount,
                    desc=desc,
                    balance=balance,
                )
            )

        return transactions
