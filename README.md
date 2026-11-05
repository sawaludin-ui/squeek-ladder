# Squeek Ladder

Merge planner and CLI for [SqueekChain](https://squeekchain.com) Genesis holders.

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
| `index.html` | the site (single file, no build step, no dependencies) |
| `build_site.py` | generator for `index.html` |
| `tools/squeek.py` | CLI: `check`, `squeeks`, `ladder`, `tester`, `merge`, `raw` |

## CLI

```
cd D:\NXR\squeek
python tools\squeek.py check
```

`check` prints wallet, gas, Squeek count, merge gate, checkpoint status — read-only.
`merge` executes only merges whose cooldown has elapsed; `merge()` is owner-only and needs
no approval. The private key stays in a local `.env` and is never sent anywhere.

## Contracts (SqueekChain Sepolia, chainId 11155111)

| Contract | Address |
|---|---|
| Core | 0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4 |
| Mining | 0x2dccb11fcc2defdd188555e45acb52231e82e218 |
| Staking | 0x50fd1780526c3186a0c037c7622203bc4fb611ca |
| SQK | 0xd78a3956cf63164d1fa1c622ad3c66623162fa1e |
| SqueekNFT | 0xc4c7982657f00509548f3a3a41db7fa439a6856b |

squeekchain-project: 502c8855-e4e0-4067-bf83-d2de88597fa3
