fixture_url := "https://raw.githubusercontent.com/carrollaboratory/fhir-kfi-dbt-model/main/output/dbt_fhir.json"
fixture_path := "tests/data/dbt_fhir.json"

# List available recipes
default:
    just --list

start-pgsql:
  docker start dbt-test-pg || true

# Run the test suite
test:
    uv run pytest

# Re-fetch the dbt FHIR export fixture, then run the tests against it
update-fixture:
    curl -sL -o {{fixture_path}} {{fixture_url}}
    just test

install:
    uv sync --extra dev

# TODO: bring up a local HAPI FHIR server with the NCPI IG loaded, for
# ValidateAgainstIG -- discuss what that setup should look like before
# wiring it in here.
