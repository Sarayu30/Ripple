# Ripple

### Know how your content lands before you post.

Ripple gives your content a rehearsal audience. Upload a short video or add a public link with its transcript or caption, describe who you want to reach, and explore how different **AI-simulated viewers** might respond. See what connects, why someone might scroll, and which edits are worth testing next.

![Ripple’s introduction with an animated audience illustration](docs/screenshots/01-landing.png)

**[Who it’s for](#who-is-ripple-for)** · **[Feature tour](#a-tour-of-ripple)** · **[Setup](#run-ripple-locally)** · **[First simulation](#your-first-simulation)** · **[Troubleshooting](#troubleshooting)**

## Who is Ripple for?

| You are… | Use Ripple to… |
| --- | --- |
| An Instagram creator | Explore whether a Reel’s opening, message, and call to action make sense to your intended audience. |
| A social media manager | Examine different audience perspectives before committing to a campaign concept. |
| A founder or marketer | Find where a product explanation needs clearer benefits or stronger evidence. |
| A creative strategist or agency | Compare proposed hooks, captions, and audience definitions using saved simulations. |
| A developer studying agent workflows | Inspect a working six-stage LangGraph pipeline, structured outputs, evidence references, and resumable checkpoints. |

Instagram and short-form content are the starting point. The interface also supports TikTok, YouTube Shorts, LinkedIn, and other public HTTPS links.

## What does it do?

**Your content → a simulated audience → individual reactions → audience patterns → suggested improvements → a version you can compare.**

Each viewer receives their own AI evaluation. Ripple combines those responses into an interactive audience map and evidence-grounded recommendations. You can ask follow-up questions, revisit saved work, and test a proposed change without overwriting the original simulation.

These are synthetic perspectives, **not real Instagram analytics, human research, or a promise of engagement**. Ripple helps you form and investigate creative hypotheses. It does not publish posts, scrape protected videos, or render replacement footage.

## A tour of Ripple

Screenshots containing results use **clearly labeled documentation fixtures**, not real predictions or private user content. Fixtures exist only in the browser test harness; the application has no fabricated-results mode.

### 1. Bring your content and define your audience

Upload MP4, MOV, or WebM, preview the selected video, and describe the intended audience and message. Alternatively, paste a public link and supply its transcript or caption. Choose a panel size and optionally include people outside your intended audience.

![Content upload, audience setup, and simulation controls](docs/screenshots/02-new-simulation.png)

- Start with **25 viewers** to keep the first run small. Larger panels increase API usage, not proven accuracy.
- Uploads are limited to **100 MB and 180 seconds by default**, configurable on the server.
- A link does not grant access to its video. Upload the original file for actual sampled-frame and audio analysis.
- Before submitting, the consent control explains which content is sent to Groq.

### 2. Explore the audience reaction map

Each dot is one simulated viewer. Select a dot to see the reaction, the reason behind it, its audience group, profile, and possible connections. Expand reasoning to inspect all returned engagement scores.

![Audience map with selected viewer, stage progress, insights, and recommendations](docs/screenshots/03-audience-map.png)

- **2D** provides an overview; **3D** lets you rotate the layout by dragging.
- Filter by target audience, outside audience, sharing, scrolling, negative reactions, or pending responses.
- Zoom, pan, reset, expand to fullscreen, or use **Tab + Enter** to select viewers.
- **Replay analysis** steps through saved events, with pause, scrubbing, speed controls, and a return to the latest reactions. Older records without events explain that replay is unavailable.
- Connections represent hypothetical sharing paths, not a real follower graph.

| Label | What it actually means |
| --- | --- |
| Simulated viewers | The number of viewers with returned reactions. |
| Message understood | Percentage of completed viewers with a clarity score of at least 70/100. |
| Would share | Percentage whose returned action is `share`. |
| Engagement / share intent scores | AI-stated intent scores, not calibrated probabilities of human behavior. |
| Evidence confidence | An evidence/completion heuristic capped at 75, not the probability a prediction is correct. |
| Target / outside audience | People the content is intended for / other simulated perspectives. |

### 3. Find the next edit and inspect the evidence

The Studio separates **what happened**, **why it happened**, and **what should I change?** The first recommendation is prominent; all remaining suggestions, alternative hooks, captions, CTAs, cover ideas, and creative variants are available in a drawer.

Expandable sections retain audience segments, full content diagnostics and scores, sharing scenarios, sampled source frames, version history, assumptions, evidence references, and AI execution activity. Download a creator-friendly Markdown report or export the full saved JSON.

### 4. Ask Ripple about your simulation

Ask why viewers scrolled, which segment responded differently, or what opening to try. Answers use scoped retrieval of the selected simulation and validated evidence references. Follow-up conversations are saved.

![Ask Ripple answering a question with saved evidence references](docs/screenshots/04-ask-ripple.png)

### 5. Test a change and compare versions

Choose an original simulation, change a hook, caption, CTA, audience, or describe a content variation, then approve the revised run. Each version keeps its own input, media copies, and results.

![Original and revised versions with metric changes, segment differences, and recommendations](docs/screenshots/05-compare-versions.png)

Content-only edits reuse the audience profiles while reevaluating responses. Audience changes regenerate the profiles. Comparisons expose changed assumptions and model variability; a positive score difference does not prove a real improvement. Described video edits are hypothetical—the uploaded video itself is not edited.

### 6. Return to your work, on any screen

**Your simulations** shows saved runs, dates, audience descriptions, status, and available verdicts. Reopen results, resume interrupted work, or delete a simulation with confirmation. **Library** collects creative directions and downloadable reports.

The interface supports dark and light themes, desktop/tablet/mobile layouts, keyboard navigation, and reduced-motion preferences.

<details>
<summary>See the light theme and mobile introduction</summary>

![Light-theme Studio](docs/screenshots/07-light-studio.png)

<img src="docs/screenshots/06-mobile-landing.png" width="320" alt="Ripple’s responsive mobile introduction">

</details>

## Run Ripple locally

You need:

1. **Python 3.11 or newer** and Git.
2. A **Groq API key** with access to suitable text, vision, and transcription models.
3. A **PostgreSQL database**. A Neon project works; keep the TLS parameters in its connection string.
4. **FFmpeg and ffprobe** on your PATH for uploaded-video analysis. They are not needed for transcript/caption-only link tests.

No Node installation or frontend build is needed to run Ripple. Node is only used for optional UI development checks.

### Windows PowerShell

```powershell
git clone --branch version_2 https://github.com/Sarayu30/Ripple.git
cd Ripple
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# New installations only. Preserve an existing .env.
Copy-Item .env.example .env
```

### macOS / Linux

```bash
git clone --branch version_2 https://github.com/Sarayu30/Ripple.git
cd Ripple
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# New installations only. Preserve an existing .env.
cp .env.example .env
```

### Configure your private `.env`

Open `.env` in your editor and fill in:

```dotenv
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
DATABASE_SCHEMA=ripple
```

Use the complete URL supplied by your database provider; keep any additional TLS parameters. Never commit `.env`. The connection string and Groq key stay on the server and are not returned to the browser. Do not put an API key in a model-name field.

The example also contains text, vision, and transcription model IDs. Verify that those models are available in your Groq account. **Provider setup** in the app checks the available model list without generating content.

### Start the app

```powershell
# Windows
.\.venv\Scripts\python.exe check_setup.py --database
.\.venv\Scripts\python.exe run.py
```

```bash
# macOS / Linux, with the virtual environment activated
python check_setup.py --database
python run.py
```

Open **http://localhost:8000**. Start from the introduction or jump directly to **http://localhost:8000/#studio**.

The first start creates Ripple’s tables in the configured PostgreSQL schema. If `data/ripple.sqlite3` exists, its history is imported transactionally once. Existing source records and local files are preserved. See [UPGRADE.md](UPGRADE.md) before updating an older installation.

### Docker alternative

Configure `.env` first, then run:

```bash
docker compose up --build
```

The image includes FFmpeg and the runtime agent skills. PostgreSQL is supplied through `DATABASE_URL`; Compose does not create a second database service. Local media and caches persist in the `ripple-data` volume. This volume is separate from a host installation’s `data/` directory—copy or mount existing data deliberately when moving installations.

## Your first simulation

1. Select **Simulate your audience** or **New simulation**.
2. Name the test and upload a video, or add a public link with transcript/caption.
3. Describe the target audience in plain language. Explain the one idea viewers should remember.
4. Choose a goal, publishing platform, and CTA. Keep **25 viewers** for the first run.
5. Review the consent text and run the simulation. Keep the server running.
6. Watch the analysis stages, then select a viewer to read their response.
7. Read the top edit, inspect its supporting evidence, and optionally create a what-if version.

Runs may take several minutes because Ripple makes separate provider requests and respects rate limits. It saves completed work instead of substituting scores when a request fails. Resume an interrupted or partial run from the Studio.

## How it works underneath

The actual LangGraph sequence is:

1. **Content Analysis** — sampled-frame, transcript, hook, and messaging evidence.
2. **Audience Research** — distinct target/outside audience profiles.
3. **Viewer Simulation** — separate bounded Groq calls and modeled exposure waves.
4. **Propagation Analyst** — deterministic sharing arithmetic with explicit assumptions.
5. **Insights Analyst** — patterns and disagreements grounded in saved source IDs.
6. **Creative Strategist** — three priority edits and alternative creative directions.

Ask Ripple uses a separate planning → scoped retrieval → grounded answer graph. Six allowlisted files under `skills/` are loaded at execution; their hashes are saved with results.

| Layer | Implementation |
| --- | --- |
| API | FastAPI, Pydantic, same-origin mutation checks |
| AI provider | Groq, paced requests, bounded retries, validated structured output |
| Orchestration | LangGraph, specialized stages, independent viewer contexts |
| Database | PostgreSQL / Neon, Psycopg, a bounded connection pool |
| Recovery | PostgreSQL checkpoints for new runs; preserved SQLite checkpoints for older runs; atomic JSON viewer caches |
| Media | FFmpeg/ffprobe; private local files, frames, and audio |
| UI | Build-free JavaScript, CSS, SVG network rendering |

See [ARCHITECTURE.md](ARCHITECTURE.md) for state flow, cache invalidation, persistence, and framework choices. [FEATURE_MAP.md](FEATURE_MAP.md) maps controls to implementation and checks.

## Data, privacy, and operating limits

- Simulation history/results and new graph checkpoints are stored in your PostgreSQL database. With Neon, that storage is remote.
- Uploaded media, sampled frames, JSON response caches, version metadata, and the local chat transcript remain under `DATA_DIR` (default `data/`). Back up **both PostgreSQL and this directory**.
- Groq receives submitted content context, sampled frames/audio when applicable, and audience descriptions. Provider retention follows your provider agreement.
- No account connection, real follower graph, actual retention measurement, or live social analytics is available.
- Sharing scenarios use uncalibrated assumptions: 6% sharing-intent realization, 0.65 wave decay, 65% within-cluster affinity, and four exposure waves. Engagement uses a separate 12% realization prior.
- The visual contact network has its own seed/delivery rules. Unreached viewers are independently evaluated as controls and do not count as cascade reach.
- This remains a **single-user, single-process workspace**. A polished UI and PostgreSQL do not provide multi-tenant authentication, a distributed job queue, or production SaaS operations. `APP_PASSWORD` is optional local workspace protection. The default server binds to `127.0.0.1`.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| PostgreSQL will not connect | Run `check_setup.py --database`. Check `.env`, database availability, network access, and TLS parameters. The check hides credentials. |
| Neon pooled URL | Ripple uses the corresponding direct Neon hostname with its own bounded pool, allowing session-specific schema selection and checkpoint setup. Your `.env` is not rewritten. |
| Video analysis fails immediately | Confirm `ffmpeg -version` and `ffprobe -version` work in the same terminal. Check file size and duration. |
| A link provides little evidence | Supply its actual transcript/caption or upload the original video. A public URL alone is not downloadable media access. |
| Groq model error | Open **Provider setup**, check available model IDs, update `.env`, then restart. |
| Rate limit or paused simulation | Wait for the provider cooldown, then choose **Resume simulation**. Keep concurrency low. Completed viewer responses are reused. |
| No reactions or incomplete suggestions | Read the surfaced error. Ripple does not fabricate missing work. Resume after correcting the issue. |
| Previous media missing after moving machines | Restore `DATA_DIR` as well as the database. PostgreSQL does not contain the uploaded video files. |

## Development and validation

Python integration tests run in a unique temporary PostgreSQL schema and remove that schema afterward. They use fixture providers, not paid Groq generations. The database role must be allowed to create a schema. Use a dedicated development database if preferred.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=artifacts/pytest-check
npm.cmd install --prefix artifacts/ui-check --no-audit --no-fund jsdom@30.1.1 playwright@1.58.2
node tests/frontend.cjs
node tests/browser.cjs
```

The browser suite uses installed Chrome, an isolated fixture HTTP server, and headless rendering. It checks the interactive flows and responsive layouts and refreshes the screenshots under `docs/screenshots/`. On macOS/Linux, use `python` and `npm` equivalents. Test tooling under `artifacts/` is not a runtime dependency.

See [VALIDATION.md](VALIDATION.md) for checks actually run and their limits.

## API and project guide

Existing API routes are retained:

- Configuration, provider availability, and source preview: `/api/config`, `/api/providers/groq/check`, `/api/preview`.
- Create/list/open/delete simulations: `/api/tests`, `/api/tests/{id}`.
- Resume, live network, private video/frames, and JSON export: `/api/tests/{id}/retry`, `/live`, `/video`, `/frames/{name}`, `/export`.
- Versions, comparisons, chat, and reports: `/api/tests/{id}/versions`, `/compare/{other}`, `/chat`, `/report`.

Mutation requests require `X-Ripple-Client: 1` and pass same-origin checks. Model keys and database credentials are never part of browser configuration.

| File / directory | Start here for… |
| --- | --- |
| `app/main.py` | API routes and request boundaries |
| `app/agents/` | Analysis, viewers, insights, strategy, and chat |
| `app/store.py`, `app/checkpoints.py` | PostgreSQL, migration, checkpoint recovery |
| `app/static/` | Landing page, workspace, network, and visual design |
| `skills/` | Runtime instructions for the six agent stages |
| `tests/` | Backend, DOM, and browser regression checks |

Visual inspiration: [Shift Studio by Elux Space](https://dribbble.com/shots/27104940-Shift-Studio-Digital-Agency-Hero-Animation). Ripple uses its own audience-network identity and implementation.
