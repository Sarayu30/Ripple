# Research and provenance

Reference supplied by the user: https://www.instagram.com/reel/DZVd6KRChq2/

The original Instagram URL could not be retrieved by the research browser. The later user-supplied screen recording was available and inspected through timestamped frames and visible subtitles. It names the demonstrated product Viralyst. Its observable product demonstration (roughly 7–40 seconds) informed the v2 interface; the Guildly segment was excluded. This identifies what the supplied recording shows, not independently verified authorship or the original inventor of the idea. See FEATURE_MAP.md for the visible feature mapping and resolution limitations.

Primary implementation references consulted:

- Groq Images and Vision: https://console.groq.com/docs/vision — multimodal image inputs, base64 payloads, model configuration, maximum three images per request in the retrieved documentation.
- Groq Structured Outputs: https://console.groq.com/docs/structured-outputs — JSON/structured response support and the distinction between schema conformance and semantic accuracy.
- Groq Rate Limits: https://console.groq.com/docs/rate-limits — shared pacing and Retry-After handling; quotas differ by account and model.
- Groq API Reference: https://console.groq.com/docs/api-reference — chat completions and transcription request shapes.
- Groq Speech to Text: https://console.groq.com/docs/speech-to-text — transcription endpoint and verbose JSON option.
- Groq models: https://console.groq.com/docs/models — configurable model IDs. Account availability may vary.
- Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output — JSON response support and schema-validation patterns.
- Gemini image understanding: https://ai.google.dev/gemini-api/docs/image-understanding — inline multimodal image inputs.

The propagation coefficients and confidence formula are explicitly uncalibrated product assumptions, not research-derived predictive estimates. This repository does not claim an empirically validated simulation of Instagram, TikTok, YouTube or LinkedIn ranking systems.

V2 provider documentation was rechecked during implementation on 2026-09-25. The default text model and supported strict-schema adapter follow the official Groq structured-output documentation. Defaults remain configurable and model discovery is available in Provider setup. A listed model is not proof of all account permissions or capabilities.
