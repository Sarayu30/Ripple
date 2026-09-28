# Ripple v2 — validation performed

Validation date: 2026-09-25.

## Automated checks

- `python -m pytest -q`: **20 passed**. One dependency deprecation warning; no failures.
- Python module compilation and JavaScript syntax checks passed.
- Isolated provider tests verify independent per-persona requests, partial failure reporting and resume without rerunning successful agents.
- Real FFmpeg ingestion test generates and decodes a short video, extracts timestamped frames/audio, and verifies metadata.
- HTTP tests cover missing credentials, secret-free configuration, URL validation, same-origin mutation protection, optional workspace password and nonpublic data paths.
- Network tests verify response-driven propagation, exposure deduplication and exclusion of direct-test holdouts from cascade reach.
- Provider regression tests cover configuration paste errors, strict structured requests, locally validated score bounds with corrective retries, sanitized error details, and long Retry-After resets without premature retries.
- Legacy result/export checks verify that missing historical propagation is not invented.

## Browser and visual checks

A local Uvicorn subprocess and Chromium were run together. Browser checks passed for the new-test form, a 100-node network, persona selection/inspector, 3D view, outside-audience filtering, replay/play/pause/scrubbing, both themes, report navigation, new-version input copying, comparison, missing-key model checks, and mobile layout at 390px width. No JavaScript errors were recorded. Screenshots were inspected for the form, light/dark network and mobile layout. Completed tests correctly hide the resume button.

Browser data was explicitly labeled handcrafted UI fixtures, isolated outside the application data directory, and is not included in the download. The production application has no fixture/demo-score fallback.

## Remaining validation limits

No live Groq inference was performed because no API key was supplied to the development environment. Account model access, provider quotas and real response quality must be checked with your own account. `check_setup.py` confirmed local FFmpeg/ffprobe availability and correctly reported missing development keys without printing secrets.

Docker configuration is supplied but was not built here. Public multi-tenant operation, load capacity and empirical predictive accuracy have not been validated. This is a local implementation with production-oriented foundations; see README deployment requirements.
