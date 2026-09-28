# Ripple v3 — Skill-based Audience Agents

**Already using Ripple? Read [UPGRADE.md](UPGRADE.md) first. Keep your existing `.env` and `data` folder.**

V3 replaces single-shot viewer evaluation with independent, resumable agents. Each
agent discovers reviewed `SKILL.md` metadata, chooses a skill, reads evidence through
an allowlisted tool, and submits a validated reaction. The inspector shows actual
skill versions and tool activity. No frontend reaction generator exists.

Report synthesis uses **LangChain Deep Agents 0.7.18**: a coordinator plans with
`write_todos`, reads evidence, and delegates to an evidence reviewer and a creative
editor. All three share a bounded model-call budget. The final report still passes
Pydantic validation. Provider setup has moved out of the UI; edit `.env` and run
`python check_setup.py --groq` when needed.

See [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) for design decisions, research,
request budgets, checkpoint behavior, and how to add reviewed skills.


V2 adds the reference-video-inspired live network, target/outside-audience cohorts, clickable persona inspector, 2D/3D projection, playback of saved agent events, light/dark themes, private video playback, explicit provider errors, paced requests and model discovery. The original insights, recommendations, history, export and comparison remain available. See [FEATURE_MAP.md](FEATURE_MAP.md) for the reference-to-implementation mapping.

A runnable local AI audience-testing platform for short-form video. Light/dark dashboard, independent persona evaluations, private media ingestion, explicit sharing scenarios, durable test history, JSON export, and version comparison.

**No random/demo scores are used in the application. An API key is required to run a simulation.** The test suite uses isolated fake provider fixtures only.

## Quick start — Windows PowerShell

Install Python 3.11+ and FFmpeg. Ensure both `ffmpeg` and `ffprobe` are on PATH (restart your terminal after installing). FFmpeg is required only for uploaded videos; link/transcript tests can run without it.

```powershell
cd ripple
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
# Add GROQ_API_KEY=your_real_key and save, then:
.\.venv\Scripts\python.exe run.py
```

Open **http://localhost:8000**. No Node/npm setup is needed.

## macOS / Linux

Install Python 3.11+ and FFmpeg through your system package manager.

```bash
cd ripple
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GROQ_API_KEY
python run.py
```

## Docker option

Docker bundles Python and FFmpeg. Copy `.env.example` to `.env`, set your key, then:

```bash
docker compose up --build
```

Open http://localhost:8000. Docker exposes the port on loopback only. The named volume keeps your saved tests. Do not use `docker compose down -v` unless you intend to remove the database and all media.

## Configure providers

| Setting | Purpose |
|---|---|
| `AI_PROVIDER=groq` | Default selected provider; each test can override it |
| `GROQ_API_KEY` | Your Groq key, used only by the backend |
| `GROQ_MODEL` | Persona, synthesis and recommendation model; default `openai/gpt-oss-20b` |
| `GROQ_VISION_MODEL` | Frame analysis model; default `qwen/qwen3.8-27b` from current Groq vision docs |
| `GROQ_TRANSCRIPTION_MODEL` | Default `whisper-large-v3-turbo` |
| `GEMINI_API_KEY` | Optional Gemini key |
| `GEMINI_MODEL` | Default `gemini-2.5-flash`; Gemini handles text, frame analysis and audio transcription |
| `AGENT_MAX_TOOL_STEPS` | Tool-selection budget per persona; default 4, bounded 2–8, followed by one reaction call |
| `DEEP_MAX_MODEL_CALLS` | Shared coordinator/specialist call budget; default 24, bounded 8–40; one final formatting call |
| `AGENT_CONCURRENCY` | Concurrent LLM evaluations; default 1, capped at 10 |
| `REQUEST_INTERVAL_SECONDS` | Minimum spacing between request starts, default 4 seconds; shared per provider/key in the worker |
| `MAX_PROVIDER_ATTEMPTS` | Max attempts per structured request, default 4 |
| `MAX_COMPLETION_TOKENS` | Groq output budget, default 5000; GPT-OSS uses low reasoning effort |
| `MAX_UPLOAD_MB` | Default 100 MB |
| `MAX_DURATION_SECONDS` | Default 180 seconds |
| `DATA_DIR` | SQLite and private media directory; default `./data` |
| `APP_PASSWORD` | Optional local HTTP Basic password, any username |

Provider model availability changes and may differ by account. If a model is not available, use the provider console to choose a compatible model and update `.env`. Groq vision calls contain no more than three images per request. Supported Groq models use strict JSON-schema output. Other models use JSON object mode, and Gemini uses JSON MIME output. All outputs receive full local Pydantic validation. Provider schema bounds are validated locally. Retries include field-level validation feedback without echoing content or secrets. Keys are never placed in frontend code or returned by the configuration endpoint. Restart after editing `.env`.

## Your first simulation

1. Choose Upload or Public link and name the test.
2. Upload an MP4/MOV/WebM, or paste a public HTTPS URL.
3. For a link, **supply the real transcript or caption/description**. A URL alone is not enough evidence. For an uploaded silent video, a working vision model or supplied content text is required.
4. Define audience, goal, message, platform, CTA and panel size.
5. Review distribution assumptions and consent to sending content to the chosen AI provider.
6. Run the panel. Leave the server running. A 250-person panel can take many minutes and exceed free-tier quotas.
7. Explore individual responses, evidence limits, edits, audience segments and cascade assumptions.
8. Use **Test a new version** to copy audience/assumptions into a new test. Supply the edited video/transcript; then compare the two saved tests.

For a text/link test, each persona normally needs three tool-selection calls plus one reaction call (at most `AGENT_MAX_TOOL_STEPS + 1`). Add profile batches, one analysis call, and up to `DEEP_MAX_MODEL_CALLS + 1` report calls. Provider retries can multiply these counts. An uploaded video adds frame analysis batches and optional transcription. Running 250 personas means 250 independent agent runs, not one model response pretending to be 250 agents. Check your provider's current pricing and rate limits; see [VALIDATION.md](VALIDATION.md) for the current live-check results.

## How it works

```text
Browser → FastAPI → private ingestion → evidence analysis
        → audience profile generation → N isolated skill/tool loops
        → validated responses → score aggregation / cluster propagation
        → Deep Agents specialist synthesis → SQLite results → dashboard / comparison
```

- **Uploaded media:** ffprobe verifies the real video stream, duration and dimensions. FFmpeg extracts up to seven timestamped JPEG frames and mono audio. Opening, 1-second and 3-second frames are prioritized. Vision interprets on-screen text/captions and visual content; selected provider transcribes speech. The UI displays the actual sampled frames.
- **Limits of media analysis:** visual analysis is sparse, not continuous motion analysis. Pacing, scene descriptions and attention drop-off are hypotheses. Brief overlays or scenes can be missed; captions are model-inferred, not a guaranteed complete subtitle extraction. Audio is transcribed; there is no detailed sound-design analysis.
- **Links:** platform hostnames are validated. Official YouTube/TikTok oEmbed endpoints may supply title/author metadata. No embed HTML is rendered and no remote thumbnail is fetched. Instagram, LinkedIn and arbitrary URLs remain URL + supplied-context analysis; there is no protected scraping, cookie harvesting, login bypass or arbitrary URL download. The source preview includes an Open original link. Uploaded videos also have a private local playback endpoint, protected by the same optional workspace password.
- **Personas:** audience-tailored profiles contain background, motivation, skepticism and viewing context. Each viewer receives isolated context and has no access to other agents' answers. The required scores and reaction fields are extended with `understood`, `shareReason`, `confusion`, `emotion`, `wouldStop`, `wouldFinish`, `likeIntent` and `followIntent` to cover the requested questions.
- **Durability:** SQLite stores test metadata, status and final results. Atomic local JSON checkpoints preserve profiles, content evidence and completed evaluations. A restart marks running jobs interrupted. Click Retry to resume; successful persona calls are reused. Partial results are shown only when at least half the requested panel (minimum 5) completed. Failed agents are explicitly counted. Recommendation failures do not discard valid agent responses.
- **Privacy:** original videos, sampled frames, audio, transcripts and checkpoints live in `data/private`, not the static directory. Local same-origin endpoints serve frame previews. Delete a finished test to remove its files and database record. Provider retention is governed by your provider agreement; local deletion cannot delete provider-side records. There is no automatic retention expiry or at-rest encryption in this local edition.


## Live network and replay

The new Simulation Studio opens during processing and stays available after completion. Each dot is an actual generated persona profile, with a separate model inference for its reaction. Profiles are grouped by intended versus outside audience. Colors update only after real returned reactions; failed requests have a separate state. Click or keyboard-select a node to inspect its profile, understanding, action, reasons to share, objection, and recommended edit.

The layout itself is deterministic geometry so it remains stable while inspecting. This does not generate scores. The 3D mode projects the same graph with depth and lets you rotate it; it does not add extra people or rerun models. Zoom, reset, action/cohort filters and a hover card are available.

For new tests, approximately 16% of profiles receive seed exposure, stratified across archetypes. A returned share response can expose assumed contacts in the next wave, for up to four waves including the seed. A weighted share × relevance × sentiment index must reach .28 and the agent must either choose `share` or have share intent of at least 60. Up to three contacts are exposed, with similar-archetype links and explicit cross-cohort bridges. All contacts and thresholds are assumptions. This is not a reproduction of Instagram's private algorithm.

Unreached viewers are independently evaluated as direct-test holdouts. Their opinions remain useful for feedback and target/outside comparison, but they do **not** count as cascade reach. The graph's finite-panel reach is shown separately from the original wider exposure-range sensitivity model in Insights. Scores in the original report summarize the combined panel; the Studio also shows cohort-specific relevance and share intent.

Replay reveals saved agent events. Its speed/slider change presentation only and make no AI calls. Summary metrics below the graph remain the final run totals while replay is active. Replaying an old run never invents missing historical events. No reference-video assets, reference participants, or Guildly features are bundled.

## Provider reliability and diagnostics

- Default Groq text model is `openai/gpt-oss-20b`; configurable per `.env`.
- Model configuration validates common paste errors: keys accidentally put in model fields and comments attached to model IDs.
- Calls are paced (4 seconds by default), with a shared cooldown per provider/key. Numeric/date Retry-After is honored. A reset longer than 180 seconds pauses rather than retrying early.
- Permanent HTTP errors and exhausted 429 retries pause remaining new persona requests. Invalid JSON receives a bounded retry with field-level correction. Full successful responses are checkpointed atomically.
- The activity feed and errors panel show provider/model/status/error code. Raw provider messages and failed-generation bodies are not displayed because they can echo private content.
- `python check_setup.py` performs local checks without printing keys. `python check_setup.py --groq` queries Groq's official model list. It makes no generation request and cannot guarantee all account permissions/capabilities.
- Automated tests use isolated model fixtures, not a production demo fallback. See VALIDATION.md for live provider checks and remaining limits. Prediction quality is not empirically validated.

## What the numbers mean

All outcomes are **AI-modeled estimates, not guaranteed platform performance or real historical analytics**. Synthetic personas are not representative human participants. Separate requests to the same base model can have correlated biases.

- Scores are arithmetic means of completed agents' stated subjective judgments (0–100), not measured probabilities.
- Verdict: relevance below 45 → Low relevance; otherwise hook below 55 → Needs stronger hook; otherwise hook, relevance and share intent all at least 75 → Strong niche hit; otherwise Promising.
- Sharing propensity per segment = mean of `shareIntent/100 × relevanceScore/100 × sentimentFactor`. Sentiment factors: positive 1, mixed .75, neutral .65, negative .35.
- New exposures = current exposures × propensity × **.06 intent-realization prior** × contacts per share × **.65^depth**. A **.65 within-segment affinity** plus **.35 panel-weighted cross-segment allocation** produces the cluster network. The export includes the complete edge list; the dashboard shows wave totals and segment fit.
- Reach range = seed × .6–1.4 plus secondary exposures × .3–2.0. This is an uncalibrated sensitivity envelope, not a statistical interval. Exposures are not deduplicated unique people; platform ranking and real account follower graphs are absent.
- Engagement rate = average maximum like/save/comment/share/click intent × **.12 realization prior**. This is a transparent heuristic, not a learned platform probability.
- Confidence = `(15 + evidencePoints × .6) × completed/requested`, capped at 75. Evidence points: metadata 25, vision 30, transcript 25, caption 10, oEmbed 10. This measures available input and execution completeness, not probability of accuracy. Confidence can be lower for incomplete or link-only analysis.
- Panel size explores more opinions but does not supply empirical validation, representative sampling, or narrower statistical uncertainty.

All coefficients are visible in `app/simulation.py`, the Method page, and each result's exported assumptions. Use actual published outcomes and real human feedback to calibrate before using these numbers for spend or forecasting decisions. No guaranteed uplift is shown.

## Architecture / files

```text
ripple/
  .env.example          Server configuration template
  requirements.txt      Pinned Python dependencies
  run.py                Loopback-only local entry point
  check_setup.py        Local checks and optional --groq model discovery
  UPGRADE.md            Preserve your existing key and saved tests
  FEATURE_MAP.md        Visible reference features and implementation notes
  Dockerfile            Optional Python + FFmpeg container
  compose.yaml          Local Docker setup and durable volume
  app/
    main.py             API, upload limits, security middleware, job lifecycle
    schemas.py          Input, analysis, persona and recommendation validation
    providers.py        Groq / Gemini adapters, JSON retries and transcription
    media.py            FFmpeg extraction, URL validation and official oEmbed
    simulation.py       Independent evaluations, checkpoints and wave orchestration
    network.py          Synthetic topology, sharing rules and cohort statistics
    store.py            SQLite persistence
    static/
      index.html        Application shell
      styles.css        Responsive dark interface, no external assets
      app.js            Form, reports, history and comparison
      network.js        Interactive SVG renderer: selection, zoom, pan and 3D projection
      studio.js         Live workspace, inspector, event replay and themes
      studio.css        Reference-inspired studio and light-theme styling
  tests/
    test_core.py        Security, media and isolated simulation tests
    test_v2.py          Network, strict output, error privacy and quota regression tests
  RESEARCH.md           Sources and supplied-video provenance
```

## API

`GET /api/config`, `POST /api/preview`, `GET/POST /api/tests`, `GET/DELETE /api/tests/{id}`, `POST /api/tests/{id}/retry`, `GET /api/tests/{id}/export`, `GET /api/tests/{id}/frames/{name}`, `GET /api/tests/{id}/live`, `GET /api/tests/{id}/video`, and `POST /api/providers/groq/check`.

Mutation requests require the `X-Ripple-Client: 1` header and same-origin browser context. Creation accepts multipart `payload` (TestInput JSON (now also `outsidePercent` 0–50 and optional `outsideAudience`)) plus optional `video`. Built-in API docs are disabled. The app accepts only loopback/test hostnames by default. This is intentionally a single-process server; do not start multiple Uvicorn workers against its in-memory job registry.

## Tests

```bash
python -m pytest -q
```

FFmpeg is needed for the real ingestion test. Tests use a temporary data directory and do not call live providers. They verify score bounds, independent per-persona calls, partial failures, checkpoint resume, URL validation, cross-origin protection, password checks, nonpublic storage and actual media extraction.

## Deployment readiness — honest scope

This is a complete local implementation, **not a certified production-ready multi-tenant SaaS**. It has useful production-oriented foundations: bounded file/request sizes, strict schemas, provider timeouts, retries, file isolation, same-origin checks, private data paths, SQLite durability and checkpoints. Before public commercial deployment, add and validate:

- Real account authentication, per-user authorization and tenant isolation on every test/media route.
- Durable distributed queue and workers, cancellation, scheduling, per-account budget/rate limits and idempotency.
- TLS, encrypted object storage, encryption at rest, managed secrets and restrictive storage permissions.
- Malware/content inspection and strongly isolated FFmpeg workers. Keep FFmpeg/dependencies patched.
- Central observability with redacted logs, retention policies, deletion/export guarantees and provider data agreements.
- Backup/restore procedures, load tests, dependency/security scanning and operational monitoring.
- Measured calibration against actual audience studies and platform outcomes; explicitly version coefficients and prompts.

The optional Basic password protects a local workspace, not separate users. Media processing uses restricted input protocols and subprocess timeouts but is not a complete hostile-file sandbox. Use only trusted uploads in this local edition. Do not expose port 8000 directly to the internet.

## Troubleshooting

- **Missing key:** edit `.env` in the project root and restart. Do not paste keys in the web UI.
- **401/403 from provider:** check key/model permissions and account status.
- **429 or slow panel:** reduce `AGENT_CONCURRENCY` to 1, wait for quota and Retry. Saved successful calls are reused.
- **Vision unavailable:** verify `GROQ_VISION_MODEL`. Supply transcript/caption to allow explicitly limited text-based evaluation, or use Gemini.
- **FFmpeg missing:** check `ffmpeg -version` and `ffprobe -version` in the same terminal, or use Docker.
- **Invalid video:** confirm MP4/MOV/WebM, under the size/duration limit, and at most 4K frame dimensions. File extension alone is never treated as validation.
- **Server restarted:** open the interrupted test in Test library and Retry.
- **Need full analysis of a link:** upload your authorized original video; no restricted media scraping is provided.
