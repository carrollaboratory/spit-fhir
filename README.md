# spit-fhir

Extract FHIR resources from the warehouse, validate them, and load into
Dewrangle.

## Where this fits

FHIR resources are now rendered inside dbt (previously this was done with a
Jinja-templating engine driven by a LinkML data model -- see
[carrollaboratory/piper](https://github.com/carrollaboratory/piper) for that
approach, kept around as reference). dbt writes its output into a single
Postgres table, `fhir_resources`, uniquely keyed by `(id, resource_type)`:

| column          | meaning                                   |
|-----------------|--------------------------------------------|
| `id`            | row identifier (not unique on its own)     |
| `resource_type` | the FHIR `resourceType`, e.g. `Patient`    |
| `resource`      | the rendered FHIR resource (JSON/JSONB)    |

`spit-fhir`'s job starts there: read that table (optionally filtered to
specific ids or resource types), run each resource through basic FHIR
validation (and, optionally, NCPI IG validation against a live FHIR server),
and write a manifest suitable for loading into Dewrangle by a separate
existing script.

```
Postgres (dbt output) -> extract -> validate -> Dewrangle manifest
```

## Install

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
and [just](https://just.systems/) to wrap the common commands. If you're new
to uv: it replaces `pip`/`venv` -- `uv sync` reads `pyproject.toml` and
`uv.lock` and creates/updates a `.venv` for you, and `uv run <cmd>` runs
something inside that environment without you having to activate it
yourself.

Requires [carrollaboratory/car-utils](https://github.com/carrollaboratory/car-utils)
(shared logging setup, LinkML model loading).

```
just install    # uv sync --extra dev
```

Requires Python 3.10+ (uv will fetch it automatically if it's not already
on your machine).

If you'd rather not install `just`, the recipes are one-liners -- see the
`justfile` and run the underlying `uv` commands directly.

## Configure

Copy `example/config.yaml` and point it at your warehouse:

```yaml
db:
  uri: postgresql+psycopg://user:pass@localhost:5432/warehouse
  table: fhir_resources

dewrangle:
  output_file: output/dewrangle.json
```

`db.uri` can also be supplied via the `SPIT_FHIR_DB_URI` environment
variable instead of being committed to the config file.

## Run

```
uv run spit-fhir example/config.yaml
```

Narrow the extraction with `--id` and/or `--resource-type` (both accept
multiple values and combine with AND); omit both to extract everything:

```
uv run spit-fhir example/config.yaml --resource-type Patient Observation
uv run spit-fhir example/config.yaml --id co-ajdm9fyxxz
```

`just start-pgsql` brings up the same local Postgres container
(`dbt-test-pg`) used by `fhir-kfi-dbt-model`, so `example/config.yaml` can
point at dbt's own output during local development.

### IG validation locally

`ValidateAgainstIG` needs a FHIR server with the NCPI IG loaded. That's
[carrollaboratory/hapi-helper](https://github.com/carrollaboratory/hapi-helper)
(docker-compose + an IG loader script), assumed to be checked out as a
sibling directory (`../hapi-helper`) -- override with `HAPI_HELPER_DIR` if
yours lives elsewhere.

```
just hapi-up      # bring up HAPI + its own Postgres, wait until ready
just load-ig      # load the published NCPI IG package
just hapi-ready   # both of the above in one step

just load-ig https://deploy-preview-162--ncpi-fhir-ig-v2.netlify.app/package.tgz
                  # load a different package instead, e.g. an unreleased
                  # netlify preview build

just hapi-logs    # tail the HAPI server's logs
just hapi-down    # stop and remove the containers (keeps IG/data volume)
just hapi-reset   # stop and remove everything, including the data volume
```

## Test data

`tests/data/dbt_fhir.json` is a snapshot of
[fhir-kfi-dbt-model's dbt export](https://github.com/carrollaboratory/fhir-kfi-dbt-model/blob/main/output/dbt_fhir.json)
-- toy data, expected to grow as the dbt transforms are completed.

```
just update-fixture   # re-fetch the fixture and run the tests against it
just test             # just run the tests
```

See `TODO.md` for known gaps.
