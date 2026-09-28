# Upgrade your existing Ripple installation to v3

Keep your existing `.env` and `data` directory. The ZIP contains neither credentials nor saved-test data.

1. Stop Ripple in the VS Code terminal with **Ctrl+C**.
2. Make a backup copy of your current `ripple` folder.
3. Extract this ZIP. Copy the new `app` directory into your existing `ripple` folder, replacing its files. Also copy the new `skills` directory (required), `scripts`, `run.py`, `check_setup.py`, `requirements.txt`, `README.md`, and the other documentation/configuration templates. Keep your current `.venv`, `.env`, and `data` directories/files.
4. Open your existing `.env`. Keep the actual key ONLY on the `GROQ_API_KEY=` line. Set these other lines exactly:

```env
AI_PROVIDER=groq
GROQ_MODEL=openai/gpt-oss-20b
GROQ_VISION_MODEL=qwen/qwen3.8-27b
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
AGENT_CONCURRENCY=1
REQUEST_INTERVAL_SECONDS=4
MAX_PROVIDER_ATTEMPTS=4
MAX_COMPLETION_TOKENS=5000
```

Put each setting on a separate line. Put comments on separate lines too. If a model is unavailable in your account, run the model-check command described below; do not put your API key into a model field. Do not erase your existing `GROQ_API_KEY` or change `DATA_DIR` if you use a custom data directory.

5. In your Ripple folder, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe run.py
```

6. Open http://localhost:8000 and press **Ctrl+F5** to load the updated frontend.
7. Run **`python check_setup.py --groq`** to confirm the configured model IDs are listed. The key stays on your server. Model listing makes no content-generation request. Listing is not a guarantee of project permissions or every input capability.
8. Open an existing failed test and choose **Resume missing agents**. Previously successful reactions are reused. A new test is recommended when you want the new target/outside-audience split; old tests keep their original audience and input configuration.

## What happens to old tests?

The database schema is unchanged. Old results and media continue to open. v1 tests with saved profiles/reactions appear in the network inspector, but are labeled as having no recorded exposure history. No past propagation or timestamp history is invented. A retry creates a new recorded network run using saved reactions where possible. Per-response model provenance is shown when available; older reactions are labeled legacy.

## If only a few agents finish

The new **Agent errors & execution details** panel distinguishes HTTP status/model errors, rate limits, truncated output, timeouts and JSON-validation failures. Permanent provider errors or exhausted rate limits pause new requests instead of sending the remaining panel into the same failure. Resume after correcting the indicated issue. A daily quota cannot be fixed by lowering concurrency; wait for the quota reset or change your provider plan.

## New installation instead of updating in place

Follow README Quick start. After creating the new `.env`, copy your prior `data` directory into the new Ripple directory if you want the old tests there. Never run both servers against the same directory. Always stop the old server before switching.

## V3 agent behavior

Reinstall requirements to add the pinned Deep Agents runtime. Docker builds must
include the `skills` directory. The Provider setup page has been removed.

New and unfinished viewers use the skill/tool loop. Previously completed reactions
are reused and keep their original provenance; they are never retroactively labeled
as skill-based. Start a new simulation for an entirely skill-based panel.

Tool steps are checkpointed per viewer. A failed final reaction resumes after the
saved tool steps. A Deep Agents report failure preserves all viewers; retry restarts
that bounded report run. Completed reports are reused when the panel, evidence,
model, and synthesis skill versions match. Agent runs use more API calls than v2;
start with 25 viewers and keep `AGENT_CONCURRENCY=1`.
