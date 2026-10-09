# Ripple feature preservation checklist

The redesign keeps the existing API paths, Groq provider behavior, six agent stages, generated schemas, scoring, propagation arithmetic, and saved results. PostgreSQL replaces the history store and handles new checkpoints; legacy checkpoint files remain available for recovery.

“Verified” below refers to the named automated checks, not an exhaustive live-provider run. Public screenshots use an isolated browser fixture server.

| Existing capability | Where it is accessible now | Verification |
| --- | --- | --- |
| Idea and attached-video handoff | Homepage content composer → New simulation | Browser checks draft text, source tab, File transfer and local preview |
| Live creative brief | New simulation companion | Browser checks name, audience and panel-size updates |
| Audience perspective introduction | Keyboard-accessible audience lens | Browser selection and arrow-key checks; illustration clearly labeled |
| Original input context | Studio content ribbon above the metrics | Browser expansion and saved-angle assertion |
| Ambient movement control | Homepage Pause motion; system reduced motion | Separate Chrome contexts exercise both motion preferences and pause |
| Video upload and source preview | New simulation; local video preview, upload controls | Browser input visibility; Python FFmpeg extraction and HTTP boundaries |
| Public links, transcript, caption | New simulation → Paste a link | DOM and browser tab/disclosure checks; URL validation tests |
| Audience, outside share, platform, goal, CTA | New simulation form; original field names retained | DOM checks; schema and workflow tests |
| Panel sizes and distribution assumptions | New simulation → test audience / distribution details | Existing schema and aggregation tests |
| Explicit provider consent | Original submission checkbox | Input schema and HTTP tests; unchanged validation |
| Model availability / provider settings | Provider setup, including mobile navigation | Provider adapter/model tests; responsive navigation checks |
| Content analysis and sampled frames | Studio → Your content / full analysis; evidence disclosure | Browser diagnostic drawer; backend extraction and pipeline tests |
| Six-stage agent workflow | Plain-language stage strip; AI activity disclosure | Real LangGraph execution with fixture providers |
| Independent viewer evaluation | Existing viewer workflow unchanged | Independent-call, failure and response reuse tests |
| Target and outside audience | Map filters, legend and viewer audience chip | Browser cohort-filter counts |
| Reaction states | Colors plus legend, filter and accessible node labels | Browser negative/cohort filters; keyboard renderer retained |
| SVG audience map | Studio → Audience reaction map | DOM nodes/selection/connections; browser interaction |
| 2D and 3D | Explicit mode buttons, existing renderer modes | Browser pressed states and mode interaction |
| Zoom / pan / rotation / reset / fullscreen | Existing map controls and gestures | Renderer preserved; reset/fullscreen controls present; browser mode/filter checks |
| Replay | Play/pause, scrubber, speed and Latest | Browser historical cutoff and inspector consistency |
| Viewer reasoning and profile | About this viewer → Thoughts / Profile / Connections | DOM inspector tabs and linked-viewer selection |
| All engagement scores / share reasoning | Viewer reasoning disclosure; full-analysis drawer | Browser/DOM diagnostics; original response schema retained |
| Aggregate scores and sharing scenarios | Full content & audience analysis drawer | Aggregation tests and browser drawer |
| Insights / disagreements / source IDs | What happened / why; suggestion and evidence drawers | Evidence validation and citation-recovery tests |
| Priority edits, alternative hook/caption/CTA | What should I change? → See all suggestions | DOM and browser suggestion drawer |
| Cover ideas, variants, what to keep | Suggestion drawer | Browser cover assertion; underlying schema unchanged |
| Ask Ripple and follow-ups | Sidebar → Ask Ripple | Tool-scoping, persistence and evidence-retry tests; browser question submission |
| What-if edits | Version comparison / current project / suggestion drawer | Browser approved submission; backend cache invalidation and lineage tests |
| Side-by-side versions | VERSION A / Original and VERSION B / Updated | DOM/browser comparison; backend metric/segment comparison tests |
| Resume / restart recovery | Resume simulation | PostgreSQL graph interruption/recovery and partial-viewer reuse tests |
| Saved history | Your simulations, with audience and stored verdict | PostgreSQL summary and CRUD tests; DOM/browser history |
| Creative library | Library | DOM and responsive browser navigation |
| Markdown reports / JSON exports | Content details, Library, comparison | Existing API/report and legacy export tests |
| Confirmed deletion | Your simulations | API tests; PostgreSQL transactional checkpoint cleanup; confirmation retained |
| Theme toggle | Workspace header; preference retained locally | Browser dark/light toggle |
| Mobile and tablet layouts | Every main page | 16 browser overflow checks at 390px and 768px |
| Empty / loading / error states | Existing pages and drawers; clearer guidance | DOM empty-state; API failure/retry tests |
| Private media / same-origin boundaries | Existing server routes and middleware | HTTP security tests |

New additions: introduction with illustrative SVG audience, visible journey and target-user sections, local upload preview, clearer insight hierarchy, full diagnostic access, PostgreSQL migration, and documented screenshot generation.

No inference stage, score formula, provider retry policy, result schema, or original result record was replaced with mock behavior. See [VALIDATION.md](VALIDATION.md) for practical test limits.
