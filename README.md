# spit-fhir

Extract FHIR resources from the warehouse, validate them, and load into
Dewrangle.

## Where this fits

FHIR resources are now rendered inside dbt (previously this was done with a
Jinja-templating engine driven by a LinkML data model -- see
[carrollaboratory/piper](https://github.com/carrollaboratory/piper) for that
approach, kept around as reference). dbt writes its output into Postgres as
one table per resource group, with each row holding:

| column          | meaning                                   |
|-----------------|--------------------------------------------|
| `id`            | row identifier                             |
| `resource_type` | the FHIR `resourceType`, e.g. `Patient`    |
| `resource`      | the rendered FHIR resource (JSON/JSONB)    |

`spit-fhir`'s job starts there: read those tables, run each resource through
basic FHIR validation (and, optionally, NCPI IG validation against a live
FHIR server), and write a manifest suitable for loading into Dewrangle.

```
Postgres (dbt output) -> extract -> validate -> Dewrangle manifest
```

## Install

```
pip install -e ".[dev]"
```

Requires Python 3.13+.

## Configure

Copy `example/config.yaml` and point it at your warehouse:

```yaml
db:
  uri: postgresql+psycopg://user:pass@localhost:5432/warehouse
  tables:
    - dev_include_access.fhir_resource

dewrangle:
  output_file: output/dewrangle.json
```

`db.uri` can also be supplied via the `SPIT_FHIR_DB_URI` environment
variable instead of being committed to the config file.

## Run

```
spit-fhir example/config.yaml
```

## Test data

`tests/data/dbt_fhir.json` is a snapshot of
[fhir-kfi-dbt-model's dbt export](https://github.com/carrollaboratory/fhir-kfi-dbt-model/blob/main/output/dbt_fhir.json)
-- toy data, expected to grow as the dbt transforms are completed. Re-fetch
it with:

```
curl -sL -o tests/data/dbt_fhir.json \
  https://raw.githubusercontent.com/carrollaboratory/fhir-kfi-dbt-model/main/output/dbt_fhir.json
```

See `TODO.md` for known gaps.
