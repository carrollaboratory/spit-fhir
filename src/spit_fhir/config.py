"""Application configuration, loaded from YAML into typed dataclasses.

Keeping this as plain dataclasses (rather than raw dict access) means a
missing or misspelled config key fails fast with a clear message instead of
a bare KeyError somewhere deep in the extract run.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from yaml import safe_load

from .exceptions import ConfigError


@dataclass
class DbConfig:
    """Connection and source-table details for the Postgres warehouse.

    Each table in `tables` is expected to provide, at minimum, an id column,
    a resource_type column, and a JSON/JSONB column holding the rendered
    FHIR resource -- this is the shape dbt currently produces (see
    tests/data/dbt_fhir.json for an example).
    """

    uri: str
    tables: list[str]
    id_column: str = "id"
    resource_type_column: str = "resource_type"
    resource_column: str = "resource"

    @classmethod
    def from_dict(cls, data: dict) -> "DbConfig":
        uri = data.get("uri") or os.environ.get("SPIT_FHIR_DB_URI")
        if not uri:
            raise ConfigError(
                "db.uri is required (or set SPIT_FHIR_DB_URI in the environment)"
            )

        tables = data.get("tables")
        if not tables:
            raise ConfigError(
                "db.tables must list at least one 'schema.table' to read from"
            )

        return cls(
            uri=uri,
            tables=list(tables),
            id_column=data.get("id_column", "id"),
            resource_type_column=data.get("resource_type_column", "resource_type"),
            resource_column=data.get("resource_column", "resource"),
        )


@dataclass
class DewrangleConfig:
    """Where/how the Dewrangle manifest gets written.

    NOTE: this currently only writes a local JSON manifest file -- it does
    not call the Dewrangle API. See TODO.md.
    """

    output_file: str = "output/dewrangle.json"
    buffer_size: int = 1000

    @classmethod
    def from_dict(cls, data: dict) -> "DewrangleConfig":
        return cls(
            output_file=data.get("output_file", "output/dewrangle.json"),
            buffer_size=data.get("buffer_size", 1000),
        )


@dataclass
class AppConfig:
    db: DbConfig
    dewrangle: DewrangleConfig = field(default_factory=DewrangleConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        if "db" not in data:
            raise ConfigError("Config is missing the required 'db' section")
        return cls(
            db=DbConfig.from_dict(data["db"]),
            dewrangle=DewrangleConfig.from_dict(data.get("dewrangle", {})),
        )


def load_config(path: str | Path) -> AppConfig:
    with open(path, "rt") as f:
        data = safe_load(f)
    return AppConfig.from_dict(data)
