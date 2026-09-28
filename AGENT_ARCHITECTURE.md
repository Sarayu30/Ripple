# Ripple agent architecture

Research checked 2026-09-27. This is application agent behavior, not instructions
for the developer's coding assistant. Uploaded content never supplies skills.

## Decisions and primary sources

- [Agent Skills specification](https://agentskills.io/specification): a skill is a
  directory with `SKILL.md`, YAML name/description, and instructions. Discovery
  loads metadata; the chosen workflow is disclosed when used. Ripple uses six
  short reviewed skills and records a content hash for each activation.
- [Deep Agents skills](https://docs.langchain.com/oss/python/deepagents/skills):
  the SDK discovers metadata and exposes full skills through `read_file`. Ripple
  seeds only synthesis skills into an ephemeral StateBackend.
- [Deep Agents subagents](https://docs.langchain.com/oss/python/deepagents/subagents):
  specialist delegation isolates task context. Ripple uses an evidence reviewer
  and creative editor after the independent panel finishes. There is no reason
  for every synthetic viewer to run its own research team.
- [Deep Agents backends](https://docs.langchain.com/oss/python/deepagents/backends):
  StateBackend supplies a virtual filesystem. Ripple provides no host filesystem
  or shell backend. Writes and general-purpose delegation are excluded.
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs) and
  [native local tools](https://console.groq.com/docs/tool-use/local-tool-calling):
  structured outputs and native tool use cannot currently be combined. Ripple
  separates native Deep Agents function turns from validated final JSON output.
  Persona decisions use a compact JSON action protocol with real local dispatch.
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling):
  tool declarations and function response turns connect models to local tools.
  Ripple preserves native model parts, including thought signatures, between
  function turns; these private transport fields are not shown in the UI.
- [Groq API reference](https://console.groq.com/docs/api-reference): JSON calls
  set `tool_choice=none`; required native tool stages select the named function
  (Gemini uses `ANY` with the current declarations). Optional turns use `auto`.
  Rejected function turns
  receive sanitized correction instructions within the bounded retry policy.

## Runtime

```text
Evidence analysis → profile generation → independent persona agents
                                          discover skill metadata
                                          choose load_skill / inspect_evidence
                                          validate final Reaction
                                          save tool activity and response
                  → response-driven network waves and holdouts
                  → aggregate returned scores
                  → Deep Agents coordinator + evidence / creative specialists
                  → validated Recommendations + execution audit
```

`app/agent_runtime.py` gives every persona a separate state, skill catalog and
content evidence. No tool can inspect another viewer, change network weights,
run a shell, fetch an arbitrary URL, or change files. Loading a skill and reading
transcript, caption, or analysis are prerequisites for submitting a reaction.
Exhausting the budget without those actions produces an explicit failure.

`app/deep_analysis.py` adapts the paced `Provider.tool_call` transport to a
LangChain `BaseChatModel`. Native Groq/Gemini function responses become validated
`AIMessage` tool calls. Deep Agents executes its actual tools, supplies
`ToolMessage` observations, and delegates real additional model calls. Its
`TodoListMiddleware` is explicitly enabled. Unsupported names, arguments outside
the allowlist, host paths, and recursive delegation are rejected.

Tool availability enforces prerequisites: load the assigned skill, plan (for the
coordinator), inspect evidence and viewer feedback, then delegate to both
specialists. Models choose tool arguments, task briefs, specialist order and
findings. A final report is accepted only after both specialists complete their
required evidence steps. Feedback reads return up to 20 viewers per page, spread
across cohorts and archetypes; pagination is available. Reports disclose this
sampling limit, while aggregate metrics use every completed viewer.

The coordinator and specialists share 24 logical model calls by default, followed
by one final schema-formatting call. Each logical call retains the provider's
bounded HTTP/JSON retries and shared per-key pacing. LangSmith tracing is disabled
for these runs so ambient tracing configuration cannot send content to another
service. The selected Groq/Gemini service still receives the evaluation context. Native
function turns and final `Provider.json` formatting share the same pacing gate.

## Persistence and inspection

- `agent-N.json`: private, per-viewer tool observations, completed actions, loaded
  skill versions, and final response. Fingerprints cover evidence/profile/model
  and persona skill versions. Retry continues after saved actions; an invalid
  plan that exhausted its budget starts a fresh bounded plan on explicit resume.
- `response-audit.json`: observable actions, evidence-source names and skill
  versions for returned reactions. These appear in the persona inspector and
  export. It contains no hidden chain of thought.
- `recommendation-audit.json`: report model-call count and requested/completed/
  failed tool calls with coordinator/specialist attribution. Updated during the
  run. Report failure preserves the panel; retry restarts the bounded report.
- `recommendations.json`: completed report cache keyed to panel, analysis,
  metrics, limitations, model, and synthesis skill versions.
- Legacy completed reactions remain reused and are labeled as lacking recorded
  skill history. They are not rewritten or represented as new agent runs.

The topology and propagation equations are unchanged. Model-selected skills do
not make synthetic judgments empirically representative or predictive.

## Extending skills

Add `skills/<lowercase-hyphenated-name>/SKILL.md` with required name/description
and `metadata.role: persona` or `synthesis`. Keep instructions specific to the
available tools. Review additions as executable policy in code review; no runtime
skill upload or remote skill installation endpoint exists. Changing skill text
changes its hash. Adding tools requires explicit dispatcher/schema changes and
tests; text in a skill cannot grant a new capability.

## Verification

Run `python -m pytest -q` (FFmpeg/ffprobe required for the ingestion test).
`python scripts/smoke_agents.py --deep` is an optional **billable live check**
using synthetic content and server-side `.env` credentials. It does not create
a saved audience study or claim to validate prediction quality. See
[VALIDATION.md](VALIDATION.md) for this change's actual results.
