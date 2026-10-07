# Upgrading Ripple to PostgreSQL and the redesigned Studio

## Before you start

1. Stop the existing Ripple server so an older SQLite-backed process cannot keep writing during migration.
2. Back up your entire `data/` directory and preserve `.env`. Keep the backup outside the working copy if possible.
3. Pull the `version_2` branch and install the updated requirements in your existing virtual environment.
4. Add your PostgreSQL connection string as `DATABASE_URL` in `.env`. Keep the TLS options supplied by Neon or your database host. Do not overwrite your Groq settings.
5. Optionally set `DATABASE_SCHEMA` (default `ripple`). The database role needs permission to create that schema and its tables.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_setup.py --database
.\.venv\Scripts\python.exe run.py
```

On macOS/Linux, use `python` from your activated virtual environment.

## What migration does

- Creates history and LangGraph checkpoint tables in PostgreSQL.
- Imports existing records from `DATA_DIR/ripple.sqlite3` in a single transaction. IDs, input payloads and stored results are retained.
- Records a migration marker only after a successful import. Subsequent starts do not import again or resurrect deleted records.
- Leaves the original SQLite file untouched. Conflicting IDs or invalid JSON abort the import instead of replacing records.
- Marks queued/running records interrupted at startup, as before. Use **Resume simulation** to continue them.

There is no SQLite fallback for new history writes. A missing/unavailable PostgreSQL database must be configured or restored before the workspace starts.

## What stays on disk

Keep `DATA_DIR/private/`. Uploaded videos, sampled frames/audio, per-viewer JSON caches, source context, version metadata, and local conversation transcripts are still stored there.

Existing `workflow.sqlite` and `chat.sqlite` files continue to serve older runs so exact-stage recovery is preserved. New runs use PostgreSQL checkpoints. Do not delete legacy checkpoint files while you still need those saved runs.

Back up **both the PostgreSQL database and `DATA_DIR`**. Restoring one without the other produces an incomplete workspace.

## What changes in the interface

- `/` opens the introduction. Use `/#studio` for direct workspace access.
- The Studio exposes 2D/3D views, saved-event replay, filters, and an expanded viewer inspector.
- Full scores, source evidence, assumptions, content diagnostics and AI activity remain accessible through disclosures and drawers.
- Your simulations, Ask Ripple, version comparison, what-if creation, Library, reports, JSON exports, retries and confirmed deletion remain available.
- Older results do not gain invented provenance, events or parent lineage. Replay is unavailable when no saved event history exists.

## Neon and Docker

For Neon pooled URLs, Ripple internally uses the corresponding direct endpoint with a bounded application pool so schema selection and checkpoint setup work. Your `.env` stays unchanged.

Docker users must rebuild the image. Compose uses the external PostgreSQL URL from `.env` and the existing named media volume. That volume does not automatically contain files from a host `data/` directory; migrate or mount the local files when moving an installation.

## Rollback

The old SQLite database remains a snapshot from before migration. It does **not** contain simulations created or modified afterward in PostgreSQL. Rolling application code back does not synchronize those newer records. Preserve both databases and media before any rollback, and export newer results first if you need them outside PostgreSQL.

See [ARCHITECTURE.md](ARCHITECTURE.md) for checkpoint recovery and [VALIDATION.md](VALIDATION.md) for checks performed.
