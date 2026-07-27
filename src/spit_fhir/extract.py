#!/usr/bin/env python
"""
Extract FHIR resources produced by dbt from Postgres, validate them, and hand
them off to the configured consumers (currently: a Dewrangle JSON manifest).

Each configured table is expected to provide, at minimum:
    id             -- a row identifier (any type)
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

from sqlalchemy import create_engine, text

from . import setup_logging
from .config import AppConfig, load_config
from .exceptions import FhirValidationError, PayloadDecodeError
from .fhir_consumers import DewrangleJSON, ResourceConsumer, ResourceSummary, ValidateResourceBasic


def stream_table(
    engine, table: str, db_config, chunksize: int = 1000
) -> Iterator[tuple]:
    """Yield (id, resource_type, resource) rows from a single dbt-produced table."""
    query = text(
        f"SELECT {db_config.id_column}, {db_config.resource_type_column}, "
        f"{db_config.resource_column} FROM {table}"
    )
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(query)
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
    config: AppConfig, consumers: Iterable[ResourceConsumer]
) -> ResourceSummary:
    """Stream every configured table through each consumer in turn.

    Raises FhirValidationError / PayloadDecodeError on the first bad
    resource -- it's on the caller (the CLI, or an Airflow task) to decide
    whether that should stop the run, be logged and skipped, or routed to a
    quarantine path.
    """
    engine = create_engine(config.db.uri)
    summary = ResourceSummary()
    all_consumers = [*consumers, summary]

    try:
        for table in config.db.tables:
            logging.info(f"Extracting '{table}'")
            row_count = 0
            for row_id, resource_type, resource in stream_table(
                engine, table, config.db
            ):
                payload = coerce_payload(table, row_id, resource)
                raw = json.dumps(payload)
                for consumer in all_consumers:
                    consumer(template_name=table, resource=raw, payload=payload)
                row_count += 1
            logging.info(f"{row_count} resource(s) read from '{table}'")
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
        summary = run_extract(config, consumers)
    except (FhirValidationError, PayloadDecodeError):
        logging.exception("Extract run aborted")
        raise
    finally:
        dewrangle.close()

    summary.report_totals("All resources extracted")


if __name__ == "__main__":
    run()
