// Node.js / Squeek Sprint / deterministic engine and official feed contract.
'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const enginePath=path.join(__dirname,'../sprint-engine.js');
test('the playable game ships a separately testable feed-aware engine',()=>{
  assert.ok(fs.existsSync(enginePath),'Missing feed-aware Squeek Sprint engine');
  assert.equal(typeof require(enginePath).parseStatus,'function');
});
const E=require(enginePath);
const fixture=require('./fixtures/status.json');
const NOW=Date.parse('2026-11-06T10:00:00Z');
function sample(overrides={}){
  const d=structuredClone(fixture);
  Object.assign(d.measurement,{freshness:'online',observedAt:new Date(NOW).toISOString(),receivedAt:new Date(NOW).toISOString(),coreStatus:'ACTIVE',provenance:'hardware',rpmMilli:60000,cumulativeWorkUnits:'9007199254740993'},overrides);
  return d;
}
test('freshness expires from original receivedAt, never from the most recent fetch',()=>{
  const m=E.parseStatus(sample(),NOW+119000);
  assert.equal(E.isLive(m,NOW+119000),true);
  assert.equal(E.isLive(m,NOW+120001),false);
});
test('schema and formats reject unsupported versions, corrupt counters and missing fields',()=>{
  for(const mutate of [d=>d.schemaVersion=2,d=>delete d.measurement.receivedAt,d=>d.measurement.cumulativeWorkUnits='-1',d=>d.measurement.cumulativeWorkUnits='18446744073709551616',d=>d.measurement.counterEpoch='invalid',d=>d.measurement.rpmMilli=-1]){
    const d=sample();mutate(d);assert.throws(()=>E.parseStatus(d,NOW));
  }
});
test('live mode refuses simulated, faulted, stale, missing and future readings',()=>{
  for(const patch of [{provenance:'simulated'},{coreStatus:'COUNTER_FAULT'},{freshness:'stale'},{receivedAt:new Date(NOW+60000).toISOString()}])assert.equal(E.isLive(E.parseStatus(sample(patch),NOW),NOW),false);
  assert.equal(E.isLive(null,NOW),false);
});
test('work units remain exact beyond Number.MAX_SAFE_INTEGER',()=>{
  assert.equal(E.parseStatus(sample(),NOW).work,9007199254740993n);
});
function reading(work='100',patch={}){return E.parseStatus(sample({cumulativeWorkUnits:work,...patch}),NOW);}
test('live expeditions require a fresh active hardware feed',()=>{
  assert.throws(()=>new E.Game('live',null,NOW));
  assert.throws(()=>new E.Game('live',reading('100',{rpmMilli:0}),NOW));
  assert.equal(new E.Game('practice',null,NOW).mode,'practice');
});
test('practice layouts never depend on real wheel activity',()=>{
  const a=new E.Game('practice',reading('100'),NOW),b=new E.Game('practice',reading('500'),NOW);
  for(let i=0;i<40;i++){a.tick(.05,NOW);b.tick(.05,NOW);}
  assert.deepEqual(a.objects,b.objects);assert.equal(a.epoch,'practice');
});
test('idle hardware cannot start a live run even if its RPM is nonzero',()=>{
  assert.throws(()=>new E.Game('live',reading('100',{coreStatus:'IDLE'}),NOW));
});
test('actual hamster work opens supply gates and changes the biome',()=>{
  const g=new E.Game('live',reading(),NOW);
  g.apply(reading('105',{receivedAt:new Date(NOW+5000).toISOString(),observedAt:new Date(NOW+5000).toISOString()}),NOW+5000);
  assert.equal(g.work,5n);assert.equal(g.gatesOpened,1);
  assert.equal(g.objects.filter(x=>x.kind==='supply').length,1);
  g.apply(reading('115',{receivedAt:new Date(NOW+10000).toISOString(),observedAt:new Date(NOW+10000).toISOString()}),NOW+10000);
  assert.equal(g.work,15n);assert.equal(g.biome,1);
});
test('duplicate work readings cannot mint duplicate supplies',()=>{
  const g=new E.Game('live',reading(),NOW);const next=reading('105');
  g.apply(next,NOW);g.apply(next,NOW);
  assert.equal(g.work,5n);assert.equal(g.gatesOpened,1);
});
test('out-of-order status cannot rewind the trusted wheel state',()=>{
  const g=new E.Game('live',reading(),NOW);
  g.apply(reading('110',{receivedAt:new Date(NOW+5000).toISOString(),observedAt:new Date(NOW+5000).toISOString()}),NOW+5000);
  g.apply(reading('105'),NOW+5000);
  assert.equal(g.work,10n);assert.equal(g.invalidReason,'');
});
test('counter reset and epoch changes end the live run without a local medal',()=>{
  for(const next of [reading('99'),reading('101',{counterEpoch:'67f802bd-e589-4a68-90d3-7ed7f84f60ce'})]){
    const g=new E.Game('live',reading(),NOW);g.apply(next,NOW);
    assert.equal(g.done,true);assert.ok(g.invalidReason);assert.equal(g.medal(),null);
  }
});
test('stale or resting hamster freezes live time and obstacles; practice is independent',()=>{
  const g=new E.Game('live',reading(),NOW);g.tick(.05,NOW+121000);assert.equal(g.elapsed,0);
  g.apply(reading('100',{rpmMilli:0}),NOW);g.tick(.05,NOW);assert.equal(g.elapsed,0);
  const p=new E.Game('practice',null,NOW);p.tick(.05,NOW);assert.equal(p.elapsed,.05);
});
test('RPM changes the live tempo during an existing run',()=>{
  const g=new E.Game('live',reading(),NOW);g.tick(.05,NOW);const before=g.speed;
  g.apply(reading('101',{rpmMilli:140000}),NOW);g.tick(.05,NOW);assert.ok(g.speed>before);
});
test('seed pickup, shields, rocks and survival expiry obey game rules',()=>{
  const g=new E.Game('practice',null,NOW);
  g.objects=[{kind:'seed',lane:1,y:.82}];g.tick(.01,NOW);assert.equal(g.seeds,1);assert.equal(g.score,10);
  g.charge=3;assert.equal(g.activateShield(),true);assert.equal(g.charge,0);
  g.objects=[{kind:'rock',lane:1,y:.82}];g.tick(.01,NOW);assert.equal(g.lives,3);assert.equal(g.shield,0);
  g.invincible=0;g.objects=[{kind:'rock',lane:1,y:.82}];g.tick(.01,NOW);assert.equal(g.lives,2);
  g.elapsed=59.99;g.tick(.05,NOW);assert.equal(g.done,true);assert.equal(g.won,true);
});
test('pause excludes hamster work produced while the player is away',()=>{
  const g=new E.Game('live',reading(),NOW);g.paused=true;g.apply(reading('120'),NOW);
  assert.equal(g.work,0n);g.tick(.05,NOW);assert.equal(g.elapsed,0);
  g.paused=false;g.apply(reading('125'),NOW);assert.equal(g.work,0n);
  g.apply(reading('130'),NOW);assert.equal(g.work,5n);
});
test('pause followed by resume without polling rebases the first hardware reading',()=>{
  const g=new E.Game('live',reading(),NOW);
  g.paused=true;g.paused=false;g.apply(reading('120'),NOW);
  assert.equal(g.work,0n);assert.equal(g.gatesOpened,0);
  g.apply(reading('125'),NOW);assert.equal(g.work,5n);
});
test('network failure does not erase the trusted timestamp high-water mark',()=>{
  const g=new E.Game('live',reading(),NOW);
  g.apply(reading('120',{observedAt:new Date(NOW+1000).toISOString()}),NOW+1000);
  g.measurement=null;
  g.apply(reading('110'),NOW+1000);
  assert.equal(g.done,false);assert.equal(g.lastWork,120n);assert.equal(g.measurement,null);
  g.apply(reading('125',{observedAt:new Date(NOW+2000).toISOString()}),NOW+2000);
  assert.equal(g.done,false);
});
test('simulated readings cannot contaminate hardware counter or epoch',()=>{
  const g=new E.Game('live',reading(),NOW);
  g.apply(reading('1000',{provenance:'simulated',counterEpoch:'67f802bd-e589-4a68-90d3-7ed7f84f60ce'}),NOW);
  assert.equal(g.lastWork,100n);assert.equal(g.work,0n);assert.ok(g.waiting(NOW));
  g.apply(reading('105'),NOW);assert.equal(g.done,false);assert.equal(g.work,0n);
  g.apply(reading('110'),NOW);assert.equal(g.work,5n);
});
test('deterministic practice layout and at least one unobstructed lane per row',()=>{
  const a=new E.Game('practice',null,NOW),b=new E.Game('practice',null,NOW);
  for(let i=0;i<80;i++){a.tick(.05,NOW);b.tick(.05,NOW);}
  assert.deepEqual(a.objects,b.objects);
  const rows=new Map();for(const x of a.objects.filter(x=>x.kind==='rock')){const k=x.y.toFixed(3);rows.set(k,(rows.get(k)||0)+1);}
  assert.ok([...rows.values()].every(n=>n<3));
});
