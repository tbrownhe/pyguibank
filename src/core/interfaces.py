from typing import Any, Protocol, runtime_checkable

from core.validation import Statement, ValidationError


@runtime_checkable
class IParser(Protocol):
    """Enforces consistent design inputs and outputs for all parsers.
    Class variables listed here must all be overridden by individual parsers.
    Validation during plugin import will refuse empty strings.

    Args:
        input_data (Any): The data to parse (PDFReader, CSV array, XLSX sheets, etc.).

    Returns:
        Statement: The parsed statement data.
    """

    # Plugin metadata
    SUFFIX = ""
    VERSION = ""
    COMPANY = ""
    STATEMENT_TYPE = ""
    SEARCH_STRING = ""
    INSTRUCTIONS = ""

    def parse(self, input_data: Any) -> Statement:
        raise ValidationError(
            "All children of IParser must override the parse() method"
            " and return type validation.Statement"
        )
