# Reference video → Ripple v2

The supplied screen recording was inspected using timestamped frames and its visible subtitles, including the product demonstration at roughly 7–40 seconds. The video calls the demonstrated product **Viralyst**. Ripple keeps its own name and implementation. Small text in the embedded low-resolution screen recording is not fully legible; the mapping below covers observable interactions and layout rather than claiming an exact source-code or pixel-for-pixel clone.

| Reference feature | Ripple v2 implementation |
|---|---|
| Compact content/audience/run setup above the network | Studio header with private video/source, content message, audience, status and progress |
| A field of initially neutral viewer nodes | Nodes appear from generated profiles; pending reactions remain gray |
| Agents inside and outside the target demographic | Configurable 0–50% outside-audience cohort, optional outside-audience description |
| Nodes change color as viewers react | Returned reactions control engaged/share/scroll states; failures are separate |
| Lines connecting viewers as content spreads | Auditable sharing edges triggered by the actual source agent's response and explicit topology/rules |
| Multiple rounds of spread | Seed + up to three share waves, followed by separately labeled holdout evaluation |
| Interactive viewer hover and selection | Hover card, mouse/keyboard selection, full inspector with profile/action/scores/reasons |
| Side inspector with individual agent details | Background, motivation, viewing context, understanding, emotion, sharing rationale, objection and edit |
| Visible view controls | 2D and rotatable 3D perspective, zoom, pan and reset; same underlying graph |
| Bottom playback/progress controls | Saved-event replay with play/pause, timeline scrubbing and 1×/2×/5× speed |
| “Niche hit” outcome and breakout interpretation | Existing overall verdict plus cohort-specific breakout signal, panel cascade reach and depth |
| Light minimal dashboard layout | Light Studio theme by default; original dark theme retained with a persistent toggle |
| Original Ripple diagnostics and recommendations | Preserved in Insights & recommendations, including all scores, edits, hooks, CTA and A/B ideas |
| Saving and comparing versions | Existing SQLite history/export/compare retained, plus copy-audience New version action |
| Guildly section at the end | Excluded |

The recording's claims about replicating Instagram ranking are **not** adopted as fact. Ripple simulates an explicitly assumed network using independent AI viewer judgments. It does not have Instagram's private ranking model, a real follower graph, or calibrated real-world predictive accuracy.

## Files added

- `app/network.py`
- `app/static/network.js`
- `app/static/studio.js`
- `app/static/studio.css`
- `check_setup.py`
- `tests/test_v2.py`
- `UPGRADE.md`
- `FEATURE_MAP.md`

Core provider, simulation, API, schema, and frontend files were updated. The database schema is unchanged.


## V3 agent upgrade

| Feature | Implementation |
|---|---|
| Reviewed skill registry | `skills/*/SKILL.md`, `app/skills.py`; metadata discovery, role allowlist, version hashes |
| Independent tool loops | `app/agent_runtime.py`; model-selected skill/evidence tools, bounded budget, per-viewer checkpoints |
| Deep report synthesis | `app/deep_analysis.py`; actual Deep Agents graph, todo planning, evidence and creative specialists |
| Shared provider controls | `Provider.json` and `Provider.tool_call` share pacing, bounded retries and redacted errors |
| Visible execution | Persona inspector shows skill names, versions, tool calls and evidence sources; report activity view and JSON exports include the synthesis audit |
| Provider page removal | Settings navigation, page renderer and client model-check button removed; server `.env` and CLI retained |
