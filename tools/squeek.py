#!/usr/bin/env python3
"""
squeek.py — SqueekChain Genesis command line for the owner wallet.

Reads D:\\NXR\\squeek\\.env  (PRIVATE_KEY + optional RPC_URL)

  python squeek.py check        # wallet, gas, squeeks, merge gate, checkpoint status
  python squeek.py squeeks      # daftar Squeek + level + cooldown
  python squeek.py ladder       # rencana merge penuh (L1..L10)
  python squeek.py tester       # kirim 1 tx resmi ke kontrak Squeekchain (badge code.the_tester)
  python squeek.py merge        # jalankan merge yang sudah siap
  python squeek.py raw <addr> <hexdata>   # kirim calldata manual

Testnet Sepolia. Butuh Sepolia ETH untuk gas.
"""
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

from eth_account import Account
from web3 import Web3

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

CHAIN_ID = 11155111
ADDR = {
    "core": "0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4",
    "mining": "0x2dccb11fcc2defdd188555e45acb52231e82e218",
    "staking": "0x50fd1780526c3186a0c037c7622203bc4fb611ca",
    "sqk": "0xd78a3956cf63164d1fa1c622ad3c66623162fa1e",
    "nft": "0xc4c7982657f00509548f3a3a41db7fa439a6856b",
}
API = "https://api.squeekchain.com/v1"
EXPLORER = "https://eth-sepolia.blockscout.com"

def _f(name, ins, outs, state=False):
    return {
        "type": "function",
        "name": name,
        "stateMutability": "nonpayable" if state else "view",
        "inputs": [{"name": f"a{i}", "type": t} for i, t in enumerate(ins)],
        "outputs": [{"name": f"o{i}", "type": t} for i, t in enumerate(outs)],
    }


ABI = {
    "nft": [
        _f("balanceOf", ["address"], ["uint256"]),
        _f("ownerOf", ["uint256"], ["address"]),
        _f("level", ["uint256"], ["uint8"]),
        _f("nextMergeHeight", ["uint256"], ["uint64"]),
        _f("cooldownBlocks", ["uint8"], ["uint64"]),
        _f("mergesOpen", [], ["bool"]),
        _f("MAXIMUM_LEVEL", [], ["uint8"]),
        _f("merge", ["uint256", "uint256"], [], state=True),
    ],
    "sqk": [
        _f("balanceOf", ["address"], ["uint256"]),
        _f("transfer", ["address", "uint256"], ["bool"], state=True),
    ],
    "mining": [
        _f("checkpoint", [], [], state=True),
        _f("checkpointStatus", [], ["bool", "uint64", "bool"]),
        _f(
            "state",
            [],
            ["(uint256,uint64,uint64,uint64,uint64,address,bool,bool,bool,bool)"],
        ),
    ],
}


def load_env():
    cfg = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    for k in ("PRIVATE_KEY", "RPC_URL"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def rpc_url(cfg):
    return cfg.get("RPC_URL") or "https://sepolia.gateway.tenderly.co"


def w3(cfg):
    p = Web3(Web3.HTTPProvider(rpc_url(cfg), request_kwargs={"timeout": 40}))
    if p.eth.chain_id != CHAIN_ID:
        raise SystemExit(f"chain mismatch: {p.eth.chain_id}")
    return p


def api_account(addr):
    out, cursor = [], None
    while True:
        url = f"{API}/accounts/{addr}"
        if cursor:
            url += "?cursor=" + urllib.parse.quote(cursor)
        req = urllib.request.Request(url, headers={"Accept": "application/json", "Origin": "https://squeekchain.com"})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        if d.get("status") != "available":
            raise RuntimeError("indexer " + str(d.get("status")))
        out.append(d)
        cursor = d.get("nextCursor")
        if not cursor:
            return out


def fetch_squeeks(addr):
    pages = api_account(addr)
    toks, eco = [], None
    for d in pages:
        eco = d.get("economy") or eco
        for t in d.get("tokens") or []:
            if t.get("custody") != "wallet":
                continue
            toks.append(
                {
                    "id": int(t["tokenId"]),
                    "level": int(t["level"]),
                    "next": int(t["nextMergeHeight"]),
                    "state": t.get("mergeState"),
                }
            )
    toks.sort(key=lambda x: x["id"])
    return toks, (eco or {})


def owner_of(p):
    cfg = load_env()
    key = cfg.get("PRIVATE_KEY", "")
    return Account.from_key(key) if key else None


def cmd_check(_args):
    cfg = load_env()
    p = w3(cfg)
    acct = owner_of(cfg)
    addr = acct.address if acct else "0x8346Ac89e4B3297F014050dFe8baf87bF7567e63"
    bal = p.eth.get_balance(addr)
    print(f"wallet        {addr}")
    print(f"private key   {'loaded' if acct else 'KOSONG — isi PRIVATE_KEY di ' + str(ENV_PATH)}")
    print(f"eth balance   {p.from_wei(bal, 'ether')} ETH")
    print(f"block         {p.eth.block_number}")

    try:
        toks, eco = fetch_squeeks(addr)
    except Exception as e:  # indexer down → fall back to chain
        print(f"indexer       error ({e}) — baca chain langsung")
        nft = p.eth.contract(address=Web3.to_checksum_address(ADDR["nft"]), abi=ABI["nft"])
        bal_nft = nft.functions.balanceOf(addr).call()
        print(f"squeeks       {bal_nft} (balanceOf)")
        eco = {
            "mergesOpen": nft.functions.mergesOpen().call(),
            "maximumLevel": nft.functions.MAXIMUM_LEVEL().call(),
            "coreBlockHeight": "?",
        }
        toks = []
    else:
        print(f"squeeks       {len(toks)}  (wallet custody)")
    print(f"merges open   {eco.get('mergesOpen')}")
    print(f"max level     {eco.get('maximumLevel')}")
    print(f"core block    {eco.get('coreBlockHeight')}")
    print(f"claimable     {eco.get('claimable') or 0}")

    mining = p.eth.contract(address=Web3.to_checksum_address(ADDR["mining"]), abi=ABI["mining"])
    try:
        paused, nxt, settled = mining.functions.checkpointStatus().call()
        print(f"checkpoint    round {nxt} settled={settled} core_paused={paused}")
    except Exception as e:
        print(f"checkpoint    read error: {e}")


def cmd_squeeks(_args):
    cfg = load_env()
    acct = owner_of(cfg)
    addr = acct.address if acct else "0x8346Ac89e4B3297F014050dFe8baf87bF7567e63"
    toks, eco = fetch_squeeks(addr)
    print(f"{len(toks)} squeeks · core block {eco.get('coreBlockHeight')} · merges open {eco.get('mergesOpen')}")
    for t in toks:
        print(f"  #{t['id']:<6} L{t['level']:<2} next_merge {t['next']:<8} {t['state']}")


def build_plan(toks, core_height, max_level, cooldowns):
    pool = {}
    for t in toks:
        if t["level"] >= max_level:
            continue
        pool.setdefault(t["level"], []).append({"id": t["id"], "next": t["next"], "sim": False})
    plan = []
    for lvl in range(1, max_level):
        group = sorted(pool.get(lvl, []), key=lambda x: (x["next"], x["id"] or 0))
        while len(group) >= 2:
            surv, donor = group.pop(0), group.pop(0)
            ready_at = max(surv["next"], donor["next"])
            plan.append(
                {
                    "survivor": surv["id"],
                    "donor": donor["id"],
                    "level": lvl,
                    "ready_at": ready_at,
                    "ready": ready_at <= core_height,
                    "sim": surv["sim"] or donor["sim"],
                }
            )
            born = max(ready_at, core_height) + cooldowns.get(lvl + 1, 0)
            if lvl + 1 < max_level:
                group.append({"id": None, "next": born, "sim": True})
                group.sort(key=lambda x: (x["next"], x["id"] or 0))
    return plan


def cmd_ladder(_args):
    cfg = load_env()
    p = w3(cfg)
    acct = owner_of(cfg)
    addr = acct.address if acct else "0x8346Ac89e4B3297F014050dFe8baf87bF7567e63"
    toks, eco = fetch_squeeks(addr)
    if not toks:
        print("0 squeeks di wallet — tidak ada yang bisa di-merge")
        return
    max_level = int(eco.get("maximumLevel") or 10)
    core_height = int(eco.get("coreBlockHeight") or 0)
    nft = p.eth.contract(address=Web3.to_checksum_address(ADDR["nft"]), abi=ABI["nft"])
    cds = {}
    for lvl in range(1, max_level + 1):
        try:
            cds[lvl] = nft.functions.cooldownBlocks(lvl).call()
        except Exception:
            cds[lvl] = 0
    plan = build_plan(toks, core_height, max_level, cds)
    ready = [m for m in plan if m["ready"] and not m["sim"]]
    print(f"{len(toks)} squeeks · {len(plan)} langkah ladder · {len(ready)} siap sekarang")
    for i, m in enumerate(plan[:60], 1):
        tag = "READY" if m["ready"] else f"wait@{m['ready_at']}"
        sim = " (pakai squeek hasil merge)" if m["sim"] else ""
        print(f"  {i:>3}. #{m['survivor']} <- #{m['donor']}  L{m['level']}->{m['level']+1}  {tag}{sim}")


def send(cfg, fn, label):
    p = w3(cfg)
    acct = owner_of(cfg)
    if acct is None:
        raise SystemExit("PRIVATE_KEY kosong — isi dulu di " + str(ENV_PATH))
    tx = fn.build_transaction(
        {
            "from": acct.address,
            "nonce": p.eth.get_transaction_count(acct.address),
            "chainId": CHAIN_ID,
            "gasPrice": p.eth.gas_price,
        }
    )
    try:
        tx["gas"] = int(p.eth.estimate_gas(tx) * 1.25)
    except Exception:
        tx["gas"] = 300000
    signed = acct.sign_transaction(tx)
    h = p.eth.send_raw_transaction(signed.raw_transaction)
    print(f"{label}: sent {h.hex()}")
    rc = p.eth.wait_for_transaction_receipt(h, timeout=300)
    ok = rc.status == 1
    print(f"{label}: {'OK' if ok else 'REVERTED'} block {rc.blockNumber} gas {rc.gasUsed}")
    print(f"{EXPLORER}/tx/{h.hex()}")
    return ok


def cmd_tester(_args):
    """Badge code.the_tester: one real transaction to a tracked Squeekchain contract."""
    cfg = load_env()
    p = w3(cfg)
    acct = owner_of(cfg)
    if acct is None:
        raise SystemExit("PRIVATE_KEY kosong — isi dulu di " + str(ENV_PATH))

    mining = p.eth.contract(address=Web3.to_checksum_address(ADDR["mining"]), abi=ABI["mining"])
    paused, nxt, settled = mining.functions.checkpointStatus().call()
    print(f"checkpointStatus: nextRound={nxt} settled={settled} corePaused={paused}")

    if settled and not paused and nxt != 0:
        return 0 if send(cfg, mining.functions.checkpoint(), "checkpoint") else 1

    # round belum settle: pakai tx resmi lain yang selalu lolos — SQK.transfer(self, 0)
    sqk = p.eth.contract(address=Web3.to_checksum_address(ADDR["sqk"]), abi=ABI["sqk"])
    print("round belum settle → kirim SQK.transfer(self, 0) sebagai tx resmi ke kontrak Squeekchain")
    return 0 if send(cfg, sqk.functions.transfer(acct.address, 0), "sqk.transfer(0)") else 1


def cmd_merge(_args):
    cfg = load_env()
    p = w3(cfg)
    acct = owner_of(cfg)
    if acct is None:
        raise SystemExit("PRIVATE_KEY kosong — isi dulu di " + str(ENV_PATH))
    toks, eco = fetch_squeeks(acct.address)
    if not toks:
        print("0 squeeks di wallet")
        return 1
    max_level = int(eco.get("maximumLevel") or 10)
    core_height = int(eco.get("coreBlockHeight") or 0)
    nft = p.eth.contract(address=Web3.to_checksum_address(ADDR["nft"]), abi=ABI["nft"])
    cds = {l: nft.functions.cooldownBlocks(l).call() for l in range(1, max_level + 1)}
    plan = [m for m in build_plan(toks, core_height, max_level, cds) if m["ready"] and not m["sim"]]
    if not plan:
        print("tidak ada langkah yang siap (semua cooldown / belum punya pasangan)")
        return 0
    print(f"{len(plan)} merge siap dijalankan")
    done = 0
    for m in plan:
        if send(cfg, nft.functions.merge(m["survivor"], m["donor"]), f"merge #{m['survivor']}<-#{m['donor']}"):
            done += 1
        else:
            break
    print(f"selesai: {done}/{len(plan)} merge sukses")
    return 0


def cmd_raw(args):
    if len(args) != 2:
        raise SystemExit("usage: squeek.py raw <address> <hexdata>")
    cfg = load_env()
    p = w3(cfg)
    acct = owner_of(cfg)
    if acct is None:
        raise SystemExit("PRIVATE_KEY kosong — isi dulu di " + str(ENV_PATH))
    to = Web3.to_checksum_address(args[0])
    data = args[1] if args[1].startswith("0x") else "0x" + args[1]
    tx = {
        "from": acct.address,
        "to": to,
        "data": data,
        "value": 0,
        "nonce": p.eth.get_transaction_count(acct.address),
        "chainId": CHAIN_ID,
        "gasPrice": p.eth.gas_price,
    }
    try:
        tx["gas"] = int(p.eth.estimate_gas(tx) * 1.25)
    except Exception:
        tx["gas"] = 300000
    signed = acct.sign_transaction(tx)
    h = p.eth.send_raw_transaction(signed.raw_transaction)
    rc = p.eth.wait_for_transaction_receipt(h, timeout=300)
    print(f"{'OK' if rc.status == 1 else 'REVERTED'} {h.hex()}")
    print(f"{EXPLORER}/tx/{h.hex()}")


COMMANDS = {
    "check": cmd_check,
    "squeeks": cmd_squeeks,
    "ladder": cmd_ladder,
    "tester": cmd_tester,
    "merge": cmd_merge,
    "raw": cmd_raw,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]) or 0)
