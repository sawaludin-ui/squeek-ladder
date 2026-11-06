# Squeek Sprint

A playable, three-lane hamster expedition driven by Squeekchain's public hardware feed. The GitHub repository retains its historical `squeek-ladder` name; **Squeek Sprint is the submitted game**, not the legacy planner or profile reader.

Built on Squeekchain — https://docs.squeekchain.com

Production: https://squeek.onerub.net

## Play

Survive **60 active seconds**, collect seeds, rescue supplies, dodge rocks. Three hits end a run. Arrows / A-D / touch buttons / swipe change lanes. Space spends three seed charges on a four-second shield. P pauses. Sound is optional and off by default.

- **Live:** requires a fresh, schema-valid, moving hardware wheel. RPM continuously determines trail speed. Each five actual work units unlocks a supply drop, and each twelve advances the habitat. Work is the API's cumulative counter, **not a claim of exact physical revolutions**. Counter values use BigInt. Pause excludes work received while paused.
- **Practice:** deterministic local simulation, always available. No live work or live medal is fabricated. Practice records are separate.
- Stale/offline/simulated/COUNTER_FAULT input cannot be labeled live. Live runs wait safely for the wheel, without advancing the survival timer. Epoch changes or decreasing counters end a run; out-of-order observations cannot rewind state.
- Personal bests and bronze/silver/gold keepsakes are browser-local, editable by that browser, and not authoritative rankings. They are **not Genesis badges, Aura, token rewards, or on-chain proofs**.

Surviving a valid live expedition earns a local bronze keepsake. Silver needs at least one rescued supply and eight seeds; gold needs two supplies and fifteen seeds. Supply crates are worth 50 points; each seed is worth 10. No wallet, signup, or transaction is needed.

## Real integration, not a read-only wrapper

Actual hamster activity affects an ongoing game in three independent ways: movement/obstacle tempo from RPM; interactable supply spawns from increases in cumulative work; and habitat progression from that same real counter. Real player movement, collision, resource use, survival, and scoring determine outcomes. Habitat and supply thresholds are **game rules**, not protocol emission rules. There are no prediction rounds or settlement claims.

The client requests `https://api.squeekchain.com/v1/status` at most once per five seconds while visible, with a bounded eight-second request timeout and no overlapping requests. It validates the **entire response** against the pinned official Draft 2020-12 schema before reading `measurement`.

A hardware reading must have `freshness: online`, hardware provenance, a non-faulted core, and both `observedAt` and `receivedAt` within 120 seconds (maximum five-second future clock tolerance). This application uses a conservative local admission window; the API's own freshness classification is still required. An unsupported schema or missing measurement fails closed to practice. Game work is not used as a round-scoped or settled counter.

Official references:
- https://docs.squeekchain.com/developers/api.md
- https://docs.squeekchain.com/developers/build-with-ai.md
- https://docs.squeekchain.com/assets/api/status.json
- https://squeekchain.com/genesis/code

## Run, test, and build

Node.js 18+ and Python 3 are required for the full suite. Runtime gameplay is static HTML/CSS/JS; Ajv and esbuild are build-only dependencies pinned in package-lock.json.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
python -m unittest discover -s tests -p 'test_*.py'
python -m http.server 8080 --directory site
```

Visit http://127.0.0.1:8080. For real-browser tests, install Playwright in a virtual environment and install its isolated Chromium (not a personal browser profile):

```sh
python -m pip install playwright
python -m playwright install chromium
npm run test:browser
```

The browser suite uses explicitly mocked API fixtures **only inside the test context** to test counter-driven progression, stale/error behavior, input, pause, storage, mobile layout, and console errors. Release verification separately checks the real public feed and production-origin browser access. Test simulation is never substituted into production API requests.

## Source layout and reproducibility

- `src/index.html`, `src/sprint.css`, `src/sprint.js`, `src/favicon.svg`, `src/README.md`: authored UI/game documentation.
- Root `index.html`, `sprint.css`, `sprint.js`, `favicon.svg`, `README.md`: generated public copies; edit `src/`, then build.
- `sprint-engine.js`: separately testable game state, work-counter rules and feed admission.
- `docs/status.schema.json`: pinned official schema; explicit review is required for schema updates.
- `tools/build-schema.cjs`: compiles the schema with Ajv 2020-12 + formats to `status-validator.js`; generated validator is served locally, no remote script dependency.
- `tools/sync-site.cjs`: copies only allowlisted runtime/docs files into root and `site/`, verifying byte equality. It never copies sessions, wallet files, evidence, or `.env`.
- `site/`: Vercel deployment root; `.vercelignore` excludes local configuration.
- `tests/sprint-engine.test.cjs`, `tests/sprint.test.cjs`, `tests/sprint_browser.py`: deterministic game, deployment, and browser regression tests.
- Existing `planner.html`, `genesis.html` and Python `tools/` are **legacy supplemental utilities**, not the submitted game. Their tests remain intact. CLI transaction/signing functions are intentionally disabled.

## Safety, privacy, and limits

Only the public status API is read by the game. No tracking library, wallet connection, private key, session token, or authentication credential is part of the frontend. Rendering uses textContent rather than HTML for live content. Audio and browser storage failures do not block practice. Background tabs automatically pause; resuming is explicit. Accessibility includes keyboard controls, visible focus, text status, touch alternatives, reduced-motion support, and labeled controls; the canvas itself is not a screen-reader-playable alternative.

GitHub source, deployment files, and exact Genesis submission metadata must be kept aligned. **Deployment readiness is not Genesis approval**. No official badge is awarded by this app, and no reviewer outcome is promised.
