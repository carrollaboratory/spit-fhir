from spit_fhir.fhir_consumers import ValidateResourceBasic


def test_sample_resources_pass_basic_validation(fhir_resources):
    """The dbt export fixture should always be a set of FHIR-valid resources.

    A failure here means either the fixture has real (unfixed) errors, or
    validation logic itself has regressed -- check the raised
    FhirValidationError for which resource and field.
    """
    validator = ValidateResourceBasic()
    for resource in fhir_resources:
        validator(
            template_name=resource.get("resourceType", "Unknown"),
            resource=resource,
            payload=resource,
        )
