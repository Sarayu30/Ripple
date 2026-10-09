# Ripple implementation architecture

## Runtime boundaries

FastAPI owns request validation, same-origin checks, bounded uploads, job admission and local workspace authentication. Simulation history lives in PostgreSQL; existing SQLite history is imported without modifying its source. Private-media paths are preserved. React and Motion power the introduction and contextual workspace components; the existing JavaScript dispatcher and SVG network retain the simulation behavior. Built assets are committed, so running the Python app requires no Node installation.

- `app/agents/orchestrator.py`: typed LangGraph state, six specialized stages, durable checkpoints, progress and execution trace.
- `app/store.py`: bounded Psycopg connection pool, PostgreSQL history, transactional legacy import, and deletion of associated PostgreSQL checkpoint rows.
- `app/checkpoints.py`: PostgreSQL saver with asynchronous thread offloading; preserved per-run SQLite savers for legacy recovery.
- `content.py`, `audience.py`, `viewers.py`: original Groq/media behavior extracted into specialized modules.
- `analytics.py`: deterministic propagation, segment summaries, provenance registry and citation validation.
- `insights.py`, `strategist.py`: structured evidence-grounded interpretation and creative recommendations.
- `skills.py`: allowlisted runtime skill discovery and content hashes.
- `tools.py`, `chat.py`: model-selected read-only tools and conversational LangGraph.
- `experiments.py`: immutable child runs, cache reuse/invalidation and saved-result comparison.
- `reports.py`: creator-ready Markdown built from stored outputs.
- `schemas.py`: strict Pydantic models including experiments, insights, tool plans and chat.
- `frontend/experience.jsx`: React introduction, draft/file handoff, live creative brief, content context ribbon, and Lucide navigation icons.
- `frontend/experience.css`: rose/apricot/charcoal design, local variable fonts, responsive layouts, ambient motion and light/dark workspace themes.
- `frontend/build.mjs`: esbuild bundles React/Motion into `static/experience-react.js` and CSS; copies local fonts and their licenses. No browser CDN requests are required.
- `static/landing.js`, `redesign.css`: fallback introduction and retained component layout foundation.
- `static/studio.js`, `workspace.js`, `network.js`, `experience.js`: Studio, drawers, experiments, 2D/3D network, replay, and full diagnostic access. Earlier stylesheet layers remain for compatible component layouts.

## State and recovery

SimulationState contains the immutable input row plus context, analysis, profiles, reactions, failures, response audits, outcome, provenance, insights and recommendations. Runtime objects hold only the provider, concurrency gate, directory and live event emitter; credentials never enter graph state.

New runs persist LangGraph stage boundaries in PostgreSQL. Workflow thread IDs use the simulation ID; chat thread IDs use `chat:{id}` so the two graphs cannot overwrite each other. Existing `private/{id}/workflow.sqlite` and `chat.sqlite` files use their original savers and thread IDs, preserving exact-stage recovery for older runs. A failed or interrupted graph resumes with `ainvoke(None)`. Viewer-level JSON caches preserve results inside a stage. Partial completed runs begin a fresh pass using those caches; downstream insights/recommendations are invalidated when missing viewers are retried.

Startup creates an isolated schema (default `ripple`) and imports legacy `ripple.sqlite3` history transactionally. A migration marker prevents repeated imports from resurrecting deleted records. Existing ID conflicts fail safely instead of overwriting data. The source SQLite file remains untouched. Old results without provenance remain readable and are explicitly treated as legacy evidence.

Deletion removes the history row and workflow/chat checkpoint rows in one PostgreSQL transaction before removing local media and caches. PostgreSQL connection failures therefore do not delete media first. Media deletion retains the existing best-effort local cleanup behavior. Backups must include both PostgreSQL and `DATA_DIR`; PostgreSQL alone cannot restore uploaded media, JSON caches, version metadata or the local chat transcript.

Psycopg uses a bounded pool of 1–6 connections for the existing synchronous store interface. Checkpoint operations use a dedicated autocommit connection per active graph and `asyncio.to_thread`, retaining Windows Proactor compatibility needed by FFmpeg subprocesses. The installed PostgresSaver supplies serialization, locking, versioning, and checkpoint SQL. Schema names are validated; statement values are parameterized. New LangGraph tables are set up once per process/schema.

Neon pooled URLs are resolved to the same endpoint's direct hostname internally: its transaction pool rejects startup `search_path`. A small application pool and disabled prepared-statement caching avoid a hidden reliance on transaction-pool session behavior. `.env` is never rewritten. Other PostgreSQL URLs are used as provided. Keep provider-supplied TLS options.

References: [Psycopg row factories](https://www.psycopg.org/psycopg3/docs/advanced/rows.html), [LangGraph PostgreSQL checkpoint API](https://reference.langchain.com/python/langgraph.checkpoint.postgres).

## UI state and feature access

The introduction is the default view; hashes link to Studio, new simulation, history, library, comparison, method, and setup. The existing route dispatcher and API contracts remain. The landing network is explicitly labeled illustrative and uses deterministic SVG geometry. Actual Studio node colors and metrics come exclusively from returned saved reactions.

React roots mount only into the introduction, setup companion, content ribbon, and navigation icon containers. `RippleExperience.dispose()` unmounts page roots before the dispatcher replaces their DOM. Navigation icon roots persist. The existing form owns submission, provider consent, file validation, and API calls. The homepage composer carries its draft and optional File into that form in browser memory; it does not submit a simulation. The brief subscribes to form events and disconnects its listeners and section observer on unmount.

Motion supplies entrance reveals, scroll-linked floating labels, button feedback and the content-ribbon expansion. CSS supplies the ambient atmosphere and illustrative audience pulse. The introduction has a pause control for ambient motion and honors system reduced-motion preferences. Studio defaults to the light palette for a new browser; an existing theme preference is retained. Local Manrope and DM Sans fonts include their OFL licenses.

Replay uses the renderer's existing event cutoff; the inspector obeys that cutoff too, so a future response cannot appear early. Leaving the Studio clears replay and polling timers. Video previews use object URLs released on replacement/navigation. Theme preference is stored locally. Dialogs use native modal focus handling with Escape and focus restoration. Reduced-motion CSS disables decorative animations; the replay button remains an intentional user control.

The focused Studio keeps detailed scores, scenarios, content diagnostics, source frames, full recommendations, disagreements, profile reasoning and execution events accessible through disclosures and drawers. Provider setup and method controls remain visible on mobile. Public documentation captures are generated by a separate fixture HTTP server, never by injecting example records into production storage.

The dependency graph is intentionally bounded. Simulation stages follow a known plan; per-viewer evaluation runs through a bounded queue and response-driven propagation waves. Chat uses conditional routing from a validated plan to its selected tools, then a grounded answer. This is an orchestrated agent workflow, not an unrestricted autonomous agent.

## Cache invalidation

| Change | Media/context | Content analysis | Profiles | Viewer responses | Insights / strategy |
| --- | --- | --- | --- | --- | --- |
| Retry interrupted stage | reuse | checkpoint/cache | checkpoint/cache | reuse successful | pending work |
| Recover partial viewers | reuse | reuse | reuse | missing only | regenerate |
| Hook/caption/CTA/variation | reuse source, update proposals | regenerate | reuse | regenerate | regenerate |
| Target audience only | reuse, update audience | reuse | regenerate | regenerate | regenerate |

Children preserve root/parent lineage and independent copies of source media. Copying costs disk space, but allows deletion of a baseline without destroying child media. If the parent is deleted, parent comparisons become unavailable rather than fabricated.

## Evidence and uncertainty

Provenance separates timestamped video source frames, transcript-derived data, creator descriptions, AI interpretations, synthetic viewer reactions and mathematical assumptions. A source frame is actual media; its visual interpretation is still AI output. Hypothetical edits are never labeled observed footage.

Insight claims, recommendations and chat outputs use existing source IDs. Validation checks reference existence, not semantic truth; LLM interpretations can still be mistaken. The UI and report expose limitations. Percent metrics are explicitly defined panel summaries, not calibration claims.

For legacy results without provenance catalogs, chat resolves source IDs from actual stored analysis, outcomes and viewer reactions using the same ordering as retrieval. This adapter is read-only. Chat permits tool citations only for selected tools and regenerates an answer once if source validation fails. Persisted conversation history contains only verified replies.

## Skills and tools

Six SKILL.md documents define inputs, invocation, instructions, tools, output schemas, evidence requirements and validation. Groq prompts load these documents; they are not unused documentation. The deterministic propagation node loads its skill and enforces arithmetic in code.

The chat planner uses a structured tool-selection schema, not Groq's native function-call wire protocol. The application dispatches only allowlisted tools with a server-bound simulation row. No arbitrary filesystem, shell, URL or simulation-ID arguments are model-controlled. Follow-up context is limited to at most ten messages and 3,000 characters total (1,000 per message). Retrieved tools share a 10,000-character budget, with truncation disclosed. Schema-specific output token caps reduce oversized requests. The last sixty conversation entries remain in the local transcript.

## Framework decisions

[LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [persistent checkpoints](https://docs.langchain.com/oss/python/langgraph/persistence) supply the actual stateful orchestration.

[Deep Agents](https://reference.langchain.com/python/deepagents) was evaluated. Its general filesystem/long-horizon harness would duplicate the bounded orchestration and expand permissions. It is not a dependency. The useful capabilities here are implemented explicitly: staged decomposition, specialized delegation, isolated viewer context, structured outputs, persistent state, read-only planning/tools and human-approved experiments.

MCP was evaluated and not added: there is no requested external analytics/account integration. Local scoped functions suffice; the product makes no claim to fetch real social analytics.

The original Groq adapter is retained to preserve pacing, safe errors and compatibility. [Groq structured output documentation](https://console.groq.com/docs/structured-outputs) describes strict and JSON modes; the implementation additionally recovers strict-schema failures through JSON mode with mandatory local validation.

## Known operating limits

- Local single-user, single-process service; no distributed workers or tenant isolation.
- Results rely on one model family and may exhibit correlated bias.
- Synthetic panels are not representative human studies.
- Video sampling does not observe continuous motion or actual retention.
- What-if video changes are descriptions, not rendered replacement media.
- Reports are portable Markdown and full JSON, not designed PDF exports.
- Restarts require the user to Resume affected runs.
- No social publishing, external analytics, Deep Agents package or MCP server is implemented.
