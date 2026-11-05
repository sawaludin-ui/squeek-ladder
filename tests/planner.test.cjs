const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function app(options={}) {
  const nodes = new Map();
  const node = () => ({textContent:'', innerHTML:'', style:{}, disabled:false, value:'', children:[], prepend(x){this.children.unshift(x);}, addEventListener(){}});
  const document = {getElementById(id){if(!nodes.has(id)) nodes.set(id,node()); return nodes.get(id);}, createElement:node};
  const source = options.source || fs.readFileSync(path.join(__dirname,'../build_site.py'),'utf8');
  let script = source.split('<script>')[1].split('</script>')[0];
  script = script.replace('  // ---------- boot ----------', '  globalThis.app = {state, buildPlan, load, loadFromApi, tokensOf, loadTokenState, replan, runLadder, log, fetchJson, pickProvider, connect, simulate}; '+(options.boot ? '' : 'return;')+'\n  // ---------- boot ----------');
  const ctx = {document, window:options.window || {}, console, URL, AbortController, setTimeout, clearTimeout,
    ethers:{Interface:class {encodeFunctionData(f,args){return {f,args};} decodeFunctionResult(f,data){return data;}},
      isAddress:a=>/^0x[0-9a-f]{40}$/i.test(a), id:x=>x, zeroPadValue:x=>x,
      Contract:class {constructor(address,abi,p){return p.contract(address,abi);}}},
    fetch:async()=>{throw Error('unmocked network');}};
  vm.createContext(ctx); vm.runInContext(script,ctx);
  return {a:ctx.app, ctx, nodes, document};
}
const tokens = (n) => Array.from({length:n},(_,i)=>({id:i+1,level:1,next:0}));
test('future steps preserve survivor IDs but are never ready now',()=>{
  const {a}=app(); a.state.maxLevel=3; a.state.cooldowns={2:0,3:0};
  const p=a.buildPlan(tokens(4),100);
  assert.deepEqual(Array.from(p,m=>m.level),[1,1,2]);
  assert.equal(p[2].survivor,1); assert.equal(p[2].donor,3);
  assert.equal(p[2].status,'future');
});
test('missing cooldown cannot create a zero-cooldown plan',()=>{
  const {a}=app(); a.state.maxLevel=3; a.state.cooldowns={};
  assert.throws(()=>a.buildPlan(tokens(2),0),/cooldown/i);
});
module.exports={app,tokens};
