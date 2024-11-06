# -*- coding: utf-8 -*-
import csv
from datetime import datetime
from pathlib import Path

import openpyxl
import pdftotext

from core.db import execute_sql_query, get_sqltable

from parsers import (
    amazonbus,
    amazonper,
    citi,
    fedloan,
    fidelity401k,
    fidelityhsa,
    hehsa,
    occuauto,
    occubank,
    occucc,
    transamerica,
    usbank,
    vanguard,
    wfbus,
    wfper,
    wfploan,
)


def get_account(text: str) -> tuple[str, str]:
    """
    Determine what kind of account this statement is
    """
    # Get the list of accounts and search strings from the db.
    db_path = Path("pyguibank.db")
    data, columns = get_sqltable(db_path, "AccountNumbers")

    # Search the text block for each search string
    account_id = None
    col = columns.index("SearchString")
    for row in data:
        search_str = row[col]
        if search_str in text:
            # If the string was found, retrieve the AccountID
            account_id = row[columns.index("AccountID")]
            break

    # If the AccountID was not found, raise an error
    if account_id is None:
        raise ValueError("Statement not recognized. Update tables and scripts.")

    # Get the name of the account and parser for this text.
    data, columns = execute_sql_query(
        db_path, "SELECT Account, Parser FROM Accounts WHERE AccountID=%s" % account_id
    )
    account, parser = data[0]

    return account, parser


def select_parser(text: str, extension=None) -> tuple[int, str]:
    """
    Determine what kind of statement this is so the correct parser can be used.
    """
    # Get the list of accounts and search strings from the db.
    db_path = Path("pyguibank.db")
    query = "SELECT STID, SearchString, Parser FROM StatementTypes"
    if extension:
        query += " WHERE Extension='%s'" % extension
    parser_data, _ = execute_sql_query(db_path, query)

    # Search the text block for each search string
    parser = None
    STID = None
    text_lower = text.lower()
    for row in parser_data:
        search_pattern = row[1].lower()
        search_strs = search_pattern.split("&&")
        matching = all([search_str in text_lower for search_str in search_strs])
        if matching:
            # If the string was found, retrieve the Parser name
            STID = row[0]
            parser = row[2]
            break

    # If the AccountID was not found, raise an error
    if STID is None or parser is None:
        raise ValueError("Statement type not recognized. Update tables and scripts.")

    return STID, parser


def read_pdf(fpath: Path) -> tuple[str, list[str], list[str]]:
    """
    Uses pdftotext to open and clean up the text in the document.
    """
    # Load PDF file
    with fpath.open("rb") as f:
        doc = pdftotext.PDF(f, physical=True)

    # Shape and clean the text
    text = "\n".join(doc)
    lines_raw = [line for line in text.splitlines() if line.strip() != ""]
    lines = [" ".join(line.split()) for line in lines_raw]

    return text, lines_raw, lines


def parse_pdf(fpath: Path) -> tuple[int, list[datetime], dict[str, list]]:
    """
    Opens the pdf and routes the contents to the appropriate parsing script
    """
    text, lines_raw, lines = read_pdf(fpath)

    # Determine statement type
    STID, parser = select_parser(text, extension=".pdf")

    # Parse lines into transactions for each account type
    match parser:
        case "occubank":
            date_range, data = occubank.parse(lines)
        case "citi":
            date_range, data = citi.parse(lines)
        case "usbank":
            date_range, data = usbank.parse(lines)
        case "occucc":
            date_range, data = occucc.parse(lines)
        case "wfper":
            date_range, data = wfper.parse(lines_raw, lines)
        case "wfbus":
            date_range, data = wfbus.parse(lines_raw, lines)
        case "wfploan":
            date_range, data = wfploan.parse(lines)
        case "fidelity401k":
            date_range, data = fidelity401k.parse(lines)
        case "fidelityhsa":
            date_range, data = fidelityhsa.parse(lines)
        case "hehsa":
            date_range, data = hehsa.parse(lines)
        case "transamerica":
            date_range, data = transamerica.parse(lines)
        case "vanguard":
            date_range, data = vanguard.parse(lines)
        case _:
            raise ValueError("Support for %s must be added to parse.py" % parser)

    return STID, date_range, data


def parse_csv(fpath: Path) -> tuple[int, list[datetime], dict[str, list]]:
    """
    Opens the csv and routes the contents to the appropriate parsing script.
    """
    # Load csv as plain text
    with fpath.open("r", encoding="utf-8-sig") as f:
        text = f.read()

    # Load csv as array
    array = []
    with fpath.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            array.append(row)

    # Determine which parsing script to use
    STID, parser = select_parser(text, extension=".csv")

    # Parse lines into transactions for each account type
    match parser:
        case "occuauto":
            date_range, data = occuauto.parse(array)
        case "amazonper":
            date_range, data = amazonper.parse(array)
        case "amazonbus":
            date_range, data = amazonbus.parse(array)
        case _:
            raise ValueError(
                ValueError("Support for %s must be added to parse.py" % parser)
            )

    return STID, date_range, data


def read_xlsx(fpath: Path) -> dict[str, list]:
    # Load the worksheets, skipping any blank rows
    workbook = openpyxl.load_workbook(fpath)
    sheets = {}
    sheetnames = workbook.sheetnames
    for i, worksheet in enumerate(workbook.worksheets):
        contents = list(worksheet.values)
        clean_sheet = [row for row in contents if any([col is not None for col in row])]
        sheets[sheetnames[i]] = clean_sheet
    return sheets


def parse_xlsx(fpath: Path) -> tuple[int, list[datetime], dict[str, list]]:
    """
    Opens the xlsx and routes the contents to the appropriate parsing script.
    """
    # Read the sheets into a dict[str, list[list]]
    sheets = read_xlsx(fpath)

    # Convert all workbook data to plaintext
    doc = []
    for sheet in sheets.values():
        doc.append(
            "\n".join(
                [
                    ", ".join([str(cell) for cell in row if cell is not None])
                    for row in sheet
                ]
            )
        )
    text = "\n".join(doc)

    # Determine the parser and route the sheets to that module
    STID, parser = select_parser(text, extension=".xlsx")
    match parser:
        case "fedloan":
            date_range, data = fedloan.parse(sheets)
        case _:
            raise ValueError(
                ValueError("Support for %s must be added to parse.py" % parser)
            )

    return STID, date_range, data


def parse(fpath: Path) -> tuple[int, list[datetime], dict[str, list[tuple]]]:
    """
    Routes the file to the appropriate parser based on file type.
    Scrape all the transactions from the file and get simplified filename
    """
    suffix = fpath.suffix.lower()
    match suffix:
        case ".pdf":
            return parse_pdf(fpath)
        case ".csv":
            return parse_csv(fpath)
        case ".xlsx":
            return parse_xlsx(fpath)
        case _:
            raise ValueError("Unsupported file extension: %s" % suffix)
