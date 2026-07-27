import logging
from typing import Any

from fhir.resources.R4B import get_fhir_model_class
from pydantic import ValidationError

from ..exceptions import FhirValidationError
from .resource_consumer import ResourceConsumer
from .utils import scrub_empty


class ValidateResourceBasic(ResourceConsumer):
    """Validates basic conformance to the FHIR spec using fhir.resources.

    This won't catch NCPI IG-specific errors -- see ValidateAgainstIG for
    that. It's fast enough to act as a sanity check on every resource before
    the (slower, network-bound) IG validation step or the Dewrangle load.
    """

    def __call__(self, template_name: str, resource: str, payload: dict[str, Any]):
        resource_type = payload.get("resourceType")
        if not resource_type:
            raise FhirValidationError(
                f"No resourceType found in resource from '{template_name}'"
            )

        dropped_keys: list[str] = []
        cleaned_payload = scrub_empty(payload, dropped_keys=dropped_keys)

        try:
            fhir_class = get_fhir_model_class(resource_type)
            fhir_class(**cleaned_payload)
        except ValidationError as e:
            if dropped_keys:
                logging.warning(
                    "The following properties were '' and were dropped before "
                    "validation: %s",
                    ", ".join(dropped_keys),
                )
            errors = e.errors()
            messages = [
                f"field '{err['loc'][-1]}' had value '{err.get('input')}': {err['msg']}"
                for err in errors
            ]
            raise FhirValidationError(
                f"Basic FHIR validation of '{template_name}' ({resource_type}) "
                f"failed with {len(errors)} error(s):\n" + "\n".join(messages),
                resource_type=resource_type,
                errors=errors,
            ) from e
