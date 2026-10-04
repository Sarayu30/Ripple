# Ripple — audience intelligence Studio

Understand who connects with your content, why others scroll, and what to change before you publish.

Ripple is a single-workspace FastAPI application using Groq, LangGraph, Pydantic, SQLite and a build-free JavaScript frontend. Results come from actual saved model responses. Synthetic viewers and sharing scenarios are exploratory, not calibrated forecasts.

## Start locally

Python 3.11+ is required. Install FFmpeg and ffprobe for uploaded videos.

Windows PowerShell:

~~~powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Only for a NEW installation; preserve an existing .env:
Copy-Item .env.example .env
# Put your Groq key in .env, then:
.\.venv\Scripts\python.exe run.py
~~~

macOS/Linux:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Only for a NEW installation:
cp .env.example .env
python run.py
~~~

Open http://localhost:8000. No Node installation or frontend build is needed to run the product.

For an existing installation, preserve both `.env` and `data/`, install the updated requirements, then restart. Existing SQLite records and JSON results remain readable; the upgrade does not rewrite old results. See [UPGRADE.md](UPGRADE.md).

Docker: `docker compose up --build`. The image includes runtime skills; private data persists through the configured volume.

## Studio

- Three compact KPIs: completed synthetic viewers, message understood, and would share.
- Message understood means clarity score ≥70 among completed viewers. Would share means the returned action is `share`; neither is a probability of real behavior.
- Circular network nodes, selection, hover details, highlighted connections, zoom, pan, keyboard selection, cohort/reaction filters and fullscreen.
- A contextual inspector with Thoughts, Profile and Connections tabs.
- One priority edit, with remaining suggestions in a drawer.
- Expandable audience segments, simulation details, version history, assumptions, source evidence and execution trace.
- My Simulations provides saved runs, retries and confirmed deletion. Library collects creative directions and Markdown reports.
- Dark navy/lime styling, responsive layouts, light-theme toggle, empty/loading/error states and modal focus handling.

Graph connections are synthetic sharing possibilities, never a real follower graph. Green represents engagement, orange sharing, blue-gray undecided/scrolling and red negative sentiment. Pending viewers have no invented reaction.

## Agent workflow

The actual LangGraph sequence is:

1. Content Analysis: sampled-frame and transcript evidence, hook and messaging analysis.
2. Audience Research: distinct target/adjacent profiles, generated in validated batches.
3. Viewer Simulation: independent Groq calls, bounded parallelism, modeled exposure waves and separate unreached controls.
4. Propagation Analyst: deterministic arithmetic using declared assumptions.
5. Insights Analyst: patterns and segment disagreements with validated evidence IDs.
6. Creative Strategist: three priority edits, alternative hook, caption, CTA and variants grounded in feedback.

Each graph stage persists to a per-simulation SQLite checkpoint. Atomic JSON caches additionally preserve individual viewer responses, so interruption inside a stage does not repeat successful evaluations. Resume retries the pending stage; completed partial runs reuse responses and refresh downstream insights. Provider failures never produce substitute scores.

Instructions are loaded at execution from six allowlisted `skills/*/SKILL.md` files. Their hashes are saved with results. See [ARCHITECTURE.md](ARCHITECTURE.md) for state, tools, cache invalidation and framework decisions.

## Ask Ripple

The drawer uses a separate LangGraph: structured tool planning → scoped retrieval → grounded answer. The model selects up to four read-only tools for saved results, audience analytics, segment comparison, parent-version comparison, content evidence and recommendations. Evidence citations are checked against the run's source IDs. Follow-up history is retained locally and bounded in the model context.

The assistant cannot publish, modify files arbitrarily or access unrelated simulations through tool arguments. Its suggestions can be tested through an explicitly approved what-if version.

## What-if versions

Choose a baseline under Compare Versions, then change the opening hook, caption, CTA, target audience or describe a video/content variation. Confirm the revised simulation to send its context to Groq.

- Hook/caption/CTA/content edits reuse personas and extracted media, but rerun analysis and all viewer responses.
- Audience-only changes reuse content analysis and media, regenerate personas, then rerun reactions and downstream work.
- A child receives its own immutable payload, private media copies, checkpoints and parent/root metadata.
- Text variations are hypothetical proposals; Ripple does not edit or render a new video.
- Comparisons show score deltas, shared-persona status, changed assumptions, segment reactions, objections and recommendation differences. No automatic improvement claim is made.
- Reports contain actual stored insights, segment breakdown, objections, creative edits, comparison where available, evidence and limitations.

## Provider configuration and recovery

Keep keys in `.env`; never paste them into a model-name field. Start with the example text/vision/transcription model IDs and verify availability for your account. The existing provider adapter retains paced requests, shared rate-limit cooldowns, bounded retries and safe errors. It honors long Retry-After values by pausing.

If a model rejects strict structured output, Ripple retries JSON mode with the complete schema and still validates every output with Pydantic. The fallback is recorded in the trace and remembered per provider instance/schema. Repeated HTTP 400 failures stop viewer evaluation after three failures; exhausted rate limits pause immediately. A retry reuses completed work.

A text/link simulation generally needs `N + ceil(targetN/5) + ceil(adjacentN/5) + 3` requests before retries. Uploads add frame batches and optional transcription. Chat normally needs two model requests. Larger audiences increase usage, not proven accuracy. Start with 25 viewers and concurrency 1.

Link analysis uses supplied transcript/caption and permitted preview metadata. It does not download arbitrary remote media or scrape protected platform content. Upload a video for actual sampled-frame analysis.

## Assumptions

The aggregate propagation scenario uses a 6% sharing-intent realization prior, 0.65 wave decay, 65% within-cluster affinity and four exposure waves. Engagement uses a separate 12% realization prior. These are explicit, uncalibrated assumptions. Exposure opportunities are not deduplicated unique viewers. Confidence is an evidence/completion heuristic capped at 75, not a probability of accuracy.

The visual network is a separate synthetic contact scenario: approximately 16% initial seeds, a weighted sharing threshold of 0.28, up to three contact deliveries per viewer and four waves. Unreached viewers receive independent control evaluations and do not count as cascade reach.

## API

Existing routes remain compatible:

- `GET /api/config`, `POST /api/providers/groq/check`, `POST /api/preview`
- `GET/POST /api/tests`, `GET/DELETE /api/tests/{id}`
- `POST /api/tests/{id}/retry`
- `GET /api/tests/{id}/live|video|export`, `GET /api/tests/{id}/frames/{name}`

New routes:

- `POST /api/tests/{id}/versions`: validated edits plus `approved: true`.
- `GET /api/tests/{id}/compare/{other}`: stored comparison.
- `GET /api/tests/{id}/versions`: related project versions.
- `GET/POST /api/tests/{id}/chat`: saved conversation / grounded question.
- `GET /api/tests/{id}/report`: downloadable Markdown report.

Mutation requests require `X-Ripple-Client: 1` and same-origin checks. Media is outside static assets. Model credentials never appear in browser configuration. Uploaded files and request bodies are bounded. An optional APP_PASSWORD protects this local workspace, but does not provide multi-tenant authorization.

## Validation

~~~powershell
New-Item -ItemType Directory -Force artifacts
.\.venv\Scripts\python.exe -m pytest -q --basetemp=artifacts/pytest-check
npm.cmd install --prefix artifacts/ui-check --no-audit --no-fund jsdom@30.1.1
node tests/frontend.cjs
~~~

The JS test dependency lives in ignored artifacts and is not a runtime dependency. Use a fresh pytest basetemp path if Windows permissions prevent reusing an older folder. Tests use isolated fixture providers and never insert demo results into the production library. See [VALIDATION.md](VALIDATION.md) for actual checks and limits.

## Deployment scope

This is a local single-user product, not a public multi-tenant service. Public hosting needs identity/tenant isolation, a durable job queue, quotas, encrypted storage, monitoring and backups. One process coordinates local jobs and provider pacing. Restart recovery is user-triggered via Resume.

Deep Agents and MCP were evaluated but not installed: this bounded workflow already has planning, scoped tool dispatch, persisted state, isolated viewer contexts and human-approved version creation. No external service requiring MCP is part of this product. LangGraph is the actual orchestration framework; no unsupported autonomous capabilities are claimed.
