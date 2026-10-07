# Validation performed

Updated: 2026-10-07.

## PostgreSQL and backend

- Full Python regression suite: **33 passed** after the storage migration (571.17 seconds). Tests used an isolated PostgreSQL schema on the configured Neon database and fixture AI providers.
- After history-summary and deletion refinements: **6 targeted tests passed** (82.10 seconds), covering migration, rollback, schema validation, history summaries, HTTP boundaries, and upgrade API contracts.
- Final storage/isolation suite: **5 passed** (67.78 seconds), including an additional legacy SQLite checkpoint recovery test. The current suite has two more tests than the first full run; the full suite was not rerun just to duplicate those targeted checks.
- New-run checkpoint recovery resumes a failed graph stage without reevaluating completed viewers. The added legacy test exercises the same interruption/resume path with an existing SQLite checkpoint while history remains in PostgreSQL.
- Migration checks preserve exact payload/result data, leave SQLite bytes unchanged, and prove a deleted record is not resurrected by repeated import.
- Database tests run in a generated `ripple_test_*` schema. `DATA_DIR` is set before collection to an isolated directory under ignored `artifacts/`, including when only one test file is selected. The schema is removed after the session. Recognizable unreferenced media left by an earlier test-isolation iteration was moved into ignored artifacts; existing saved simulations were excluded.
- Existing independent-call, partial-recovery, cache invalidation, approved-version, comparison, report, chat scoping, citation validation/repair, provider failure, rate-limit, schema, URL, HTTP security, propagation and legacy-result checks passed.
- Real FFmpeg ingestion created a test video and verified metadata, sampled frames and extracted audio.

## Existing workspace migration

- Connected to the configured Neon database without changing `.env`.
- Imported and verified **one existing simulation**. Every stored input payload and result matched its SQLite source; the source file remained byte-for-byte unchanged.
- Private media and existing legacy checkpoints were preserved.
- A read-only smoke check against the migrated record passed the actual FastAPI routes for saved history/results, live network data, JSON export, local chat history, related versions and Markdown report. New frontend assets all returned successfully.
- `check_setup.py --database` reported a successful connection with credentials hidden. FFmpeg and ffprobe were available.
- No new paid Groq simulation or chat request was made during this redesign verification.

## Browser and visual verification

The jsdom integration suite passed introduction/empty-state navigation, new-input tabs, three KPIs, circular graph nodes, inspector tabs/connections, project history, full diagnostics, suggestions, grounded chat, approved what-if submission, comparison, Library and saved history.

The headless Chrome suite passed:

- Introduction CTAs and workspace navigation.
- Upload-preview controls/object URL creation and link/transcript disclosure. The preview test uses a minimal file fixture to check controls, not video decoding; FFmpeg decoding is tested separately.
- 25 rendered fixture viewers, target/outside and negative filters, accessible labels, keyboard selection, inspector reasoning and connections.
- 2D/3D switches, scroll zoom, pan, reset and fullscreen entry/exit.
- Replay scrubbing and return to latest; the inspector does not reveal future reactions during a historical cutoff.
- Full analysis, all recommendations, saved-source chat, approved revised-version submission and comparison output.
- Light/dark toggle, native dialog Escape behavior, and absence of JavaScript page errors.
- **16 horizontal-overflow checks** covering eight main pages at 390px and 768px, in addition to 1440px desktop captures.

Seven PNG screenshots under `docs/screenshots/` were rendered and visually reviewed: introduction, input setup, audience Studio, Ask Ripple, comparison, mobile introduction and light Studio. Result screenshots are labeled documentation fixtures. The fixture server reads no production database, `.env`, private content or provider credentials. It cannot run paid model calls.

CSS reduced-motion rules disable decorative movement; the browser captures and checks run with reduced motion enabled. This is not a formal accessibility audit, screen-reader certification, cross-browser matrix or touch-device usability study.

## Earlier provider verification

The 2026-10-04 validation record documented a real 25-viewer Groq text/transcript run, all six stages, saved provenance and evidence-grounded chat, including rate-limit/schema recovery and a live legacy-citation fix. Those are historical checks, not a fresh real-provider run of this redesign. Real-provider frame vision and audio transcription were not separately exercised in this session.

## Deployment limits

Docker configuration was reviewed; an image build was not run. The app remains single-user and single-process. Public multi-tenant deployment, distributed jobs, load testing, disaster recovery drills and predictive calibration are outside this change. Neon stores database data remotely, while media and JSON caches still require local persistence and backups.

## Reproduce

Use the commands in [README.md](README.md#development-and-validation). Supply a development PostgreSQL URL if you prefer a separate database; the role needs schema-creation rights. Keep tracebacks short to avoid displaying connection internals. `node tests/browser.cjs` uses installed Chrome, serves isolated fixtures, runs interaction/responsive checks and refreshes the public screenshots.
