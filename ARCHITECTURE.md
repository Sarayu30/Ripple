# Ripple implementation architecture

## Runtime boundaries

FastAPI owns request validation, same-origin checks, bounded uploads, job admission and local workspace authentication. Existing SQLite tests and private-media paths are preserved. The UI remains vanilla JavaScript and SVG, with no build step.

- `app/agents/orchestrator.py`: typed LangGraph state, six specialized stages, durable per-run AsyncSqliteSaver, progress and execution trace.
- `content.py`, `audience.py`, `viewers.py`: original Groq/media behavior extracted into specialized modules.
- `analytics.py`: deterministic propagation, segment summaries, provenance registry and citation validation.
- `insights.py`, `strategist.py`: structured evidence-grounded interpretation and creative recommendations.
- `skills.py`: allowlisted runtime skill discovery and content hashes.
- `tools.py`, `chat.py`: model-selected read-only tools and conversational LangGraph.
- `experiments.py`: immutable child runs, cache reuse/invalidation and saved-result comparison.
- `reports.py`: creator-ready Markdown built from stored outputs.
- `schemas.py`: strict Pydantic models including experiments, insights, tool plans and chat.
- `static/studio.js`, `workspace.js`, `network.js`, `upgrade.css`: focused Studio, drawers, experiments and network interactions.

## State and recovery

SimulationState contains the immutable input row plus context, analysis, profiles, reactions, failures, response audits, outcome, provenance, insights and recommendations. Runtime objects hold only the provider, concurrency gate, directory and live event emitter; credentials never enter graph state.

Each run has `private/{id}/workflow.sqlite`. LangGraph persists stage boundaries. A failed or interrupted graph resumes with `ainvoke(None)`. Viewer-level JSON caches preserve results inside the stage. Partial completed runs begin a fresh pass using those caches; downstream insights/recommendations are invalidated when missing viewers are retried.

Per-run graph/chat databases live inside private media directories, so deletion removes their state alongside media and JSON checkpoints. Existing records need no migration. Old results without provenance remain readable and are explicitly treated as legacy evidence.

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
