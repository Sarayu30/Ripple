# Validation performed

Updated: 2026-10-04.

## Automated verification

- Python regression suite: 30 tests passed, including legacy chat citations, automatic citation repair, bounded context and preservation of conversation history after failed verification.
- Tests cover actual LangGraph execution and persistent checkpoint recovery using isolated fixture providers, independent viewer calls, partial recovery without duplicate evaluations, approved child versions, selective cache reuse, comparison, lineage exports, source-ID validation, persistent chat and bounded retrieval/history.
- Original HTTP/privacy, malformed schema, provider cooldown, network propagation and legacy-result tests still pass.
- Real FFmpeg ingestion generated a video and verified decoded metadata, sampled frames and extracted audio.
- JavaScript syntax checks passed for application, Studio, network and workspace scripts.
- The jsdom integration suite passed empty-state/new-form navigation, exactly three KPIs, circular nodes, inspector tabs and connections, project versions, suggestions, chat, approved experiments, comparisons, Library and history.
- Fixture data is isolated from the production library. There is no production demo-score fallback.

## Real Groq smoke verification

An isolated test with generic design-workflow content completed through the real configured Groq provider:

- 25 of 25 synthetic viewer evaluations completed.
- All six workflow stages, including insights and creative recommendations, completed.
- 29 provenance records were saved.
- Ask Ripple selected four read-only tools and returned a grounded answer with eight validated source references.
- Provider rate limits and strict-schema failures exposed real recovery issues; these were fixed and the same saved run resumed successfully without repeating completed viewers.
- Oversized chat retrieval initially received HTTP 413. A shared context budget and schema-specific output caps resolved it; the live chat retry passed.

This was text/transcript-based integration testing. Real-provider frame vision and real audio transcription were not separately exercised; local FFmpeg ingestion was.

## Browser/visual limits

### Ask Ripple legacy-citation fix

A pre-upgrade simulation had 25 saved viewer reactions and no provenance catalog. Retrieval exposed `viewer:N` references, but the old chat validator did not recognize them. The read-time compatibility adapter now registers those actual saved reactions using the same ordering as retrieval; it does not change simulation results or invent observations. Invalid model citations trigger one bounded corrective retry, and only verified replies enter conversation history. Tool references are limited to tools used for that answer.

After restarting the local server, the live HTTP chat endpoint answered “Why are viewers scrolling?” against that existing simulation with 11 valid source references. No simulation rerun was required.

No browser surface was connected to this session. The browser inventory returned no available browsers, so the redesigned layout was not screenshot-reviewed and real-browser fullscreen, mobile rendering and visual accessibility remain unverified. DOM integration and JavaScript checks passed; they do not replace rendered-browser QA.

## Deployment limits

Docker files were reviewed and updated to include runtime skills and exclude private artifacts, but an image build was not run. Multi-tenant security, high-load performance and predictive calibration are outside this local single-user implementation. Synthetic outcomes must not be presented as real analytics.

## Reproduce

See README for Python and jsdom commands. Use a fresh workspace-local pytest temporary directory if Windows access controls prevent reusing an older system temp directory. Live provider smoke results remain in ignored artifacts and are not committed or displayed as user simulations.
