# Deploy Squeek Sprint

The submitted game is served at https://squeek.onerub.net from `site/`.
The public source repository retains the historical name `squeek-ladder`.
Legacy planner/profile-reader pages are not the submitted game.

## Build and test

From the repository root:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
python -m unittest discover -s tests -p 'test_*.py'
python tests/sprint_browser.py --repeat 5
```

Browser tests require Python Playwright and its Chromium installation. They use
explicitly synthetic, isolated test fixtures, never real game scores or badge claims.
The build compiles the pinned official status schema, then synchronizes the
allowlisted authored UI and engine files to the public root and `site/`.
Never deploy only `index.html`: CSS, controller, engine and validator are required.

## Production

Deploy from `site/` using the existing Vercel project link:

```sh
vercel deploy --prod --yes --scope fertalites-projects
```

No environment variables, wallet keys or user sessions are required for the game.
Do not upload `.env*`, wallet JSON, browser profiles, `.vercel/` metadata or evidence.
Keep `site/.vercelignore` and `site/vercel.json` in place.

## Verification

- Check HTTPS root and runtime assets return 200 and byte-match local `site/`.
- Check CSP, nosniff, referrer and permissions headers.
- Check sensitive paths return 404 without printing content.
- Open production in isolated Chromium: no page errors, practice starts, mobile fits.
- Check real feed schema, original timestamps and provenance. Never present a
  synthetic feed as live when hardware is unavailable.
- Confirm the default GitHub branch serves identical runtime files and README.
- Read back the exact existing Genesis submission after editing its description.
- Domain attribution is not team approval. Builder badges remain gated until the
  authoritative project/account endpoints confirm they were awarded.
