# Ripple v3 — validation performed

Validation date: 2026-09-28.

## Automated checks

- `python -m pytest -q -k 'not real_ffmpeg_ingestion'`: **33 passed, 1 deselected**.
  The FFmpeg ingestion test was excluded because this environment has neither
  FFmpeg nor ffprobe. It remains in the suite for installations with those tools.
- Python compilation, JavaScript syntax checks, and `pip check` passed.
- Skill registry tests cover discovery, role/path boundaries, and version hashes.
- Persona tests verify real tool dispatch, isolated context, bounded execution,
  checkpoint resume, and reuse of successful reactions and completed reports.
- The real Deep Agents graph runs in tests with a test-only model fixture. Checks
  cover coordinator planning, both specialists, required evidence steps, tool/path
  allowlists, the shared call budget, and feedback sampling across cohorts.
- Groq/Gemini transport tests verify native functions, required tool choice,
  Gemini thought-signature and call-ID preservation, malformed-argument retries,
  recoverable provider parse errors, quota handling, and sanitized errors.
- Existing API, network, privacy, schema, partial-failure, and legacy-result
  regression checks pass. Test fixtures are never a production reaction fallback.

## Live provider check

`python scripts/smoke_agents.py --env <local-env-path> --deep` completed against
Groq using synthetic text, one synthetic viewer, and the configured real model.
The persona loaded `credibility-review`, inspected transcript and analysis,
and returned a validated reaction. The Deep Agents coordinator loaded its skill,
planned, read evidence and panel feedback, and delegated to both the evidence
reviewer and creative editor. Both specialists loaded their skills and inspected
evidence. All 12 recorded tool calls completed. The report returned three edits.

The successful synthesis used **15 of 24 logical model calls**, plus one final
schema-formatting call. Provider retries can add HTTP requests. This check proves
the real provider/tool/Deep Agents path works; it is not a full live audience
simulation or a measurement of prediction quality. Credentials are not bundled.

## Browser checks

The current UI was inspected against an isolated local test database labeled
synthetic test data. The new-test form renders without the Provider setup page.
The persona inspector shows loaded skill versions and completed tool activity.
The report expands to show the coordinator and both specialists' execution
history. The narrow layout was visually inspected and no JavaScript errors were
recorded. The temporary database and screenshots are excluded from the ZIP.

## Remaining validation limits

Gemini's transport is covered by isolated tests but was not exercised against a
live Gemini account. The uploaded-video FFmpeg ingestion test, Docker build,
large live panels, and production load were not run for this upgrade. Public
multi-tenant operation and empirical predictive accuracy remain unvalidated.
See README for setup, evidence limits, and deployment requirements.
