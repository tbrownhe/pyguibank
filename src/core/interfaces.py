from typing import Any, Protocol, runtime_checkable

from .validation import Statement


@runtime_checkable
class IParser(Protocol):
    """Enforces consistent design inputs and outputs for all parsers.

    Args:
        input_data (Any): The data to parse (PDFReader, CSV array, XLSX sheets, etc.).

    Returns:
        Statement: The parsed statement data.
    """

    def parse(self, input_data: Any) -> Statement:
        pass
