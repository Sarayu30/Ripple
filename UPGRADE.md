# Upgrading Ripple

1. Preserve your existing `.env` and `data/`; do not replace them with example files.
2. Pull the existing `version_2` branch.
3. Install `requirements.txt` into your existing virtual environment.
4. Restart Ripple using `python run.py`.
5. Open Studio. Saved simulations remain available.
6. Resume interrupted/partial runs to reuse completed work. New runs use LangGraph checkpoints and runtime skills.
7. Use Compare Versions to create explicitly approved what-if simulations.

No tests-table migration or deletion of old results is required. Older runs have no invented provenance, graph traces or parent lineage. The compact Studio replaces 3D/replay controls with a circular network and expandable execution trace; underlying saved events remain in JSON exports.

Docker users must rebuild the image so it includes LangGraph and `skills/`. Read [ARCHITECTURE.md](ARCHITECTURE.md) for recovery and cache behavior.
