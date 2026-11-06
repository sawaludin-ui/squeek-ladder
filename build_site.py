#!/usr/bin/env python3
"""
build_site.py — generates planner.html for Squeek Ladder.
Single-file static app: no build step, no backend, no custody.
"""
import pathlib, textwrap

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Squeek Ladder — merge planner for Squeek holders</title>
<meta name="description" content="Read-only Squeek merge planner: verified wallet inventory, block cooldowns and projected levels. No signing or transactions.">
<meta name="squeekchain-project" content="502c8855-e4e0-4067-bf83-d2de88597fa3">
<style>
  :root{
    --bg:#0a0b09; --panel:#111310; --line:#23271f; --ink:#e7ecdf; --dim:#8a9280;
    --acid:#c8f751; --warn:#ffb454; --dead:#ff6b6b;
    --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--mono);font-size:14px;line-height:1.5}
  a{color:var(--acid);text-decoration:none;border-bottom:1px dotted #3d4a2a}
  .wrap{max-width:1080px;margin:0 auto;padding:22px 18px 80px}
  header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:14px}
  .brand{display:flex;align-items:baseline;gap:10px}
  .brand h1{font-size:18px;margin:0;letter-spacing:.14em;text-transform:uppercase}
  .brand span{color:var(--dim);font-size:11px;letter-spacing:.22em}
  .tick{display:flex;gap:14px;font-size:11px;color:var(--dim);flex-wrap:wrap}
  .tick b{color:var(--ink);font-weight:600}
  .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--acid);margin-right:5px;vertical-align:middle}
  .dot.idle{background:var(--dim)}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:18px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}
  .card h2{font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim);margin:0 0 12px}
  button{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;background:var(--acid);color:#0a0b09;border:0;border-radius:6px;padding:10px 14px;cursor:pointer}
  button:disabled{background:#20241c;color:#5b6353;cursor:not-allowed}
  button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
  input{font-family:var(--mono);font-size:13px;background:#0c0e0a;border:1px solid var(--line);color:var(--ink);border-radius:6px;padding:10px 12px;width:100%}
  .row{display:flex;gap:8px;margin-top:10px}
  .row input{flex:1}
  .kv{display:grid;grid-template-columns:1fr auto;gap:6px 12px;font-size:12px}
  .kv .k{color:var(--dim)}
  .kv .v{text-align:right;font-variant-numeric:tabular-nums}
  .ladder{display:flex;flex-direction:column-reverse;gap:6px;margin-top:8px}
  .rung{display:grid;grid-template-columns:56px 1fr 96px;align-items:center;gap:10px;font-size:12px}
  .rung .lv{color:var(--dim);letter-spacing:.1em}
  .bar{height:16px;background:#15180f;border:1px solid var(--line);border-radius:3px;position:relative;overflow:hidden}
  .bar i{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,#465c22,var(--acid))}
  .bar.after i{background:linear-gradient(90deg,#1f4a44,#4fd8c4)}
  .rung .n{text-align:right;font-variant-numeric:tabular-nums;color:var(--dim)}
  .rung .n b{color:var(--ink)}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
  th{color:var(--dim);font-weight:500;font-size:10px;letter-spacing:.14em;text-transform:uppercase}
  td.num{text-align:right;font-variant-numeric:tabular-nums}
  .pill{display:inline-block;font-size:10px;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;border-radius:99px;border:1px solid var(--line);color:var(--dim)}
  .pill.ok{color:#0a0b09;background:var(--acid);border-color:var(--acid)}
  .pill.wait{color:var(--warn);border-color:#4a3a1c}
  .pill.off{color:var(--dead);border-color:#4a2222}
  #log{max-height:190px;overflow:auto;font-size:11.5px;color:var(--dim);margin-top:10px;border-top:1px solid var(--line);padding-top:10px}
  #log div{margin-bottom:4px;word-break:break-all}
  #log b{color:var(--ink)}
  .hint{color:var(--dim);font-size:11px;margin-top:10px}
  .warnbox{border:1px solid #4a3a1c;background:#171208;color:var(--warn);border-radius:8px;padding:10px 12px;font-size:12px;margin-top:12px;display:none}
  footer{margin-top:26px;padding-top:14px;border-top:1px solid var(--line);color:var(--dim);font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
  .stat{font-size:26px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
  .stat small{font-size:11px;color:var(--dim);letter-spacing:.1em;text-transform:uppercase;display:block;margin-top:2px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <a href="/genesis.html">Genesis Navigator · Aura, badges & next actions →</a>
    <div class="brand">
      <h1>Squeek Ladder</h1>
      <span>merge planner</span>
    </div>
    <div class="tick">
      <div><span class="dot idle" id="dot"></span><b id="coreState">—</b> core</div>
      <div>block <b id="coreHeight">—</b></div>
      <div>round <b id="coreRound">—</b></div>
      <div>cadence <b id="coreRate">—</b></div>
    </div>
  </header>

  <div class="grid">
    <section class="card">
      <h2>01 · wallet</h2>
      <div class="row">
        <input id="addr" value="0x8346Ac89e4B3297F014050dFe8baf87bF7567e63" placeholder="0x… or connect" spellcheck="false">
        <button id="load">load</button>
      </div>
      <div class="row">
        <button class="ghost" id="connect">use wallet address</button>
        <button class="ghost" id="disconnect" style="display:none">disconnect</button>
      </div>
      <div class="kv" style="margin-top:14px">
        <div class="k">address</div><div class="v" id="who">—</div>
        <div class="k">squeeks held</div><div class="v" id="held">—</div>
        <div class="k">merge gate</div><div class="v" id="gate">—</div>
        <div class="k">max level</div><div class="v" id="maxlvl">—</div>
      </div>
      <div class="hint">Read-only Sepolia planner. Wallet connection selects an address only; no signing or transactions. Deposited Squeeks are excluded.</div>
    </section>

    <section class="card">
      <h2>02 · ladder now</h2>
      <div class="ladder" id="ladderNow"><div class="hint">load a wallet to build the ladder</div></div>
      <div class="kv" style="margin-top:14px">
        <div class="k">merge-ready pairs</div><div class="v" id="readyPairs">—</div>
        <div class="k">eligible at snapshot</div><div class="v" id="moves">—</div>
      </div>
    </section>

    <section class="card">
      <h2>03 · planned result</h2>
      <div class="ladder" id="ladderAfter"><div class="hint">—</div></div>
      <div class="row" style="margin-top:14px">
        <button id="run" disabled>read-only planner</button>
        <button class="ghost" id="replan" disabled>re-plan</button>
      </div>
      <div class="warnbox" id="warn"></div>
      <div id="log"></div>
    </section>
  </div>

  <section class="card" style="margin-top:14px">
    <h2>04 · moves</h2>
    <table>
      <thead><tr><th>#</th><th>survivor</th><th>donor</th><th>level</th><th>state</th><th class="num">earliest height</th><th class="num">timing</th></tr></thead>
      <tbody id="movesBody"><tr><td colspan="7" style="color:#8a9280">—</td></tr></tbody>
    </table>
    <div class="hint" id="planNote"></div>
  </section>

  <footer>
    <div>Squeek Ladder · read-only · wallet-custody projections only · donor burns permanently</div>
    <div id="netinfo">sepolia · 11155111</div>
  </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/ethers@6.13.4/dist/ethers.umd.min.js"></script>
<script>
(() => {
  "use strict";
  // Read-only. Official Sepolia deployment revision 7 and published NFT/Core ABIs.
  // https://docs.squeekchain.com/assets/deployments/sepolia.json
  // Wallet merges: NFT.merge. Deposited merges: Staking.mergeDeposited (outside this planner).
  const NFT = "0xC4C7982657f00509548F3a3a41db7FA439a6856B";
  const CORE = "0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4";
  const DEPLOY_BLOCK = 12057769;
  const RPCS = ["https://sepolia.gateway.tenderly.co", "https://ethereum-sepolia.public.blastapi.io", "https://ethereum-sepolia-rpc.publicnode.com"];
  const API_BASE = "https://api.squeekchain.com/v1";
  const MC3 = "0xcA11bde05977b3631167028862bE2a173976CA11";
  const ABI = ["function balanceOf(address) view returns (uint256)", "function ownerOf(uint256) view returns (address)",
    "function level(uint256) view returns (uint8)", "function nextMergeHeight(uint256) view returns (uint64)",
    "function cooldownBlocks(uint8) view returns (uint64)", "function mergesOpen() view returns (bool)",
    "function MAXIMUM_LEVEL() view returns (uint8)", "function sqkCore() view returns (address)"];
  const CORE_ABI = ["function state() view returns ((uint64 settledThroughRound,uint64 cumulativeWork,uint96 cumulativeBlockUnits,uint64 blockHeight,uint96 blockProgress,uint32 workPerThousandBlocks,uint256 authorizationNonce,bool paused))"];
  const MC3_ABI = ["function aggregate3((address target,bool allowFailure,bytes callData)[] calls) payable returns ((bool success,bytes returnData)[])"];
  const MC3_IFACE = new ethers.Interface(ABI);
  const $ = (id) => document.getElementById(id);
  const short = (a) => a ? a.slice(0,6) + "…" + a.slice(-4) : "—";
  const state = {provider:null, account:null, tokens:[], cooldowns:{}, maxLevel:0, coreHeight:0,
    mergesOpen:false, plan:[], busy:false, loaded:false, snapshot:null, version:0};
  function log(msg, kind) {
    const d = document.createElement("div");
    d.textContent = String(msg);
    if (kind === "err") d.style.color = "#ff6b6b";
    $("log").prepend(d);
  }
  function integer(value, label) {
    if (!["number","bigint","string"].includes(typeof value) || (typeof value === "string" && !/^\d+$/.test(value))) throw new Error("missing or invalid " + label);
    const n = Number(value);
    if (!Number.isSafeInteger(n) || n < 0) throw new Error("invalid " + label);
    return n;
  }
  async function fetchJson(url, options = {}, timeoutMs = 15000) {
    const controller = new AbortController();
    let timer;
    try {
      const timeout = new Promise((_, reject) => {
        timer = setTimeout(() => {controller.abort(); reject(new Error("request timeout"));}, timeoutMs);
      });
      return await Promise.race([(async () => {
        const response = await fetch(url, {...options, signal:controller.signal});
        if (!response.ok) throw new Error("HTTP " + response.status);
        return await response.json();
      })(), timeout]);
    } finally {clearTimeout(timer);}
  }
  async function pickProvider() {
    for (const url of RPCS) {
      let p;
      try {
        const request = new ethers.FetchRequest(url); request.timeout = 15000;
        // Some public gateways stall batched eth_call; contract multicall still batches token reads.
        p = new ethers.JsonRpcProvider(request, undefined, {batchMaxCount:1});
        if (Number((await p.getNetwork()).chainId) !== 11155111) throw new Error("RPC chain mismatch");
        await p.getBlockNumber(); return p;
      } catch {if (p) p.destroy();}
    }
    throw new Error("no verified Sepolia RPC reachable");
  }
  async function multicall(p, calls) {
    const mc = new ethers.Contract(MC3, MC3_ABI, p), out = [];
    for (let i=0; i<calls.length; i+=200) {
      const slice = calls.slice(i,i+200);
      const res = await mc.aggregate3.staticCall(slice.map(c=>({target:NFT,allowFailure:true,callData:c.data})), {blockTag:state.snapshot});
      if (res.length !== slice.length) throw new Error("incomplete multicall response");
      res.forEach((r,j)=>out.push({ok:r.success,data:r.returnData,tag:slice[j].tag}));
    }
    return out;
  }
  async function loadFromApi(addr) {
    let cursor = null;
    const tokens = [], seenIds = new Set(), seenCursors = new Set();
    for (let page=0; page<60; page++) {
      const url = new URL(API_BASE + "/accounts/" + addr);
      if (cursor !== null) url.searchParams.set("cursor",cursor);
      const d = await fetchJson(url.toString(), {cache:"no-store",headers:{Accept:"application/json"}});
      if (d.status !== "available" || !Array.isArray(d.tokens)) throw new Error("incomplete indexer response");
      for (const t of d.tokens) {
        const id = integer(t.tokenId,"token ID");
        if (id<1 || seenIds.has(id)) throw new Error("duplicate or invalid token ID");
        seenIds.add(id);
        if (t.custody === "wallet") tokens.push({id});
      }
      cursor = d.nextCursor;
      if (cursor === null || cursor === undefined) return {tokens:tokens.sort((a,b)=>a.id-b.id)};
      if (typeof cursor !== "string" || !cursor || seenCursors.has(cursor)) throw new Error("invalid or repeated indexer cursor");
      seenCursors.add(cursor);
    }
    throw new Error("incomplete pagination: page limit reached");
  }
  async function scanLogs(topics) {
    const logs = [];
    for (let from=DEPLOY_BLOCK; from<=state.snapshot; from+=50000) {
      logs.push(...await state.provider.getLogs({address:NFT,fromBlock:from,toBlock:Math.min(from+49999,state.snapshot),topics}));
    }
    return logs;
  }
  async function tokensOf(owner) {
    const incoming = await scanLogs([ethers.id("Transfer(address,address,uint256)"),null,ethers.zeroPadValue(owner.toLowerCase(),32)]);
    // Never subtract all outbound IDs: an NFT may have transferred back afterwards.
    const candidates = [...new Set(incoming.map(l=>integer(BigInt(l.topics[3]),"token ID")))];
    const res = await multicall(state.provider,candidates.map(id=>({tag:id,data:MC3_IFACE.encodeFunctionData("ownerOf",[id])})));
    const ids = [];
    for (const r of res) {
      // Burned tokens revert ownerOf. A final balance check detects missing owned tokens.
      if (!r.ok) continue;
      const [actual] = MC3_IFACE.decodeFunctionResult("ownerOf",r.data);
      if (actual.toLowerCase() === owner.toLowerCase()) ids.push(r.tag);
    }
    return ids.sort((a,b)=>a-b);
  }
  async function loadTokenState(ids) {
    const calls = ids.flatMap(id=>["ownerOf","level","nextMergeHeight"].map(f=>({tag:{id,f},data:MC3_IFACE.encodeFunctionData(f,[id])})));
    const rows = new Map(ids.map(id=>[id,{id}]));
    for (const r of await multicall(state.provider,calls)) {
      if (!r.ok) throw new Error("token read failed: #"+r.tag.id+" "+r.tag.f);
      const [value] = MC3_IFACE.decodeFunctionResult(r.tag.f,r.data);
      const t = rows.get(r.tag.id);
      if (r.tag.f === "ownerOf") {
        if (value.toLowerCase() !== state.account.toLowerCase()) throw new Error("ownership mismatch #"+t.id);
        t.owned = true;
      } else t[r.tag.f === "level" ? "level" : "next"] = integer(value,r.tag.f);
    }
    return ids.map(id=>{
      const t = rows.get(id);
      if (!t.owned || !t.level || t.level>state.maxLevel || t.next === undefined) throw new Error("incomplete token state");
      return {id:t.id,level:t.level,next:t.next};
    });
  }
  function buildPlan(tokens, coreHeight) {
    integer(coreHeight,"core height");
    if (!Number.isInteger(state.maxLevel) || state.maxLevel<1 || state.maxLevel>255) throw new Error("invalid maximum level");
    for (let lvl=2; lvl<state.maxLevel; lvl++) integer(state.cooldowns[lvl],"cooldown L"+lvl);
    const pool = new Map(), seen = new Set(), plan = [];
    const push = (lvl,t)=>{if (!pool.has(lvl)) pool.set(lvl,[]); pool.get(lvl).push(t);};
    for (const t of tokens) {
      if (integer(t.id,"token ID")<1 || seen.has(t.id)) throw new Error("duplicate or invalid token ID");
      seen.add(t.id);
      if (integer(t.level,"level")<1 || t.level>state.maxLevel) throw new Error("invalid level");
      integer(t.next,"token cooldown");
      if (t.level<state.maxLevel) push(t.level,{...t,sim:false});
    }
    for (let lvl=1; lvl<state.maxLevel; lvl++) {
      const group = pool.get(lvl) || [];
      group.sort((a,b)=>a.next-b.next || a.id-b.id);
      while (group.length>=2) {
        const survivor=group.shift(), donor=group.shift(), readyAt=Math.max(survivor.next,donor.next);
        const future=survivor.sim || donor.sim;
        plan.push({n:plan.length+1,survivor:survivor.id,donor:donor.id,level:lvl,
          survivorSim:survivor.sim,donorSim:donor.sim,readyAt,
          status:future ? "future" : readyAt<=coreHeight ? "ready" : "wait",
          eta:future ? "reload required" : readyAt<=coreHeight ? "at snapshot" : "unknown"});
        if (lvl+1<state.maxLevel) {
          const next=integer(Math.max(readyAt,coreHeight)+state.cooldowns[lvl+1],"projected height");
          push(lvl+1,{id:survivor.id,level:lvl+1,next,sim:true});
        }
      }
    }
    return plan;
  }
  function simulate(tokens,plan) {
    const before=new Map(); tokens.forEach(t=>before.set(t.level,(before.get(t.level)||0)+1));
    const after=new Map(before);
    for (const m of plan) {after.set(m.level,(after.get(m.level)||0)-2); after.set(m.level+1,(after.get(m.level+1)||0)+1);}
    return {before,after};
  }
  function renderLadder(el,counts,cls) {
    const levels=[...counts.keys()].sort((a,b)=>a-b), max=Math.max(1,...counts.values());
    el.innerHTML=levels.length ? levels.map(l=>`<div class="rung"><div class="lv">L${l}</div><div class="bar ${cls}"><i style="width:${Math.max(0,Math.round(counts.get(l)/max*100))}%"></i></div><div class="n"><b>${counts.get(l)}</b></div></div>`).join("") : '<div class="hint">no wallet Squeeks</div>';
  }
  function renderMoves(plan) {
    $("movesBody").innerHTML=plan.length ? plan.slice(0,40).map(m=>`<tr><td>${m.n}</td><td>#${m.survivor}</td><td>#${m.donor}</td><td>L${m.level}→${m.level+1}</td><td><span class="pill ${m.status==="ready" && state.mergesOpen ? "ok" : "wait"}">${m.status==="future" ? "future" : !state.mergesOpen ? "gate closed" : m.status==="ready" ? "eligible" : "cooldown"}</span></td><td class="num">${m.readyAt}</td><td class="num">${m.eta}</td></tr>`).join("") : '<tr><td colspan="7">no merge pairs</td></tr>';
    $("planNote").textContent=`${plan.length} projected moves${plan.length>40 ? " (first 40 shown)" : ""}. Future heights are lower bounds assuming earliest inclusion, not promises. Only completed Squeek blocks count; no time ETA. Reload after each merge. Survivor selection: earliest cooldown, then lowest ID. Donors burn permanently. Read-only; no transaction execution.`;
  }
  function clearPlan() {
    state.loaded=false; state.tokens=[]; state.plan=[]; state.cooldowns={}; state.mergesOpen=false;
    $("run").disabled=true; $("replan").disabled=true;
    for (const id of ["held","gate","maxlvl","readyPairs","moves"]) $(id).textContent="—";
    $("ladderNow").textContent="No verified inventory loaded"; $("ladderAfter").textContent="—";
    $("movesBody").textContent="No verified plan"; $("planNote").textContent="";
  }
  function replan() {
    if (!state.loaded) return;
    state.plan=buildPlan(state.tokens,state.coreHeight);
    const {before,after}=simulate(state.tokens,state.plan);
    renderLadder($("ladderNow"),before,"before"); renderLadder($("ladderAfter"),after,"after"); renderMoves(state.plan);
    const eligible=state.mergesOpen ? state.plan.filter(m=>m.status==="ready").length : 0;
    $("readyPairs").textContent=eligible; $("moves").textContent=eligible;
    $("run").disabled=true; $("replan").disabled=false;
    $("warn").style.display="block";
    $("warn").textContent=`Read-only snapshot at Sepolia block ${state.snapshot}. ${state.mergesOpen ? "Gate open" : "Merge gate closed"}. Planning excludes deposited Squeeks; no wallet signs or sends transactions. Re-plan only recomputes this snapshot; Load refreshes chain data.`;
  }
  async function load(addr) {
    if (state.busy) return;
    clearPlan(); state.account=addr;
    if (!ethers.isAddress(addr)) {log("not an address","err"); return;}
    state.busy=true; const version=++state.version;
    $("who").textContent=short(addr); $("load").disabled=true;
    log("Reading wallet inventory and verifying at one Sepolia block…");
    try {
      if (!state.provider) state.provider=await pickProvider();
      if (Number((await state.provider.getNetwork()).chainId)!==11155111) throw new Error("RPC chain mismatch");
      state.snapshot=await state.provider.getBlockNumber();
      const c=new ethers.Contract(NFT,ABI,state.provider), core=new ethers.Contract(CORE,CORE_ABI,state.provider);
      const at={blockTag:state.snapshot};
      const [binding,open,maximum,coreState,balance]=await Promise.all([c.sqkCore(at),c.mergesOpen(at),c.MAXIMUM_LEVEL(at),core.state(at),c.balanceOf(addr,at)]);
      if (binding.toLowerCase()!==CORE) throw new Error("NFT/core binding mismatch");
      if (typeof open!=="boolean") throw new Error("invalid merge gate");
      state.maxLevel=integer(maximum,"maximum level");
      if (state.maxLevel<1 || state.maxLevel>255) throw new Error("invalid maximum level");
      state.coreHeight=integer(coreState.blockHeight === undefined ? coreState[3] : coreState.blockHeight,"core height");
      state.mergesOpen=open;
      let ids;
      try {ids=(await loadFromApi(addr)).tokens.map(t=>t.id);}
      catch (e) {log("Indexer unavailable: "+e.message+"; scanning incoming transfers…"); ids=await tokensOf(addr);}
      if (new Set(ids).size!==ids.length || ids.length!==integer(balance,"wallet balance")) throw new Error("incomplete inventory: balance mismatch; retry Load");
      state.tokens=await loadTokenState(ids);
      for (let lvl=2; lvl<state.maxLevel; lvl++) state.cooldowns[lvl]=integer(await c.cooldownBlocks(lvl,at),"cooldown L"+lvl);
      if (version!==state.version) return;
      state.loaded=true;
      $("held").textContent=state.tokens.length; $("gate").textContent=open ? "open" : "closed";
      $("maxlvl").textContent=state.maxLevel; $("coreHeight").textContent=state.coreHeight;
      $("coreRound").textContent=integer(coreState.settledThroughRound === undefined ? coreState[0] : coreState.settledThroughRound,"round");
      $("coreState").textContent=coreState.paused === true || coreState[7] === true ? "paused" : "snapshot";
      $("coreRate").textContent="no time ETA";
      replan(); log(state.tokens.length+" Squeeks verified; gate "+(open ? "open" : "closed"));
    } catch (e) {
      clearPlan(); $("warn").style.display="block"; $("warn").textContent="Read failed. No usable plan; retry Load.";
      log(String(e.message || e),"err");
    } finally {state.busy=false; $("load").disabled=false;}
  }
  async function runLadder() {log("Read-only planner: transaction execution disabled.","err");}
  async function connect() {
    if (!window.ethereum) {log("No injected wallet found; enter a public address.","err"); return;}
    try {
      const accounts=await window.ethereum.request({method:"eth_requestAccounts"});
      if (!accounts.length || !ethers.isAddress(accounts[0])) throw new Error("no wallet account");
      $("addr").value=accounts[0]; await load(accounts[0]);
      $("disconnect").style.display="";
    } catch (e) {log(String(e.message || e),"err");}
  }
  // ---------- boot ----------
  $("load").onclick=()=>load($("addr").value.trim());
  $("addr").addEventListener("keydown",e=>{if(e.key==="Enter") load($("addr").value.trim());});
  $("connect").onclick=connect; $("run").onclick=runLadder; $("replan").onclick=replan;
  $("disconnect").onclick=()=>{++state.version; clearPlan(); state.account=null; $("who").textContent="—"; $("disconnect").style.display="none";};
  if (window.ethereum && window.ethereum.on) {
    const invalidate=()=>{++state.version; clearPlan(); log("Wallet account/network changed. Reload the selected address.");};
    window.ethereum.on("accountsChanged",invalidate); window.ethereum.on("chainChanged",invalidate);
  }
})();
</script>
</body>
</html>
"""

out = pathlib.Path(__file__).parent / "planner.html"
out.write_text(HTML, encoding="utf-8")
print(out, len(HTML), "bytes")
