# Validation performed

## Public introduction and account UX — October 21

- Anonymous visitors see the feature introduction with top-right sign-in/signup actions. Account dialogs support keyboard dismissal; protected CTAs open signup and do not fetch workspace records.
- Seven authentication tests cover public entry, rejected credentials, unverified accounts, recovery, session renewal and network failures. Build, UI and deployment tests passed. Chrome verified guest navigation at 390/768/1440px and the existing workspace suite passed 32 responsive checks. Public introduction and account screenshots were reviewed.
- The user's reported sign-in HTTP 401 remains an external account diagnosis: no password was collected, account modified, or verification bypassed. Live email delivery and successful sign-in with that account remain unverified.

## Authentication startup fix — October 20

- Reproduced the deployed login failure in isolated Chrome: CSP blocked Neon's `/get-session` because the allowed URL lacked the trailing slash required for endpoint paths. Both website and backend policies now allow paths beneath the configured Auth base URL.
- Build, five authentication flow tests, two deployment tests and the bundled SDK Chrome test passed. The browser test now applies the actual generated CSP. A read-only anonymous check against the live Neon tenant displayed sign-in with the corrected policy; no accounts or emails were created.
- Session lookup failures now preserve the login/signup form and keep the workspace locked. This does not establish that real signup, verification delivery or recovery has passed live acceptance.

Updated: 2026-10-19. The sections below distinguish automated checks from live deployment acceptance.

## Temporary media and free-cloud preparation — October 18

- October 19: [GitHub release checks passed](https://github.com/Sarayu30/Ripple/actions/runs/39199133662) for commit `cedb385`: **56 Python tests passed** against disposable PostgreSQL, plus frontend build, UI, authentication, deployment security and browser checks (32 responsive checks). The deployment test now creates its artifact directory on fresh checkouts.
- Local Neon reruns failed after a dropped connection, DNS resolution errors and an unreachable network; they are not counted as passes. The successful GitHub run verifies the application independently of that local connectivity failure. Render-to-Neon connectivity still needs the deployed health check below.
- `npm run build`, `test:ui`, `test:auth`, `test:auth-browser`, `test:deploy`, and `test:browser` passed. UI checks cover saved upload records without requests for deleted images or video. The browser suite passed 32 responsive checks and refreshed the README screenshots; the new-input and account screenshots were visually reviewed.
- All 10 standalone configuration/authentication unit tests passed, including production startup with a temporary directory and required origin/authentication safeguards.
- The configured database URL, provider key, origin secret and local password were compared against tracked/new deployment files without printing their values; no matches were found. `.env` remains ignored and untracked.
- Render's Docker runtime, Free plan, health-check and automatic-deployment settings were checked against its current Blueprint documentation. No paid service or disk was created. Docker is not available in this local environment, so the actual container build and public-domain acceptance must be checked on Render.
- Browser auth checks use fixtures. Actual signup, verification/recovery email delivery, Vercel-to-Render routing, uploaded-video processing on Free compute, and browser cookie compatibility still need live acceptance checks after deployment.

## Workspace contrast and page review — October 12

- `npm run build`, `npm run test:ui`, and `npm run test:browser` passed.
- The browser suite now checks all eight main pages at 390px and 768px in both light and dark themes: **32 responsive overflow checks**.
- New assertions verify the inspector's three saved-profile shortcuts, keyboard activation, focus on the selected viewer name, and the dark network surface in both themes. Existing replay, filters, 2D/3D, pan/zoom/fullscreen, chat, experiments, comparisons and draft handoff checks still pass.
- Thirteen fixture screenshots were regenerated and visually reviewed, including history, Library, method, provider setup and a mobile map. They are embedded in the README walkthrough.
- No JavaScript page errors were recorded. Motion-enabled and reduced-motion browser paths both passed. This remains functional and visual verification, not a formal accessibility audit.
- No backend/database implementation changed; no production record, private media or `.env` value was read or altered for these captures. No paid Groq calls were made. The Python suite was not repeated for this frontend-only change.

## React redesign verification — October 9

- `npm run build` passed. The committed React/Motion bundle, stylesheet, fonts and license files build from the pinned lockfile. `npm install` reported zero dependency vulnerabilities at installation time.
- `npm run test:ui` passed with the real React bundle loaded in jsdom, alongside the existing dispatcher, SVG renderer and workspace scripts.
- `npm run test:browser` passed in headless Chrome. New assertions cover draft text/source handoff, attached-file transfer and preview, live brief changes, audience-lens keyboard controls, saved content-ribbon details and light/dark themes.
- Existing map, 2D/3D, zoom, pan, fullscreen, filters, replay cutoff, inspector, diagnostics, suggestions, chat, approved version creation and comparison checks still pass. All 16 responsive overflow checks pass at 390px and 768px.
- A separate browser context starts with motion enabled and verifies the ambient animation and pause control. Screenshot contexts use reduced motion. No JavaScript page errors were captured.
- Eight updated screenshots were captured from the isolated fixture server and visually reviewed. They contain no private media, real user results, database credentials or paid provider calls.
- No backend or database implementation changed in this UI pass; the Python suite was not repeated. No new real-provider simulation, deployment or Docker image build was performed.

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

Eight PNG screenshots under `docs/screenshots/` show the introduction, input setup, audience Studio, Ask Ripple, comparison, mobile introduction, light Studio and dark Studio. Result screenshots are labeled documentation fixtures. The fixture server reads no production database, `.env`, private content or provider credentials. It cannot run paid model calls.

CSS reduced-motion rules disable decorative movement; the browser captures and checks run with reduced motion enabled. This is not a formal accessibility audit, screen-reader certification, cross-browser matrix or touch-device usability study.

## Earlier provider verification

The 2026-10-04 validation record documented a real 25-viewer Groq text/transcript run, all six stages, saved provenance and evidence-grounded chat, including rate-limit/schema recovery and a live legacy-citation fix. Those are historical checks, not a fresh real-provider run of this redesign. Real-provider frame vision and audio transcription were not separately exercised in this session.

## Deployment limits

Docker configuration was reviewed; an image build was not run. The backend runs as one process, with account-scoped records and Neon Auth. Public signup and cross-account isolation still require live deployment acceptance. Distributed jobs, load testing, disaster recovery drills and predictive calibration have not been validated. New runs store textual caches and workflow state in PostgreSQL; media is temporary. Older SQLite workflow checkpoints require their original disk for exact-stage recovery.

## Reproduce

Use the commands in [README.md](README.md#development-and-validation). Supply a development PostgreSQL URL if you prefer a separate database; the role needs schema-creation rights. Keep tracebacks short to avoid displaying connection internals. `node tests/browser.cjs` uses installed Chrome, serves isolated fixtures, runs interaction/responsive checks and refreshes the public screenshots.
