class ConfigError(Exception):
    """Raised when the application config is invalid or incomplete."""


class PayloadDecodeError(Exception):
    """Raised when a row's resource payload can't be parsed as JSON."""

    def __init__(self, table: str, row_id, raw, cause: Exception):
        super().__init__(f"Row '{row_id}' from '{table}' is not valid JSON: {cause}")
        self.table = table
        self.row_id = row_id
        self.raw = raw
        self.cause = cause


class FhirValidationError(Exception):
    """Raised when a FHIR resource fails validation.

    Consumers raise this instead of exiting the process, so callers (CLI,
    Airflow task, etc.) can decide whether to stop, log-and-continue, or
    quarantine the offending resource.
    """

    def __init__(self, message: str, resource_type: str = "Unknown", errors=None):
        super().__init__(message)
        self.resource_type = resource_type
        self.errors = errors or []
