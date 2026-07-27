# TODO

## Needs a decision

- **Table discovery.** `db.tables` is a hand-maintained list right now. dbt
  appears to produce one `fhir_resource` table per schema (e.g.
  `dev_include_access.fhir_resource`) -- if that pattern holds and more
  schemas get added over time, it may be worth sweeping
  `information_schema.tables` for everything matching `%.fhir_resource`
  instead of maintaining the list by hand. Depends on how many resource
  groups there end up being and whether all of them should always be
  included.
- **Dewrangle is still just a file writer.** `DewrangleJSON` (ported from
  piper) writes a local JSON manifest "suitable for Dewrangle" -- it does not
  call the Dewrangle API. Needs to be written for real: either extend this
  consumer to POST to Dewrangle directly, or confirm the manifest file is
  handed off to some other existing loader.
- **IG validation isn't wired into the CLI yet.** `ValidateAgainstIG` was
  ported and works the same as before (network call to a FHIR server's
  `$validate`), but `extract.py`'s `run()` only uses `ValidateResourceBasic`
  by default. Needs CLI flags (mirroring piper's old `--validate` /
  `--max-validation-count`) once there's a target IG validation server to
  point at.
- **Credentials.** DB connection currently comes from `db.uri` in the config
  or `SPIT_FHIR_DB_URI`; there's no secrets-manager integration. Fine for
  local dev -- decide before this runs anywhere shared.

## Known issue

- The current `tests/data/dbt_fhir.json` fixture fails
  `test_hl7_validation.py` as of 2026-07-27: `Consent.provision.purpose` is
  typed as `Coding[]` in base FHIR R4B, but the dbt output wraps each entry
  in an extra `{"coding": [...]}` envelope (as if it were a
  `CodeableConcept[]`). That's a dbt-side transform bug, not a spit-fhir bug
  -- worth fixing upstream in `fhir-kfi-dbt-model`, or the fixture will keep
  failing this test as more resources are added.

## Smaller items

- No CI workflow yet (`.github/workflows`) -- add one once there's enough
  here to be worth gating on.
- No integration test against a real Postgres instance -- current tests only
  exercise the validation/scrub logic against the static fixture, not
  `stream_table`/`run_extract` against a live DB.
- `ncpi_fhir_client` is pulled from `main` via a git URL dependency, same as
  piper did -- consider pinning to a tag/commit once that project's release
  cadence settles.
