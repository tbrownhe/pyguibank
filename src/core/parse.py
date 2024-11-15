import csv
from datetime import datetime
from pathlib import Path

import openpyxl
import pdftotext

from . import parsepdf, parsecsv, parsexlsx
from .query import statement_types


def select_parser(db_path: Path, text: str, extension="") -> tuple[int, str]:
    """
    Determine what kind of statement this is so the correct parser can be used.
    """
    data, _ = statement_types(db_path, extension=extension)

    # Search the text block for each search string
    parser = None
    STID = None
    text_lower = text.lower()
    for STID, pattern, parser in data:
        search_strs = pattern.lower().split("&&")
        matching = all([search_str in text_lower for search_str in search_strs])
        if matching:
            break

    if not matching:
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


def parse_pdf(
    db_path: Path, fpath: Path
) -> tuple[int, list[datetime], dict[str, list]]:
    """
    Opens the pdf and routes the contents to the appropriate parsing script
    """
    text, lines_raw, lines = read_pdf(fpath)

    # Determine statement type
    STID, parser = select_parser(db_path, text, extension=".pdf")

    # Parse lines into transactions for each account type
    match parser:
        case "occubank":
            date_range, data = parsepdf.occubank.parse(lines)
        case "citi":
            date_range, data = parsepdf.citi.parse(lines)
        case "usbank":
            date_range, data = parsepdf.usbank.parse(lines)
        case "occucc":
            date_range, data = parsepdf.occucc.parse(lines)
        case "wfper":
            date_range, data = parsepdf.wfper.parse(lines_raw, lines)
        case "wfbus":
            date_range, data = parsepdf.wfbus.parse(lines_raw, lines)
        case "wfploan":
            date_range, data = parsepdf.wfploan.parse(lines)
        case "fidelity401k":
            date_range, data = parsepdf.fidelity401k.parse(lines)
        case "fidelityhsa":
            date_range, data = parsepdf.fidelityhsa.parse(lines)
        case "hehsa":
            date_range, data = parsepdf.hehsa.parse(lines)
        case "transamerica":
            date_range, data = parsepdf.transamerica.parse(lines)
        case "vanguard":
            date_range, data = parsepdf.vanguard.parse(lines)
        case _:
            raise ValueError(f"Parser name {parser} must be added to parse.py")

    return STID, date_range, data


def parse_csv(
    db_path: Path, fpath: Path
) -> tuple[int, list[datetime], dict[str, list]]:
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
    STID, parser = select_parser(db_path, text, extension=".csv")

    # Parse lines into transactions for each account type
    match parser:
        case "occuauto":
            date_range, data = parsecsv.occuauto.parse(array)
        case "amazonper":
            date_range, data = parsecsv.amazonper.parse(array)
        case "amazonbus":
            date_range, data = parsecsv.amazonbus.parse(array)
        case _:
            raise ValueError(f"Parser name {parser} must be added to parse.py")

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


def parse_xlsx(
    db_path: Path, fpath: Path
) -> tuple[int, list[datetime], dict[str, list]]:
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
    STID, parser = select_parser(db_path, text, extension=".xlsx")
    match parser:
        case "fedloan":
            date_range, data = parsexlsx.fedloan.parse(sheets)
        case _:
            raise ValueError(f"Parser name {parser} must be added to parse.py")

    return STID, date_range, data


def parse(
    db_path: Path, fpath: Path
) -> tuple[int, list[datetime], dict[str, list[tuple]]]:
    """
    Routes the file to the appropriate parser based on file type.
    Scrape all the transactions from the file and get simplified filename
    """
    suffix = fpath.suffix.lower()
    match suffix:
        case ".pdf":
            return parse_pdf(db_path, fpath)
        case ".csv":
            return parse_csv(db_path, fpath)
        case ".xlsx":
            return parse_xlsx(db_path, fpath)
        case _:
            raise ValueError("Unsupported file extension: %s" % suffix)
