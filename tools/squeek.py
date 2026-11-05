#!/usr/bin/env python3
"""Read-only Squeek Ladder (Sepolia).

Usage: python tools/squeek.py [check|squeeks|ladder] [0xADDRESS]
Optional RPC_URL environment variable; never opens .env or signs.
Wallet custody only; deposited NFTs are intentionally excluded.
Reference: https://docs.squeekchain.com/developers/nft.md
Pinned: Sepolia core-sepolia-20261103 revision 7, deployments/sepolia.json.
ABI sources: assets/abi/SqueekNFT.json and assets/abi/SqueekCore.json.
Wallet merges belong to NFT.merge; deposited merges to Staking.mergeDeposited.
This tool intentionally prepares neither calls nor transactions.
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from web3 import Web3

CHAIN_ID = 11155111
DEFAULT_ACCOUNT = "0x8346Ac89e4B3297F014050dFe8baf87bF7567e63"
NFT = "0xc4c7982657f00509548f3a3a41db7fa439a6856b"
CORE = "0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4"
API = "https://api.squeekchain.com/v1"


def _f(name, ins, outs):
    return {"type": "function", "name": name, "stateMutability": "view",
            "inputs": [{"name": "a" + str(i), "type": t} for i, t in enumerate(ins)],
            "outputs": [{"name": "o" + str(i), "type": t} for i, t in enumerate(outs)]}


NFT_ABI = [_f("balanceOf", ["address"], ["uint256"]),
           _f("ownerOf", ["uint256"], ["address"]), _f("level", ["uint256"], ["uint8"]),
           _f("nextMergeHeight", ["uint256"], ["uint64"]), _f("cooldownBlocks", ["uint8"], ["uint64"]),
           _f("mergesOpen", [], ["bool"]), _f("MAXIMUM_LEVEL", [], ["uint8"]), _f("sqkCore", [], ["address"])]
CORE_ABI = [{"type": "function", "name": "state", "stateMutability": "view", "inputs": [],
             "outputs": [{"name": "", "type": "tuple", "components": [
                 {"name": n, "type": t} for n, t in [
                     ("settledThroughRound", "uint64"), ("cumulativeWork", "uint64"),
                     ("cumulativeBlockUnits", "uint96"), ("blockHeight", "uint64"),
                     ("blockProgress", "uint96"), ("workPerThousandBlocks", "uint32"),
                     ("authorizationNonce", "uint256"), ("paused", "bool")]]}]}]


def api_account(addr):
    pages, cursor, seen = [], None, set()
    for _ in range(60):
        url = f"{API}/accounts/{addr}"
        if cursor is not None:
            url += "?" + urllib.parse.urlencode({"cursor": cursor})
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Squeek-Ladder/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        if data.get("status") != "available" or not isinstance(data.get("tokens"), list):
            raise ValueError("incomplete or unavailable indexer response")
        pages.append(data)
        cursor = data.get("nextCursor")
        if cursor is None:
            return pages
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            raise ValueError("invalid or repeated indexer cursor")
        seen.add(cursor)
    raise ValueError("incomplete pagination: page limit reached")


def fetch_squeeks(addr):
    tokens, seen, economy = [], set(), {}
    for page in api_account(addr):
        economy = page.get("economy") or economy
        for token in page["tokens"]:
            token_id = int(token["tokenId"])
            if token_id <= 0 or token_id in seen:
                raise ValueError("invalid or duplicate token ID")
            seen.add(token_id)
            if token.get("custody") != "wallet":
                continue
            level, nxt = int(token["level"]), int(token["nextMergeHeight"])
            if level < 1 or nxt < 0:
                raise ValueError("invalid token state")
            tokens.append({"id": token_id, "level": level, "next": nxt})
    return sorted(tokens, key=lambda t: t["id"]), economy


def build_plan(toks, core_height, max_level, cooldowns):
    if type(core_height) is not int or core_height < 0 or type(max_level) is not int or not 1 <= max_level <= 255:
        raise ValueError("invalid height or maximum level")
    for lvl in range(2, max_level):
        if lvl not in cooldowns or type(cooldowns[lvl]) is not int or cooldowns[lvl] < 0:
            raise ValueError(f"missing or invalid cooldown for level {lvl}")
    pool, seen = {}, set()
    for t in toks:
        if type(t["id"]) is not int or t["id"] <= 0 or t["id"] in seen:
            raise ValueError("duplicate or invalid token ID")
        seen.add(t["id"])
        if type(t["level"]) is not int or type(t["next"]) is not int or not 1 <= t["level"] <= max_level or t["next"] < 0:
            raise ValueError("invalid token state")
        if t["level"] < max_level:
            pool.setdefault(t["level"], []).append({"id": t["id"], "next": t["next"], "sim": False})
    plan = []
    for lvl in range(1, max_level):
        group = sorted(pool.get(lvl, []), key=lambda t: (t["next"], t["id"]))
        while len(group) >= 2:
            survivor, donor = group.pop(0), group.pop(0)
            earliest = max(survivor["next"], donor["next"])
            simulated = survivor["sim"] or donor["sim"]
            plan.append({"survivor": survivor["id"], "donor": donor["id"], "level": lvl,
                         "ready_at": earliest, "ready": not simulated and earliest <= core_height, "sim": simulated})
            if lvl + 1 < max_level:
                pool.setdefault(lvl + 1, []).append({"id": survivor["id"],
                    "next": max(earliest, core_height) + cooldowns[lvl + 1], "sim": True})
    return plan


def read_snapshot(addr):
    """Indexer discovers IDs only; authoritative reads share one Ethereum block."""
    p = Web3(Web3.HTTPProvider(os.environ.get("RPC_URL") or "https://sepolia.gateway.tenderly.co",
                             request_kwargs={"timeout": 20}))
    if p.eth.chain_id != CHAIN_ID:
        raise ValueError("RPC chain mismatch; expected Sepolia 11155111")
    block = p.eth.block_number
    nft = p.eth.contract(address=Web3.to_checksum_address(NFT), abi=NFT_ABI)
    core = p.eth.contract(address=Web3.to_checksum_address(CORE), abi=CORE_ABI)
    def read(fn):
        return fn.call(block_identifier=block)
    if read(nft.functions.sqkCore()).lower() != CORE:
        raise ValueError("NFT/core binding mismatch")
    maximum = int(read(nft.functions.MAXIMUM_LEVEL()))
    if not 1 <= maximum <= 255:
        raise ValueError("invalid maximum level")
    height = int(read(core.functions.state())[3])
    opened = read(nft.functions.mergesOpen())
    if type(opened) is not bool:
        raise ValueError("invalid merge gate")
    cds = {lvl: int(read(nft.functions.cooldownBlocks(lvl))) for lvl in range(2, maximum)}
    indexed, _ = fetch_squeeks(addr)
    if len(indexed) != read(nft.functions.balanceOf(addr)):
        raise ValueError("incomplete indexer inventory: wallet balance mismatch")
    tokens = []
    for token in indexed:
        token_id = token["id"]
        if read(nft.functions.ownerOf(token_id)).lower() != addr.lower():
            raise ValueError(f"ownership mismatch for #{token_id}")
        tokens.append({"id": token_id, "level": int(read(nft.functions.level(token_id))),
                       "next": int(read(nft.functions.nextMergeHeight(token_id)))})
    return {"tokens": tokens, "height": height, "maximum": maximum, "cooldowns": cds,
            "open": opened, "block": block}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", default="ladder")
    parser.add_argument("address", nargs="?", default=DEFAULT_ACCOUNT)
    args = parser.parse_args(argv)
    if args.command not in ("check", "squeeks", "ladder"):
        parser.error("read-only tool: transaction commands are disabled")
    if not Web3.is_address(args.address):
        parser.error("invalid account address")
    address = Web3.to_checksum_address(args.address)
    try:
        s = read_snapshot(address)
        plan = build_plan(s["tokens"], s["height"], s["maximum"], s["cooldowns"])
        eligible = sum(m["ready"] for m in plan) if s["open"] else 0
        print(f"READ ONLY · {address} · Sepolia snapshot {s['block']}")
        print(f"{len(s['tokens'])} wallet Squeeks · core height {s['height']} · merges open {s['open']}")
        print(f"{len(plan)} projected moves · {eligible} eligible at snapshot (gate included)")
        if args.command == "squeeks":
            for t in s["tokens"]:
                print(f"#{t['id']} L{t['level']} next height {t['next']}")
        if args.command == "ladder":
            for m in plan:
                status = "FUTURE / RELOAD REQUIRED" if m["sim"] else (
                    "GATE CLOSED" if not s["open"] else "ELIGIBLE AT SNAPSHOT" if m["ready"] else "COOLDOWN")
                print(f"#{m['survivor']} <- #{m['donor']} L{m['level']}->{m['level'] + 1} {status}; earliest height {m['ready_at']}")
        print("Projection only: future heights assume earliest inclusion, not a promised schedule. Donor burns permanently; survivor ID stays. No wall-clock ETA. Reload after each merge. No signing or transaction submission.")
        return 0
    except Exception as exc:
        print(f"READ FAILED — no usable plan: {exc}", file=__import__('sys').stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
