from typing import Any, Protocol, runtime_checkable

from core.validation import Statement, ValidationError


@runtime_checkable
class IParser(Protocol):
    """Enforces consistent design inputs and outputs for all parsers.

    Args:
        input_data (Any): The data to parse (PDFReader, CSV array, XLSX sheets, etc.).

    Returns:
        Statement: The parsed statement data.
    """

    def parse(self, input_data: Any) -> Statement:
        raise ValidationError(
            "All children of IParser must override the parse() method"
            " and return type validation.Statement"
        )
