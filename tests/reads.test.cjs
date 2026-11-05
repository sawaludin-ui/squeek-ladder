const test = require('node:test');
const assert = require('node:assert/strict');
const {app,tokens} = require('./planner.test.cjs');
const OWNER='0x8346Ac89e4B3297F014050dFe8baf87bF7567e63';
const CORE='0xfd6c166d4b8e2962e65746a13e5a0797cd4de0c4';
function fixture(opts={}) {
  const env=app(opts.appOptions), at=12057775, reads=[];
  const t=opts.tokens || tokens(4);
  env.ctx.fetch=async()=>({ok:true,json:async()=>({status:'available',tokens:t.map(x=>({tokenId:x.id,custody:'wallet'})),nextCursor:null})});
  const check=(o)=>{assert.equal(o.blockTag,at);};
  const view=(name,val)=>async(...args)=>{check(args.at(-1)); reads.push(name); return val;};
  env.a.state.provider={getNetwork:async()=>({chainId:11155111n}), getBlockNumber:async()=>at,
    getLogs:async(filter)=>{assert.equal(filter.toBlock,at); return t.map(x=>({topics:['transfer',null,OWNER,'0x'+x.id.toString(16)]}));},
    contract(address) {
      if (address.toLowerCase()===CORE) return {state:view('core.state',[9,0,0,100,0,1,0,false])};
      if (address.toLowerCase()==='0xca11bde05977b3631167028862be2a173976ca11') return {aggregate3:{staticCall:async(calls,o)=>{
        check(o);
        const result=calls.map(call=>{
          const {f,args}=call.callData, id=args[0]; reads.push(f);
          if (opts.failToken===f) return {success:false,returnData:[]};
          const tok=t.find(x=>x.id===id);
          return {success:true,returnData:[f==='ownerOf' ? opts.owner || OWNER : f==='level' ? tok.level : tok.next]};
        });
        return opts.shortMulticall ? result.slice(1) : result;
      }}};
      return {sqkCore:view('binding',CORE),mergesOpen:view('gate',opts.open!==false),MAXIMUM_LEVEL:view('maximum',3),
        balanceOf:view('balance',opts.balance ?? t.length),cooldownBlocks:async(lvl,o)=>{
          check(o); if(opts.failCooldown) throw Error('cooldown offline'); return 5;
        }};
    }};
  return {...env,reads};
}
test('actual load indexer path renders a fully verified snapshot without scope errors',async()=>{
  const e=fixture(); await e.a.load(OWNER);
  assert.equal(e.a.state.loaded,true); assert.equal(e.a.state.plan.length,3);
  assert.equal(e.document.getElementById('moves').textContent,2);
  assert.equal(e.document.getElementById('run').disabled,true);
  assert.match(e.document.getElementById('planNote').textContent,/No time ETA|no time ETA/);
  assert.equal(e.reads.filter(x=>x==='ownerOf').length,4);
});
test('fallback includes transferred-away-then-back tokens and verifies all state',async()=>{
  const e=fixture(); e.ctx.fetch=async()=>{throw Error('indexer offline');};
  const provider=e.a.state.provider, original=provider.getLogs;
  provider.getLogs=async(filter)=>filter.topics[1] ? [{topics:['transfer',OWNER,null,'0x1']}] : original(filter);
  await e.a.load(OWNER); assert.equal(e.a.state.loaded,true);
  assert.equal(e.a.state.tokens[0].id,1);
});
for(const [name,opts] of [
  ['cooldown failure',{failCooldown:true}],['failed level call',{failToken:'level'}],
  ['failed next height call',{failToken:'nextMergeHeight'}],['failed owner read',{failToken:'ownerOf'}],
  ['short multicall result',{shortMulticall:true}],['incomplete inventory',{balance:5}],
  ['wrong owner',{owner:'0x1111111111111111111111111111111111111111'}]
]) test(name+' discards stale plans and fails closed',async()=>{
  const e=fixture(opts); e.a.state.loaded=true; e.a.state.plan=[{status:'ready'}];
  await e.a.load(OWNER);
  assert.equal(e.a.state.loaded,false); assert.equal(e.a.state.plan.length,0);
  assert.equal(e.document.getElementById('run').disabled,true);
  assert.match(e.document.getElementById('warn').textContent,/Read failed/);
});
test('wrong RPC chain fails closed before reading or signing',async()=>{
  const e=fixture(); e.a.state.provider.getNetwork=async()=>({chainId:1n});
  await e.a.load(OWNER); assert.equal(e.a.state.loaded,false); assert.equal(e.reads.length,0);
});
test('closed gate reports no eligible pairs despite unlocked tokens',async()=>{
  const e=fixture({open:false}); await e.a.load(OWNER);
  assert.equal(e.document.getElementById('readyPairs').textContent,0);
  assert.equal(e.document.getElementById('moves').textContent,0);
  assert.match(e.document.getElementById('movesBody').innerHTML,/gate closed/);
});
test('untrusted errors are rendered as text, never HTML',()=>{
  const e=app(), payload='<img src=x onerror=alert(1)>';
  e.a.log(payload,'err'); const row=e.document.getElementById('log').children[0];
  assert.equal(row.textContent,payload); assert.equal(row.innerHTML,'');
});
test('repeated pagination cursor fails closed',async()=>{
  const e=app(); e.ctx.fetch=async()=>({ok:true,json:async()=>({status:'available',tokens:[],nextCursor:'same'})});
  await assert.rejects(e.a.loadFromApi(OWNER),/repeated/);
});
test('page limit cannot return partial success',async()=>{
  const e=app(); let page=0;
  e.ctx.fetch=async()=>({ok:true,json:async()=>({status:'available',tokens:[],nextCursor:'page'+(++page)})});
  await assert.rejects(e.a.loadFromApi(OWNER),/page limit/); assert.equal(page,60);
});
test('duplicate IDs and malformed indexer pages fail closed',async()=>{
  for(const data of [{status:'available'}, {status:'available',tokens:[{tokenId:1,custody:'wallet'},{tokenId:1,custody:'wallet'}]}]) {
    const e=app(); e.ctx.fetch=async()=>({ok:true,json:async()=>data});
    await assert.rejects(e.a.loadFromApi(OWNER),/incomplete|duplicate/);
  }
});
test('timeout includes response body, aborts fetch and rejects',async()=>{
  const e=app(); let signal;
  e.ctx.fetch=async(u,o)=>{signal=o.signal; return {ok:true,json:()=>new Promise(()=>{})};};
  await assert.rejects(e.a.fetchJson('https://example.invalid',{},5),/timeout/);
  assert.equal(signal.aborted,true);
});
test('HTTP errors do not masquerade as empty inventories',async()=>{
  const e=app(); e.ctx.fetch=async()=>({ok:false,status:503,json:async()=>({})});
  await assert.rejects(e.a.loadFromApi(OWNER),/HTTP 503/);
});
test('disabled execution never requests a signer or transaction',async()=>{
  const e=fixture(); e.ctx.window.ethereum={request:()=>{throw Error('unexpected wallet action');}};
  await e.a.load(OWNER); await e.a.runLadder();
  assert.equal(e.document.getElementById('run').disabled,true);
  assert.match(e.document.getElementById('log').children[0].textContent,/execution disabled/);
});
test('wallet connection requests only address, without chain switch or signer',async()=>{
  const e=fixture(), methods=[];
  e.ctx.window.ethereum={request:async({method})=>{methods.push(method);return [OWNER];}};
  await e.a.connect(); assert.deepEqual(methods,['eth_requestAccounts']); assert.equal(e.a.state.loaded,true);
});
test('account or chain change invalidates a loaded plan at actual boot handlers',async()=>{
  for(const event of ['accountsChanged','chainChanged']) {
    const handlers={}, window={ethereum:{on:(name,fn)=>{handlers[name]=fn;}}};
    const e=fixture({appOptions:{boot:true,window}});
    await e.a.load(OWNER); assert.equal(e.a.state.loaded,true);
    handlers[event]();
    assert.equal(e.a.state.loaded,false); assert.equal(e.a.state.plan.length,0);
    assert.equal(e.document.getElementById('run').disabled,true);
    e.a.replan(); assert.equal(e.a.state.plan.length,0);
  }
});
test('disconnect during an outstanding read cannot resurrect an old plan',async()=>{
  const e=fixture({tokens:[],appOptions:{boot:true}}); let finish;
  e.ctx.fetch=()=>new Promise(resolve=>{finish=()=>resolve({ok:true,json:async()=>({status:'available',tokens:[],nextCursor:null})});});
  const pending=e.a.load(OWNER);
  for(let i=0;i<20 && !finish;i++) await Promise.resolve();
  assert.ok(finish); e.document.getElementById('disconnect').onclick(); finish();
  await pending;
  assert.equal(e.a.state.loaded,false); assert.equal(e.a.state.plan.length,0);
  assert.equal(e.document.getElementById('run').disabled,true);
});
test('provider discovery verifies chain, sets deadlines and disables gateway RPC batching',async()=>{
  const e=app(), providers=[], urls=[];
  e.ctx.ethers.FetchRequest=class {constructor(url){this.url=url;}};
  e.ctx.ethers.JsonRpcProvider=class {
    constructor(request,network,options){assert.equal(request.timeout,15000);assert.equal(options.batchMaxCount,1);urls.push(request.url);providers.push(this);}
    async getNetwork(){return {chainId:providers.indexOf(this)===0 ? 1n : 11155111n};}
    async getBlockNumber(){return 123;}
    destroy(){this.destroyed=true;}
  };
  const p=await e.a.pickProvider();
  assert.equal(p,providers[1]); assert.equal(providers[0].destroyed,true); assert.equal(urls.length,2);
});
test('invalid numeric state and unsafe integers never become ready plans',()=>{
  for(const next of [null,false,[],{},' ',1.5,Number.MAX_SAFE_INTEGER+1]) {
    const e=app(); e.a.state.maxLevel=3; e.a.state.cooldowns={2:5};
    assert.throws(()=>e.a.buildPlan([{id:1,level:1,next},{id:2,level:1,next:0}],100),/invalid|missing/);
  }
});
