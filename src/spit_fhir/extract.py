#!/usr/bin/env python
"""
Extract FHIR resources produced by dbt from Postgres, validate them, and hand
them off to the configured consumers (currently: a Dewrangle JSON manifest).

All resources live in a single table, uniquely keyed by (id, resource_type),
which is expected to provide at minimum:
    id             -- a row identifier (not unique on its own)
    resource_type  -- the FHIR resourceType, e.g. 'Patient'
    resource       -- the rendered FHIR resource as JSON/JSONB

This mirrors the shape dbt currently produces -- see tests/data/dbt_fhir.json
for an example export.
"""

import argparse
import json
import logging
from importlib.metadata import version
from typing import Iterable, Iterator

from car_utils import setup_logging
from sqlalchemy import create_engine, text

from .config import AppConfig, DbConfig, load_config
from .exceptions import FhirValidationError, PayloadDecodeError
from .fhir_consumers import (
    DewrangleJSON,
    ResourceConsumer,
    ResourceSummary,
    ValidateResourceBasic,
)


def stream_table(
    engine,
    db_config: DbConfig,
    ids: list[str] | None = None,
    resource_types: list[str] | None = None,
    chunksize: int = 1000,
) -> Iterator[tuple]:
    """Yield (id, resource_type, resource) rows from the fhir_resources table.

    With no filters, every row is streamed. `ids` and `resource_types`, when
    given, are combined with AND -- e.g. passing both narrows to just those
    ids that are also one of those resource types.
    """
    clauses = []
    params: dict = {}
    if ids:
        clauses.append(f"{db_config.id_column} = ANY(:ids)")
        params["ids"] = list(ids)
    if resource_types:
        clauses.append(f"{db_config.resource_type_column} = ANY(:resource_types)")
        params["resource_types"] = list(resource_types)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    query = text(
        f"SELECT {db_config.id_column}, {db_config.resource_type_column}, "
        f"{db_config.resource_column} FROM {db_config.table}{where}"
    )
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(query, params)
        for partition in result.partitions(chunksize):
            for row in partition:
                yield row


def coerce_payload(table: str, row_id, resource) -> dict:
    """psycopg returns JSONB columns already decoded to dict; tolerate a raw
    JSON string too, in case the column is plain text/varchar."""
    if isinstance(resource, dict):
        return resource
    try:
        return json.loads(resource)
    except (TypeError, json.JSONDecodeError) as e:
        raise PayloadDecodeError(table=table, row_id=row_id, raw=resource, cause=e) from e


def run_extract(
    config: AppConfig,
    consumers: Iterable[ResourceConsumer],
    ids: list[str] | None = None,
    resource_types: list[str] | None = None,
) -> ResourceSummary:
    """Stream the configured table through each consumer in turn.

    Raises FhirValidationError / PayloadDecodeError on the first bad
    resource -- it's on the caller (the CLI, or an Airflow task) to decide
    whether that should stop the run, be logged and skipped, or routed to a
    quarantine path.
    """
    engine = create_engine(config.db.uri)
    summary = ResourceSummary()
    all_consumers = [*consumers, summary]
    table = config.db.table

    try:
        logging.info(
            f"Extracting '{table}'"
            + (f" ids={ids}" if ids else "")
            + (f" resource_types={resource_types}" if resource_types else "")
        )
        row_count = 0
        for row_id, resource_type, resource in stream_table(
            engine, config.db, ids=ids, resource_types=resource_types
        ):
            payload = coerce_payload(table, row_id, resource)
            raw = json.dumps(payload)
            for consumer in all_consumers:
                consumer(template_name=resource_type, resource=raw, payload=payload)
            row_count += 1
        logging.info(f"{row_count} resource(s) extracted")
        summary.reset(f"'{table}' complete")
    finally:
        engine.dispose()

    return summary


def run():
    parser = argparse.ArgumentParser(
        description="Extract FHIR resources from Postgres, validate, and load to Dewrangle"
    )
    parser.add_argument("config", help="Path to the YAML configuration file")
    parser.add_argument(
        "--id",
        dest="ids",
        nargs="+",
        help="Only extract these resource ids (default: all)",
    )
    parser.add_argument(
        "--resource-type",
        dest="resource_types",
        nargs="+",
        help="Only extract these FHIR resource types (default: all)",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="INFO",
        choices=["NOTSET", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"],
        help="Log level",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('spit-fhir')}"
    )
    args = parser.parse_args()
    setup_logging(args.log_level)

    config = load_config(args.config)

    dewrangle = DewrangleJSON(
        filename=config.dewrangle.output_file,
        buffersize=config.dewrangle.buffer_size,
    )
    consumers = [ValidateResourceBasic(), dewrangle]

    try:
        summary = run_extract(
            config, consumers, ids=args.ids, resource_types=args.resource_types
        )
    except (FhirValidationError, PayloadDecodeError):
        logging.exception("Extract run aborted")
        raise
    finally:
        dewrangle.close()

    summary.report_totals("All resources extracted")


if __name__ == "__main__":
    run()
