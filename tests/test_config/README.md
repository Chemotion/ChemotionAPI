# Seeded integration environment

A local Chemotion ELN (docker compose) plus a seeded database, so the integration test suite
(the tests deselected by default via `-m "not integration"`) can run against a known state.

## Contents

- `compose.yml` — a minimal Chemotion stack, based on the
  [ChemOrc payload compose](https://github.com/Chemotion/ChemOrc/blob/main/payload/docker-compose.yml)
  but trimmed to the essentials: `db` (Postgres, published on host port **54320**) and `eln`
  (published on host port **3579**, running with `CONFIG_ROLE=combine` so the one container serves
  the web app *and* the background worker — its only startup dependency is `db`). The stock image
  only knows the eln/worker roles, so `embed/` mounts the
  [Push2Deploy](https://github.com/Chemotion/Push2Deploy) versions of `run.sh`/`health.sh`, which
  add the combine role.

  The compose project (`chemotion-test-<suffix>`) and the volume names carry a per-line suffix
  (`CHEMOTION_STACK_SUFFIX`) so one line's volumes — which survive `docker compose down` — are
  never silently reused under another line's images.
- `../data/test.sql` — the seeded database. All users are fictional:

  | Login | Password | Role |
  | --- | --- | --- |
  | `API` | `1234qewR!` | Person — the account the tests log in with |
  | `ADM` | `PleaseChangeYourPassword` | Admin |
  | `MM` (Max Mustermann) | `thebestpasswordever` | Person |

- `../data/setup_chemotion_db.sh` — dumps the current DB to `../data/dumps/` (gitignored),
  then drops, recreates and reloads it from `test.sql` and runs pending Rails migrations (the seed
  is dumped at the stack's own version, so this is normally a no-op — it only replays
  migrations after a stack upgrade. The original 2.1.1-era dump lives in git history).
- `sample_files/` — attachment fixtures used by some tests.

## Usage

```bash
cd tests/test_config
docker compose up -d       # first start initializes the instance (takes a few minutes)
```

Then run the integration suite from `tests/` — the conftest resets the DB from the seed
automatically unless `NO_SETUP=1`:

```bash
cd ..
NO_SETUP=0 ../.venv/bin/python -m pytest -m integration
```

Connection defaults (URL `http://127.0.0.1:3579`, users above) live in `tests/conftest.py
DEFAULT_CONFIG`; override any of them via environment variables or a gitignored `config.json`
(template: [`../config.json.sample`](../config.json.sample); `conftest.py` reads `config.json`
from the working directory, i.e. `tests/` in the `just test-integration` workflow).

Note: the DB reset uses the host Postgres client tools (`psql`, `pg_dump`) against port 54320
when available, and falls back to `docker compose exec db` otherwise — docker is the only hard
requirement.


## Scope: ELN v3 and v4

**This stack serves the v3 and v4 release lines. It does not support ELN v2, and the client is not
claimed to work against one.** A 2.x image will start on it — the embed scripts are portable — but
nothing here is seeded, exercised or supported for v2. `main` is where the v2-era client lives;
this layer exists to carry v3 and v4 forward.

## Choosing the server version

The stack takes its images from the environment rather than pinning one, because v3 and v4 share
it and each runs against the ELN it targets. The compose file therefore takes the images from the
environment and **has no default** — an unset variable makes `docker compose` refuse to start,
which is the point. A stack that silently brings up the wrong server produces failures that look
like client bugs.

This branch supplies them from **`images.env`**, next to `compose.yml`:

| variable | this branch (312.x) |
|---|---|
| `CHEMOTION_ELN_IMAGE` | `complat/chemotion:eln-3.1.4@sha256:f9eb18e2…` |
| `CHEMOTION_DB_IMAGE` | `ptrxyz/chemotion:db-3.1.2@sha256:97477d89…` |
| `CHEMOTION_STACK_SUFFIX` | `v3` |

**Mind the publisher.** `ptrxyz/chemotion` stops at 3.1.2 (May 2026); ELN 3.1.4 is
`complat/chemotion`. ComPlat published no `db-3.1.4`, so the DB image stays `ptrxyz` `db-3.1.2`,
the pairing ChemOrc's own 3.1.4 compose uses. Pinned 2026-11-23 at **v3.1.4** (`/about` reports
`Version: v3.1.4`). Bumping a digest is a deliberate, reviewed change: record the new digest
together with the `Version:` string `/about` then reports.

**After an ELN bump, remove the app volume** (`just stack-down`, then
`docker volume rm chemotion_app_v3`). The `eln` service mounts a named volume over
`/chemotion/app`, i.e. over the application code, and Docker fills a named volume from the image
only while it is empty: a new image over an old app volume runs the old ELN. `/about` tells you
which one is running.

To override an image for one run, set the variable in your shell: the shell environment wins over
`--env-file`.

```bash
CHEMOTION_ELN_IMAGE=some/other:image just stack-up
```

The v4 line's branch (`release/401.x`) sets its own values in its `images.env`.
