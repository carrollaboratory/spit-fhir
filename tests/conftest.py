import json
from pathlib import Path

import pytest

DATA_FILE = Path(__file__).parent / "data" / "dbt_fhir.json"


@pytest.fixture(scope="session")
def dbt_fhir_tables() -> dict:
    """The raw {table_name: [rows...]} export produced by dbt (toy data).

    Grows as the dbt transforms are completed -- see
    https://github.com/carrollaboratory/fhir-kfi-dbt-model/blob/main/output/dbt_fhir.json
    """
    with DATA_FILE.open() as f:
        return json.load(f)


@pytest.fixture(scope="session")
def fhir_resources(dbt_fhir_tables) -> list[dict]:
    """Every FHIR resource payload across all exported tables, flattened."""
    resources = []
    for rows in dbt_fhir_tables.values():
        for row in rows:
            resources.append(row["resource"])
    return resources
