# TODO

## Needs a decision

- **IG validation server.** A local HAPI FHIR server with the NCPI IG loaded
  will be stood up (on Eric's laptop for now) as the target for
  `ValidateAgainstIG`. Not yet decided whether/how that can run in CI --
  needs to bring up the server + load the IG (see the `justfile` stub) once
  that's worked out. Until then, `--validate-ig`-style CLI wiring for it is
  on hold.
- **Credentials in production.** DB connection currently comes from `db.uri`
  in the config or `SPIT_FHIR_DB_URI`. How this gets populated once the job
  runs live is still unknown -- likely baked into the runtime environment,
  but the shape of that isn't decided yet.
- **`profile` column.** A `profile` column may be added to `fhir_resources`
  later for more selective extraction. Not adding speculative filtering for
  it now -- revisit once the column actually exists.

## Resolved (was open, now settled)

- ~~Table discovery~~ -- all resources live in one `fhir_resources` table,
  uniquely keyed by `(id, resource_type)`. `extract.py` supports `--id` and
  `--resource-type` filters (combined with AND), or no filter for "all".
- ~~Dewrangle API~~ -- `DewrangleJSON` writing a local manifest file is the
  intended final behavior for this repo; a separate existing script (not
  part of this repo, may or may not get folded in later) loads that file
  into Dewrangle.

## Known issue

- `tests/data/dbt_fhir.json` fails `test_hl7_validation.py` as of
  2026-07-27: `Consent.provision.purpose` is typed as `Coding[]` in base
  FHIR R4B, but the dbt output wraps each entry in an extra
  `{"coding": [...]}` envelope, as if it were `CodeableConcept[]`. That's a
  dbt-side transform bug in `fhir-kfi-dbt-model`, not a spit-fhir bug.

## Smaller items

- No CI workflow yet (`.github/workflows`) -- add one once there's enough
  here to be worth gating on, and once the IG-validation-in-CI question
  above is settled (basic FHIR validation + unit tests don't need it either
  way).
- No integration test against a real Postgres instance -- current tests only
  exercise the validation/scrub logic against the static fixture, not
  `stream_table`/`run_extract` against a live DB.
- `ncpi_fhir_client` is pulled from `main` via a git URL dependency, same as
  piper did -- consider pinning to a tag/commit once that project's release
  cadence settles.
