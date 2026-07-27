fixture_url := "https://raw.githubusercontent.com/carrollaboratory/fhir-kfi-dbt-model/main/output/dbt_fhir.json"
fixture_path := "tests/data/dbt_fhir.json"

# Local checkout of carrollaboratory/hapi-helper (docker-compose + IG loader).
# Override if you keep it somewhere other than next to this repo, e.g.:
#   HAPI_HELPER_DIR=~/code/hapi-helper just hapi-up
hapi_helper_dir := env_var_or_default("HAPI_HELPER_DIR", "../hapi-helper")
hapi_compose := hapi_helper_dir / "docker-compose.yml"

# Base URL of the local HAPI FHIR server
fhir_url := env_var_or_default("FHIR_URL", "http://localhost:8080/fhir")

# Default NCPI IG package; override per-call for e.g. a netlify preview build:
#   just load-ig https://deploy-preview-162--ncpi-fhir-ig-v2.netlify.app/package.tgz
default_ig_url := "https://nih-ncpi.github.io/ncpi-fhir-ig-2/package.tgz"

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

# Bring up the local HAPI FHIR server (see carrollaboratory/hapi-helper) and wait for it to be ready
hapi-up:
    docker compose -f {{hapi_compose}} up -d
    just hapi-wait

# Tear down the local HAPI FHIR server (keeps the postgres data volume)
hapi-down:
    docker compose -f {{hapi_compose}} down

# Tear down the local HAPI FHIR server AND wipe its data volume
hapi-reset:
    docker compose -f {{hapi_compose}} down -v

# Tail the HAPI server's logs
hapi-logs:
    docker compose -f {{hapi_compose}} logs -f fhir

# Block until the HAPI server responds -- JPA boot + IG install takes a while
hapi-wait:
    until curl -sf {{fhir_url}}/metadata > /dev/null; do sleep 2; done

# Load the NCPI IG (or an override, e.g. a netlify preview build) into the running server
load-ig ig_url=default_ig_url:
    bash {{hapi_helper_dir}}/scripts/load_ig.sh {{fhir_url}} {{ig_url}}

# Bring up HAPI and load the IG in one step
hapi-ready: hapi-up load-ig
