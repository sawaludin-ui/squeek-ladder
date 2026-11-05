# Squeek Ladder

Read-only merge planner and Genesis evidence dashboard for [SqueekChain](https://squeekchain.com).

Genesis Navigator: https://squeek.onerub.net/genesis.html

It shows public Aura, rank, badge eligibility and next-tier deltas, and exports actual upstream snapshots. Its fixed-upstream GET-only adapter (`site/api/genesis.py`) resolves browser Origin restrictions without private sessions or wallet credentials.

Live: https://squeek.onerub.net

## What it does

- Reads every Squeek in a wallet straight from the SqueekChain indexer (`/v1/accounts/{address}`):
  level, `nextMergeHeight`, merge state, plus core block height, `mergesOpen` and `MAXIMUM_LEVEL`.
- Builds the full survivor/donor pairing tree up to level 10, chaining freshly merged Squeeks into
  the next tier with the real `cooldownBlocks` from `SqueekNFT`.
- Shows which merges are executable right now and which block unlocks the rest.
- Links every core contract and the explorer so a holder can verify aura, badges and standing.

## Files

| File | Purpose |
|---|---|
| `index.html` | generated read-only planner (ethers CDN dependency) |
| `genesis.html` | public Genesis badge/standing dashboard |
| `site/api/genesis.py` | GET-only public API adapter |
| `build_site.py` | generator for `index.html` |
| `tools/squeek.py` | read-only CLI; transaction commands disabled |
| `tests/` | regression suites and live browser checks |

## CLI

```
cd D:\NXR\squeek
python tools\squeek.py check
```

`check` is read-only. Transaction execution is disabled; the browser planner does not request signatures. Missing cooldowns, incomplete inventories, wrong chain and failed ownership reads fail closed. Projected merges preserve survivor IDs but are never labelled immediately executable. Deposited/staking custody is not supported. Merges do not establish Genesis Aura.

## Regression checks

```sh
python build_site.py
node --test tests/reads.test.cjs
python -m unittest discover -s tests -p 'test_*.py'
node tests/genesis.test.cjs
python tests/genesis_browser.py
```

The reads suite includes the planner tests. Populated-wallet scenarios use fixtures; live empty-wallet success is not evidence of every populated-wallet scenario. The browser test exercises live public APIs, JSON download and desktop/mobile layout. Python CLI tests need `web3`; browser tests need Python Playwright and Chromium.

Before deployment, copy generated `index.html` and `genesis.html` into `site/`. Deploy that directory to the existing Vercel project; its Python public-data adapter uses only the standard library. `.vercelignore` excludes local environment files, caches and stale downloaded pages.

Domain verification, team review and badge issuance are distinct. No approval, whitelist allocation or top ranking is guaranteed.

## Contracts (SqueekChain Sepolia, chainId 11155111)

| Contract | Address |
|---|---|
| Core | 0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4 |
| Mining | 0x2dccb11fcc2defdd188555e45acb52231e82e218 |
| Staking | 0x50fd1780526c3186a0c037c7622203bc4fb611ca |
| SQK | 0xd78a3956cf63164d1fa1c622ad3c66623162fa1e |
| SqueekNFT | 0xc4c7982657f00509548f3a3a41db7fa439a6856b |

squeekchain-project: 502c8855-e4e0-4067-bf83-d2de88597fa3
