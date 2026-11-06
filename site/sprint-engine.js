// JavaScript / Squeek Sprint / browser + Node / validated public wheel measurements.
(function(root,factory){
  'use strict';
  const node=typeof module==='object'&&module.exports;
  const api=factory(node?require('./status-validator.js'):root.SqueekStatusSchema);
  if(node)module.exports=api;else root.SprintEngine=api;
})(typeof globalThis==='object'?globalThis:this,function(validate){
  'use strict';
  function parseStatus(data,now=Date.now()){
    if(!validate(data))throw Error('Unsupported or malformed Squeekchain status schema');
    const m=data.measurement;
    if(!m)throw Error('No measurement');
    const work=BigInt(m.cumulativeWorkUnits);
    if(work>18446744073709551615n)throw Error('Work counter exceeds uint64');
    return {...m,work,observedMs:Date.parse(m.observedAt),receivedMs:Date.parse(m.receivedAt),fetchedMs:now};
  }
  function isLive(m,now=Date.now()){
    return !!(m&&m.freshness==='online'&&m.provenance==='hardware'&&m.coreStatus!=='COUNTER_FAULT'&&now-m.receivedMs>=-5000&&now-m.observedMs>=-5000&&now-m.receivedMs<=120000&&now-m.observedMs<=120000);
  }
  class Game{
    constructor(mode,measurement,now=Date.now()){
      if(!['live','practice'].includes(mode))throw Error('Unknown game mode');
      if(mode==='live'&&(!isLive(measurement,now)||measurement.rpmMilli<=0||measurement.coreStatus==='IDLE'))throw Error('A fresh, moving hardware wheel is required');
      const input=mode==='live'?measurement:null;
      this.mode=mode;this.measurement=input;this.lastWork=input?.work??0n;
      this.work=0n;this.epoch=input?.counterEpoch??'practice';this.elapsed=0;
      this.score=0;this.seeds=0;this.crates=0;this.charge=0;this.lives=3;this.lane=1;
      this.objects=[];this.events=[];this.spawnClock=0;this.gatesOpened=0;this.biome=0;
      this.shield=0;this.invincible=0;this.speed=0;this.scrolled=0;
      this.paused=false;this.done=false;this.won=false;this.invalidReason='';
      this.trustedObservedMs=input?.observedMs??-Infinity;this.rebaseline=false;
      this.seed=2166136261;
      for(const c of `${this.epoch}:${this.lastWork}`)this.seed=Math.imul(this.seed^c.charCodeAt(0),16777619)>>>0;
    }
    random(){this.seed=(Math.imul(1664525,this.seed)+1013904223)>>>0;return this.seed/4294967296;}
    emit(kind,text){this.events.push({kind,text});if(this.events.length>20)this.events.shift();}
    get paused(){return this._paused??false;}
    set paused(value){
      if(this._paused&&!value&&this.mode==='live')this.rebaseline=true;
      this._paused=!!value;
    }
    apply(m,now=Date.now()){
      if(this.mode!=='live'||this.done)return;
      if(m.observedMs<this.trustedObservedMs)return;
      if(!isLive(m,now)){
        this.measurement=m;this.rebaseline=true;return;
      }
      this.trustedObservedMs=m.observedMs;
      if(m.counterEpoch!==this.epoch||m.work<this.lastWork){
        this.invalidReason='Wheel counter changed. Start a new expedition.';this.done=true;return;
      }
      const delta=m.work-this.lastWork;this.lastWork=m.work;this.measurement=m;
      if(this.paused)return;
      if(this.rebaseline){this.rebaseline=false;return;}
      const before=this.work/5n;this.work+=delta;
      const opened=this.work/5n-before;
      this.gatesOpened=Number(this.work/5n);this.biome=Number(this.work/12n%3n);
      // Catch-up readings never flood the board with thousands of objects.
      for(let i=0;i<Number(opened>3n?3n:opened);i++){
        const lane=Math.floor(this.random()*3),y=-i*.18;
        this.objects.push({kind:'supply',lane,y});
      }
      if(opened>0n)this.emit('supply','Hamster-powered supply drop!');
    }
    waiting(now=Date.now()){
      if(this.paused)return 'Paused — your expedition is safe.';
      if(this.mode==='practice')return '';
      if(!isLive(this.measurement,now))return 'Live feed unavailable. Waiting for a fresh hardware reading.';
      if(this.measurement.rpmMilli<=0||this.measurement.coreStatus==='IDLE')return 'The hamster is resting. Your expedition will resume when the wheel moves.';
      return '';
    }
    move(direction){if(!this.done&&!this.paused)this.lane=Math.max(0,Math.min(2,this.lane+direction));}
    activateShield(){
      if(this.done||this.paused||this.charge<3||this.shield>0)return false;
      this.charge-=3;this.shield=4;this.emit('shield','Seed shield activated');return true;
    }
    spawn(){
      const rock=Math.floor(this.random()*3),safe=(rock+1+Math.floor(this.random()*2))%3;
      this.objects.push({kind:'rock',lane:rock,y:-.08});
      this.objects.push({kind:'seed',lane:safe,y:-.08});
      if(this.random()<.4)this.objects.push({kind:'seed',lane:safe,y:-.22});
    }
    tick(dt,now=Date.now()){
      if(this.done||this.waiting(now))return;
      dt=Math.min(.05,Math.max(0,dt));this.elapsed=Math.min(60,this.elapsed+dt);
      const rpm=this.mode==='practice'?65:this.measurement.rpmMilli/1000;
      this.speed=.27+Math.min(180,rpm)/240;
      this.scrolled+=dt*this.speed;this.shield=Math.max(0,this.shield-dt);this.invincible=Math.max(0,this.invincible-dt);
      this.spawnClock-=dt;
      if(this.spawnClock<=0){this.spawn();this.spawnClock=1.2/Math.max(.65,this.speed);}
      for(const obj of this.objects){
        const before=obj.y;obj.y+=dt*this.speed;
        if(!obj.hit&&before<=.87&&obj.y>=.77&&obj.lane===this.lane){
          obj.hit=true;
          if(obj.kind==='rock'){
            if(this.shield>0){this.shield=0;this.emit('shield','Rock blocked');}
            else if(this.invincible<=0){this.lives--;this.invincible=1.2;this.emit('damage','Ouch! Switch lanes to dodge the rocks.');}
          }else if(obj.kind==='seed'){
            this.seeds++;this.score+=10;this.charge=Math.min(6,this.charge+1);this.emit('seed','+10');
          }else{this.crates++;this.score+=50;this.charge=Math.min(6,this.charge+2);this.emit('supply','Supply rescued +50');}
        }
      }
      this.objects=this.objects.filter(x=>x.y<1.12&&!x.hit);
      if(this.lives<=0){this.done=true;this.emit('end','Expedition over');}
      else if(this.elapsed>=60){this.done=true;this.won=true;this.emit('end','Expedition complete!');}
      if(this.mode==='practice')this.biome=Math.floor(this.elapsed/20)%3;
    }
    medal(){
      if(this.mode!=='live'||!this.won||this.invalidReason)return null;
      if(this.crates>=2&&this.seeds>=15)return 'gold';
      if(this.crates>=1&&this.seeds>=8)return 'silver';
      return 'bronze';
    }
  }
  return {parseStatus,isLive,Game};
});
