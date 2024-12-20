import re
from datetime import datetime, timedelta
from statistics import mode

from loguru import logger
from pdfplumber.page import Page

from ..interfaces import IParser
from ..utils import (
    PDFReader,
    convert_amount_to_float,
    find_line_startswith,
    find_param_in_line,
    get_absolute_date,
)
from ..validation import Account, Statement, Transaction


class Parser(IParser):
    STATEMENT_TYPE = "CitiBank Credit Card"
    HEADER_DATE = r"%m/%d/%y"
    LEADING_DATE = re.compile(r"^\d{2}/\d{2}\s")
    TRANSACTION_DATE = re.compile(r"\d{2}/\d{2}")
    AMOUNT = re.compile(r"-?\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?")

    def parse(self, reader: PDFReader) -> Statement:
        """Entry point

        Args:
            reader (PDFReader): pdfplumber child class

        Returns:
            Statement: Statement dataclass
        """
        logger.trace(f"Parsing {self.STATEMENT_TYPE} statement")

        try:
            self.lines = reader.extract_lines_simple()
            if not self.lines:
                raise ValueError("No lines extracted from the PDF.")
            self.reader = reader
            return self.extract_statement()
        except Exception as e:
            logger.error(f"Error parsing {self.STATEMENT_TYPE} statement: {e}")
            raise

    def extract_statement(self) -> Statement:
        """Extracts all statement data

        Returns:
            Statement: Statement dataclass
        """
        self.get_statement_dates()
        accounts = self.extract_accounts()
        if not accounts:
            raise ValueError("No accounts were extracted from the statement.")

        return Statement(
            start_date=self.start_date,
            end_date=self.end_date,
            accounts=accounts,
        )

    def get_statement_dates(self) -> None:
        """
        Parse the statement date range into datetime.

        Raises:
            ValueError: If dates cannot be parsed or are invalid.
        """
        logger.trace("Attempting to parse dates from text.")
        try:
            _, dateline = find_line_startswith(self.lines, "Billing Period:")
            pattern = re.compile(
                r"Billing Period:\s?(\d{2}/\d{2}/\d{2})-(\d{2}/\d{2}/\d{2})"
            )
            result = pattern.search(dateline)
            self.start_date = datetime.strptime(result.group(1), self.HEADER_DATE)
            self.end_date = datetime.strptime(result.group(2), self.HEADER_DATE)
        except Exception as e:
            logger.trace(f"Failed to parse dates from text: {e}")
            raise ValueError(f"Failed to parse statement dates: {e}")

    def extract_accounts(self) -> list[Account]:
        """
        One account per statement

        Returns:
            list[Account]: List of accounts for this statement.
        """
        return [self.extract_account()]

    def extract_account(self) -> Account:
        """
        Extracts account-level data, including balances and transactions.

        Returns:
            Account: The extracted account as a dataclass instance.

        Raises:
            ValueError: If account number is invalid or data extraction fails.
        """
        # Extract account number
        try:
            account_num = self.get_account_number()
        except Exception as e:
            raise ValueError(f"Failed to extract account number: {e}")

        # Extract statement balances
        try:
            start_balance, end_balance = self.get_statement_balances()
        except Exception as e:
            raise ValueError(
                f"Failed to extract balances for account {account_num}: {e}"
            )

        # Extract transaction lines
        try:
            transaction_array = self.get_transaction_array()
        except Exception as e:
            raise ValueError(
                f"Failed to extract transactions for account {account_num}: {e}"
            )

        # Parse transactions
        try:
            transactions = self.parse_transaction_array(transaction_array)
        except Exception as e:
            raise ValueError(
                f"Failed to parse transactions for account {account_num}: {e}"
            )

        return Account(
            account_num=account_num,
            start_balance=start_balance,
            end_balance=end_balance,
            transactions=transactions,
        )

    def get_account_number(self) -> str:
        """Retrieve the account number from the statement.

        Returns:
            str: Account number
        """
        search_str = "Account number ending in:"
        _, line = find_param_in_line(self.lines, search_str)
        account_num = line.split(search_str)[-1].split()[0].strip()
        return account_num

    def get_statement_balances(self) -> None:
        """Extract the starting balance from the statement.

        Raises:
            ValueError: Unable to extract balances
        """
        patterns = ["Previous balance $", "New balance $"]
        balances = []

        for pattern in patterns:
            try:
                _, balance_line = find_param_in_line(self.lines, pattern)
                result = self.AMOUNT.search(balance_line)
                balance_str = result.group()
                balance = -convert_amount_to_float(balance_str)
                balances.append(balance)
            except ValueError as e:
                raise ValueError(
                    f"Failed to extract balance for pattern '{pattern}': {e}"
                )

        if len(balances) != 2:
            raise ValueError("Could not extract both starting and ending balances.")

        return balances[0], balances[1]

    def get_transaction_array(self) -> list[list[str]]:
        """Extract lines containing transaction information.

        Wells Fargo statements are quite tricky. They must be extracted via pdfplumber's
        table methods, but the table dimensions vary from page to page so must
        be adjusted dynamically.

        Returns:
            list[list[str]]: Processed lines containing dates and amounts for this statement
        """
        transaction_array = []
        for i, page in enumerate(self.reader.PDF.pages):
            try:
                transaction_array.extend(self.get_transactions_from_page(page))
            except Exception as e:
                raise ValueError(f"Failed to extract transactions from page {i}: {e}")

        return transaction_array

    def get_transactions_from_page(self, page: Page) -> list[list[str]]:
        """Extracts transaction array from each page of the pdf.

        Args:
            page (Page): pdfplumber PDF.pages object

        Returns:
            list[list[str]]: Processed lines containing dates and amounts for this page
        """
        header_cols = ["date", "date", "Description", "Amount"]

        # Get the metadata and text of every word in the header.
        page_words_all = page.extract_words()
        page_words = [
            word for word in page_words_all if word.get("text") in header_cols
        ]
        page_word_list = [pword.get("text") for pword in page_words]

        # Make sure all header words were found. If not, return empty row
        missing_words = [word for word in header_cols if word not in page_word_list]
        if missing_words:
            logger.trace(
                f"Skipping {page.page_number} because a table header was not found."
            )
            return []

        # Filter out spurious words by removing anything > 2 points from the mode
        y_mode = mode(word.get("bottom") for word in page_words)
        page_words = [
            word for word in page_words if abs(word.get("bottom") - y_mode) < 2
        ]
        page_word_list = [pword.get("text") for pword in page_words]

        # Make sure all header words were found. If not, return empty row
        missing_words = [word for word in header_cols if word not in page_word_list]
        if missing_words:
            logger.trace(
                f"Skipping {page.page_number} because a table header was not found."
            )
            return []

        # Make sure there are no duplicates
        if len(page_words) != len(header_cols):
            word_list = [word.get("text") for word in page_words]
            raise ValueError(
                "Too many header keywords were found."
                f" Expected: {header_cols}\nGot: {word_list}"
            )

        # Correct ambiguity in (Trans) date vs (Post) date
        dates = [i for i, word in enumerate(page_words) if word.get("text") == "date"]
        if page_words[dates[0]].get("x0") < page_words[dates[1]].get("x0"):
            page_words[dates[0]]["text"] = "Trans date"
            page_words[dates[1]]["text"] = "Post date"
        else:
            page_words[dates[1]]["text"] = "Trans date"
            page_words[dates[0]]["text"] = "Post date"

        # Remap words list[dict] so it's addressable by column name
        header = {}
        for word in page_words:
            header[word.get("text")] = {
                "x0": word.get("x0"),
                "x1": word.get("x1"),
                "top": word.get("top"),
                "bottom": word.get("bottom"),
            }

        # Crop the page to the table size: [x0, top, x1, bottom]
        crop_page = page.crop(
            [
                header["Trans date"]["x0"] - 3,
                header["Trans date"]["bottom"] + 0.1,
                header["Amount"]["x1"] + 2,
                page.height,
            ]
        )
        # im = crop_page.to_image()
        # im.show()

        def calculate_vertical_lines(header):
            """
            Create a list of vertical table separators based on the header coordinates
            0: Trans Date:   L Justified
            1: Post Date:    L Justified
            2: Description:  L Justified
            3: Amount:       R Justified
            """
            return [
                header["Trans date"]["x0"] - 3,
                header["Post date"]["x0"] - 3,
                header["Description"]["x0"] - 4,
                header["Description"]["x1"]
                + 0.85 * (header["Amount"]["x0"] - header["Description"]["x1"]),
                header["Amount"]["x1"] + 1,
            ]

        # Extract the table from the cropped page using dynamic vertical separators
        vertical_lines = calculate_vertical_lines(header)
        table_settings = {
            "vertical_strategy": "explicit",
            "horizontal_strategy": "text",
            "explicit_vertical_lines": vertical_lines,
        }
        array = crop_page.extract_table(table_settings=table_settings)

        # Array validation
        for i, row in enumerate(reversed(array)):
            # Make sure each row has the right number of columns
            if len(row) != len(vertical_lines) - 1:
                array.pop(len(array) - 1 - i)
                # raise ValueError(f"Incorrect number of columns for row: {row}")

        return array

    def parse_transaction_array(self, array: list[list[str]]) -> list[Transaction]:
        """Convert transaction table into structured data.

        Args:
            transaction_lines (listlist[[str]]): Array containing valid transaction data

        Returns:
            list[tuple]: Unsorted transaction array
        """
        # for row in array:
        #    print(row)
        # exit()

        def get_full_description(i_row):
            """Lookahead for multi-line transactions"""
            desc = array[i_row][2]
            multilines = 1
            while (
                i_row + multilines < len(array)
                and not array[i_row + multilines][1]
                and array[i_row + multilines][2]
            ):
                desc += f" {array[i_row + multilines][2]}"
                multilines += 1
            return desc, multilines - 1

        transactions = []
        i_row = 0
        while i_row < len(array):
            row = array[i_row]

            # Return early if this is not a transaction start line
            if not bool(self.TRANSACTION_DATE.search(row[1])):
                i_row += 1
                continue

            # Extract main part of the transaction
            posting_date = get_absolute_date(row[1], self.start_date, self.end_date)
            if row[0]:
                transaction_date = get_absolute_date(
                    row[0], self.start_date, self.end_date
                )
            else:
                transaction_date = posting_date
            amount = -convert_amount_to_float(row[3])
            desc, multilines = get_full_description(i_row)
            i_row += multilines

            # Append transaction
            # Note: Balance is appended only at the end of each transaction day
            # and ends up being overwritten by Transaction.sort_and_compute_balances()
            transactions.append(
                Transaction(
                    transaction_date=transaction_date,
                    posting_date=posting_date,
                    amount=amount,
                    desc=desc,
                )
            )

            # Increase counter
            i_row += 1

        return transactions
