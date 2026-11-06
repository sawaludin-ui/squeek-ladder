// Node.js / Squeek Sprint / source + deployment contract regression tests.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const test=require('node:test'),root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,p),'utf8');
test('authored UI, public source and deployed runtime remain byte-identical',()=>{
  for(const p of ['index.html','sprint.css','sprint.js','favicon.svg','README.md'])assert.equal(read(p),read('src/'+p),p);
  for(const p of ['index.html','sprint.css','sprint.js','favicon.svg','README.md','sprint-engine.js','status-validator.js'])assert.equal(read(p),read('site/'+p),p);
});
test('submitted origin identifies the actual playable project and wallet',()=>{
  const html=read('index.html');assert.match(html,/<title>Squeek Sprint/);
  assert.match(html,/502c8855-e4e0-4067-bf83-d2de88597fa3/);
  assert.match(html,/0x8346Ac89e4B3297F014050dFe8baf87bF7567e63/);
  assert.match(read('README.md'),/Built on Squeekchain — https:\/\/docs.squeekchain.com/);
  assert.doesNotMatch(html,/ethers|merge planner|Genesis Navigator/);
});
test('game has a separately loaded local validator and engine before the renderer',()=>{
  const html=read('index.html');
  assert.ok(html.indexOf('status-validator.js')<html.indexOf('sprint-engine.js'));
  assert.ok(html.indexOf('sprint-engine.js')<html.indexOf('src="sprint.js"'));
  assert.doesNotMatch(html,/<script[^>]+src="https?:/);
});
test('all UI IDs used by the renderer exist exactly once in the markup',()=>{
  const html=read('index.html'),ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(new Set(ids).size,ids.length);
  for(const m of read('sprint.js').matchAll(/\$\('([^']+)'\)/g))assert.ok(ids.includes(m[1]),'Missing UI id '+m[1]);
});
test('game production code contains no test feed or credential / wallet signing path',()=>{
  const js=read('sprint.js');assert.match(js,/api.squeekchain.com\/v1\/status/);
  assert.doesNotMatch(js,/Math\.random|innerHTML|eth_sendTransaction|personal_sign|sessionStorage|Bearer |fixtures\//);
  assert.match(js,/E\.parseStatus/);assert.match(js,/new E\.Game/);
  assert.match(js,/visibilitychange/);assert.match(js,/pointerup/);
});
test('deployment hides environment files and adds content security headers',()=>{
  assert.match(read('site/.vercelignore'),/\.env\*/);
  const config=JSON.parse(read('site/vercel.json'));
  assert.ok(config.headers.some(x=>x.headers.some(h=>h.key==='Content-Security-Policy')));
});
