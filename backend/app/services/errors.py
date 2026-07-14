"""Domain-level exceptions shared across services.

Keeping these separate from FastAPI's HTTPException means the service layer
stays framework-agnostic; the API layer maps them to HTTP responses.
"""


class IngestionError(Exception):
    """Base class for problems while ingesting a document."""


class UnsupportedFileTypeError(IngestionError):
    def __init__(self, filename: str, detail: str = "") -> None:
        self.filename = filename
        message = f"Unsupported file type: {filename!r}."
        if detail:
            message = f"{message} {detail}"
        super().__init__(message)


class EmptyDocumentError(IngestionError):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"Document {filename!r} contains no extractable text.")
