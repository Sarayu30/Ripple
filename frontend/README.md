# Working on Ripple's interface

The Python server serves committed files from `app/static/`. End users do not need Node or a frontend development server.

For frontend changes, install Node.js 22 or newer, then run these commands from the repository root:

```sh
npm ci
npm run build
npm run test:ui
npm run test:browser
```

The browser suite uses installed Google Chrome and an isolated local fixture server. It never reads `.env` or connects to the real database or Groq. It also regenerates the public README screenshots in `docs/screenshots/`.

## Where to edit

- `experience.jsx`: React introduction, in-memory draft/file handoff, live intake brief, Studio content ribbon and navigation icons.
- `experience.css`: base typography, layouts and motion.
- `workspace-color.css`: light/dark semantic tokens, plum navigation, contrasting page headers, actions, drawers and focus styles.
- `studio-color.css`: dark network surface, metric cards, inspector, profile shortcuts and recommendations. Network colors are scoped to the network panel so both surrounding themes preserve their meaning.
- `page-color.css`: setup, history, Library, comparison, method, provider setup and the public introduction. The dispatcher sets `body.dataset.view` for page-specific styling.
- `build.mjs`: esbuild bundle and local font/license copying. Commit the generated `app/static/experience-react.*` files with source changes.
- `../app/static/app.js`: existing navigation, input fields and submission. Keep the original field names and validation contracts.
- `../app/static/studio.js`, `workspace.js`, `network.js`, `experience.js`: simulation views, drawers, SVG map and event replay.

## Integration rules

React owns only its mounted containers. Before replacing a page, call `RippleExperience.dispose()` so event subscriptions, observers and scroll effects are cleaned up. Existing form handlers are installed before the React intake companion mounts. The homepage composer only prepares the form; the original consent and submission flow still runs the simulation.

Keep illustrative geometry separate from actual results. Studio metrics, reactions and evidence must come from the saved API response. Respect reduced motion, keyboard access, mobile navigation and light/dark contrast when changing components.

The browser suite checks all eight main pages at 390px and 768px in both themes (32 overflow checks), verifies viewer-shortcut focus, and captures thirteen public screenshots. The inspector's shortcuts use actual saved profiles; they do not invent reactions or bypass the replay cutoff.

Dependencies are pinned in the root lockfile. React/Motion and Lucide are bundled locally; Manrope and DM Sans are served locally with their OFL licenses. The runtime needs no font or JavaScript CDN access. Existing Python packaging copies the generated assets without adding Node to the server image.
