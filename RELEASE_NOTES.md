# Ripple v3 — latest working release

Release snapshot: 2026-09-28.

## Added in this upgrade

- Six reviewed `SKILL.md` workflows: attention, credibility, sharing, panel
  synthesis, evidence review, and creative editing. The registry discovers
  metadata, restricts roles/paths, and records skill version hashes.
- Independent persona agents choose skills and inspect evidence through real
  backend tools before returning validated reactions. Tool budgets, isolated
  context, and per-persona checkpoints support bounded execution and resume.
- LangChain Deep Agents coordinates report planning and delegates to evidence
  and creative specialists. The runtime executes native model function calls,
  shares a model-call budget, and validates the final recommendations.
- Groq/Gemini tool transport with pacing, bounded retries, quota handling,
  sanitized errors, and preserved Gemini function-call context.
- Persona inspection and report activity show completed skills/tool calls.
  Audit data is included in exports; older reactions retain their provenance.
- The Workspace / Provider setup page is removed. Provider credentials and
  model settings remain server-side in `.env`; `check_setup.py` handles checks.
- Completed reports are cached. A report failure preserves viewer results.

## Existing features retained

- Video uploads or public links with supplied transcript/caption; private media,
  sampled frames, vision analysis, and transcription when configured.
- Audience profiles, target/outside cohorts, response-driven network waves,
  independent holdouts, score aggregation, and modeled sharing scenarios.
- Live 2D/3D network, persona inspection, filters, saved-event replay, themes,
  recommendations, history, JSON export, and version comparison.
- SQLite persistence, retry/resume, private evidence files, and optional local
  workspace password.

## Verification and setup

33 automated tests pass; the FFmpeg ingestion test is excluded locally because
FFmpeg/ffprobe are absent. A live Groq persona and Deep Agents synthesis check
completed successfully. Gemini transport is tested with fixtures, not a live
account. See [VALIDATION.md](VALIDATION.md) for exact coverage and limits.

This ZIP includes source, tests, skills, configuration templates, and documents.
It excludes credentials, saved user data, virtual environments, and Git metadata.
Use [README.md](README.md) for a fresh installation or [UPGRADE.md](UPGRADE.md)
to preserve an existing `.env` and `data` folder. Reinstall requirements for v3.
