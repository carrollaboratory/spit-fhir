"""
Validate FHIR resources against the NCPI IG by POSTing to a FHIR server's
$validate endpoint.
"""

from collections import defaultdict
from typing import Dict

from ncpi_fhir_client.fhir_client import FhirClient

from ..exceptions import FhirValidationError
from .resource_consumer import ResourceConsumer
from .utils import scrub_empty


def format_operation_outcome(oo_dict) -> str:
    """
    Formats a FHIR OperationOutcome dictionary into a clean, human-readable report.
    """
    issues = oo_dict.get("issue", [])
    if not issues:
        return "No issues found in OperationOutcome."

    report = [f"{'=' * 60}", f"{'FHIR API PROFILE ERRORS':^60}", f"{'=' * 60}"]

    # Group issues by severity to reduce noise
    for severity in ["fatal", "error", "warning", "information"]:
        relevant_issues = [i for i in issues if i.get("severity") == severity]
        if not relevant_issues:
            continue

        report.append(f"\n[{severity.upper()}]")

        for issue in relevant_issues:
            # Prefer expression/FHIRPath over XPath for location
            loc = "General"
            if "expression" in issue:
                loc = " -> ".join(issue["expression"])
            elif "location" in issue:
                loc = " -> ".join(issue["location"])

            details = issue.get("details", {}).get("text")
            diagnostics = issue.get("diagnostics")
            message = details or diagnostics or "Unknown error"

            report.append(f"  • Loc: {loc}")
            report.append(f"    Msg: {message}")

    report.append(f"\n{'=' * 60}")
    return "\n".join(report)


class ValidateAgainstIG(ResourceConsumer):
    """Submit the resources to a FHIR server for NCPI IG validation.

    If max_validation_count is greater than 0, only that many resources of
    any given type will be validated -- useful for spot-checking a large run
    without paying the network cost for every single resource.
    """

    def __init__(self, fhir_config: Dict, max_validation_count: int = 0):
        self.max_validation_count = max_validation_count
        self.observed_resource_types = defaultdict(int)
        self.fhir_config = fhir_config
        self.fhir_client = FhirClient(self.fhir_config)

    def __call__(self, template_name, resource, payload):
        resource_type = payload["resourceType"]

        if (
            self.max_validation_count > 0
            and self.observed_resource_types[resource_type]
            >= self.max_validation_count
        ):
            return

        dropped_keys = []
        cleaned_payload = scrub_empty(payload, dropped_keys=dropped_keys)
        response = self.fhir_client.load(resource_type, cleaned_payload, True)

        if response["status_code"] >= 300:
            raise FhirValidationError(
                f"IG validation of '{template_name}' ({resource_type}) failed "
                f"[{response['status_code']}] {response['request_url']}\n"
                f"{format_operation_outcome(response['response'])}",
                resource_type=resource_type,
            )

        self.observed_resource_types[resource_type] += 1
