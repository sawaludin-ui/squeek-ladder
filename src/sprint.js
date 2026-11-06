// JavaScript / Squeek Sprint / canvas renderer + accessible UI + public API only.
'use strict';
(() => {
  const $=id=>document.getElementById(id),E=globalThis.SprintEngine;
  const canvas=$('game'),ctx=canvas.getContext('2d');
  const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const names=['SUNLIT MEADOW','AMBER CANYON','MOONLIT GROVE'];
  let game=null,measurement=null,lastFrame=0,nextFeed=0,fetching=false,feedError='',audio=null,sound=false;
  let etag='',lastPayload=null,feedFailures=0,trustedObservedMs=-Infinity;
  let w=720,h=600,playerLane=1,toastUntil=0,saved={liveBest:null,practiceBest:null,medals:[]};
  const STORE='squeek-sprint-v2';
  try{
    const s=JSON.parse(localStorage.getItem(STORE));
    if(s&&Array.isArray(s.medals)){
      for(const key of ['liveBest','practiceBest'])if(Number.isSafeInteger(s[key])&&s[key]>=0)saved[key]=s[key];
      saved.medals=s.medals.filter(x=>['bronze','silver','gold'].includes(x));
    }
  }catch{/* Storage is optional; play still works in private mode. */}
  function journal(){
    $('best').textContent=saved.liveBest??'—';$('practice-best').textContent=saved.practiceBest??'—';
    $('medals').replaceChildren(...['bronze','silver','gold'].map(name=>{
      const b=document.createElement('span');b.className='medal'+(saved.medals.includes(name)?' earned':'');
      b.textContent=(saved.medals.includes(name)?'✓ ':'○ ')+name[0].toUpperCase()+name.slice(1);return b;
    }));
  }
  function beep(kind){
    if(!sound)return;
    try{
      const A=window.AudioContext||window.webkitAudioContext;if(!A)return;
      audio??=new A();if(audio.state==='suspended')void audio.resume().catch(()=>{});
      const osc=audio.createOscillator(),gain=audio.createGain();osc.connect(gain);gain.connect(audio.destination);
      const frequency={seed:740,supply:1040,damage:150,shield:430,end:520}[kind]||520;
      osc.type=kind==='damage'?'triangle':'sine';osc.frequency.setValueAtTime(frequency,audio.currentTime);
      osc.frequency.exponentialRampToValueAtTime(frequency*.7,audio.currentTime+.12);
      gain.gain.setValueAtTime(.035,audio.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.15);
      osc.start();osc.stop(audio.currentTime+.16);
    }catch{/* Unsupported or blocked audio must not stop the game. */}
  }
  function toast(text){$('toast').textContent=text;toastUntil=performance.now()+1600;}
  function start(mode){
    try{game=new E.Game(mode,measurement);}
    catch(e){toast(e.message);return;}
    playerLane=1;$('overlay').hidden=true;$('pause').disabled=false;$('pause').textContent='Pause';$('restart').disabled=false;
    $('mode-label').textContent=mode==='live'?'LIVE EXPEDITION / HARDWARE':'PRACTICE / LOCAL SIMULATION';
    $('wait').hidden=true;canvas.focus({preventScroll:true});lastFrame=0;beep('shield');update();
  }
  function finish(){
    $('pause').disabled=true;$('wait').hidden=true;$('overlay').hidden=false;
    const mode=game.mode==='live'?'Live':'Practice',key=game.mode==='live'?'liveBest':'practiceBest';
    if(!game.invalidReason){saved[key]=Math.max(saved[key]??0,game.score);const medal=game.medal();if(medal&&!saved.medals.includes(medal))saved.medals.push(medal);}
    let stored=true;try{localStorage.setItem(STORE,JSON.stringify(saved));}catch{stored=false;}
    journal();$('overlay-kicker').textContent=game.invalidReason?'COUNTER SAFETY STOP':mode.toUpperCase()+' / EXPEDITION '+(game.won?'COMPLETE':'ENDED');
    $('overlay-title').textContent=game.invalidReason?'A new wheel chapter.':game.won?'Home, sweet burrow.':'A brave little attempt.';
    $('overlay-text').textContent=game.invalidReason||`${game.score} points · ${game.seeds} seeds · ${game.crates} supplies rescued. ${game.mode==='live'?game.work+' actual work units during this run.':'Practice uses a fixed, simulated pace.'}`;
    $('overlay-fine').textContent=game.medal()?`Local ${game.medal()} keepsake earned. Not an official Genesis badge.`:stored?'Personal records stay in this browser. Ready for another trail?':'Browser storage unavailable. This run cannot be saved.';
    $('practice').textContent='Practice again →';$('overlay-icon').textContent=game.won?'✓':'↗';$('mode-label').textContent=mode.toUpperCase()+' / RUN ENDED';
    beep('end');$('practice').focus({preventScroll:true});
  }
  function pause(){if(!game||game.done)return;game.paused=!game.paused;$('pause').textContent=game.paused?'Resume':'Pause';update();}
  function update(){
    if(!game)return;
    $('score').textContent=game.score;$('time').textContent=Math.ceil(60-game.elapsed)+'s';
    $('lives').textContent='● '.repeat(Math.max(0,game.lives)).trim();$('lives').setAttribute('aria-label',game.lives+' lives');
    $('work').textContent=game.mode==='live'?game.work.toString():'Practice';$('crates').textContent=game.crates;
    const remaining=game.mode==='live'?5-Number(game.work%5n):5;
    $('supply-fill').style.width=(game.mode==='live'?Number(game.work%5n)*20:0)+'%';
    $('next-supply').textContent=game.mode==='live'?`${remaining} work units to the next supply drop`:'Supply drops require the real wheel in live mode.';
    $('shield').disabled=game.done||game.paused||game.charge<3||game.shield>0;
    $('shield-label').textContent=game.shield>0?'Shield active!':'Seed shield';$('charge').textContent=`${game.charge} / 3 seeds · SPACE`;
    const waiting=game.waiting();$('wait').hidden=game.done||!waiting;$('wait').textContent=waiting;
    $('habitat').textContent=`0${game.biome+1} / ${names[game.biome]}`;
  }
  function feedDisplay(){
    const valid=E.isLive(measurement),moving=valid&&measurement.rpmMilli>0&&measurement.coreStatus!=='IDLE';
    $('start').disabled=!moving;$('start').textContent=moving?'Start live expedition ↗':valid?'Wheel resting · try practice':'Live unavailable · try practice';
    $('feed-pill').textContent=moving?'LIVE HARDWARE':valid?'RESTING':'UNAVAILABLE';$('feed-pill').classList.toggle('live',moving);
    $('rpm').textContent=valid?(measurement.rpmMilli/1000).toFixed(1):'—';
    $('provenance').textContent=measurement?.provenance??'—';
    $('observed').textContent=measurement?new Date(measurement.observedMs).toLocaleTimeString('en-GB',{timeZone:'Asia/Jakarta',hour12:false})+' WIB':'—';
    $('feed-detail').textContent=moving?'A real little hamster is turning the wheel right now.':valid?'Even tiny adventurers need a rest. Practice is ready whenever you are.':feedError||'Waiting for a fresh, validated hardware reading. Practice is available.';
    $('wheel').style.animationPlayState=moving?'running':'paused';
    $('wheel').style.animationDuration=valid?Math.max(.6,60/Math.max(1,measurement.rpmMilli/1000))+'s':'4s';
  }
  async function feed(){
    if(fetching||Date.now()<nextFeed)return;fetching=true;nextFeed=Date.now()+5000;
    const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),8000);
    try{
      const headers={Accept:'application/json'};if(etag)headers['If-None-Match']=etag;
      const r=await fetch('https://api.squeekchain.com/v1/status',{signal:ctrl.signal,cache:'no-cache',headers});
      if(r.status!==304&&!r.ok){
        if(r.status===429||r.status===503){
          const value=r.headers.get('Retry-After'),seconds=value===null?NaN:Number(value);
          if(Number.isFinite(seconds)&&seconds>=0)nextFeed=Math.max(nextFeed,Date.now()+seconds*1000);
        }
        throw Error('Wheel endpoint returned HTTP '+r.status);
      }
      const payload=r.status===304?lastPayload:await r.json();
      const next=E.parseStatus(payload);
      if(next.observedMs<trustedObservedMs)throw Error('Out-of-order wheel reading; waiting for the latest sample.');
      if(E.isLive(next))trustedObservedMs=next.observedMs;
      if(r.status!==304){lastPayload=payload;etag=r.headers.get('ETag')||'';}
      measurement=next;feedError='';feedFailures=0;
      if(game&&!game.done){game.apply(next);if(game.done)finish();}
    }catch(e){
      nextFeed=Math.max(nextFeed,Date.now()+Math.min(60000,5000*2**Math.min(4,feedFailures++)));
      measurement=null;feedError=e.name==='AbortError'?'Wheel request timed out. Practice is still ready.':'No trusted live feed. Practice is still ready.';
      if(game?.mode==='live'&&!game.done)game.measurement=null;
    }finally{clearTimeout(timer);fetching=false;feedDisplay();update();}
  }
  function ellipse(x,y,rx,ry,color,rotation=0){ctx.fillStyle=color;ctx.beginPath();ctx.ellipse(x,y,rx,ry,rotation,0,Math.PI*2);ctx.fill();}
  function path(points,color){ctx.fillStyle=color;ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();}
  function laneX(lane,y){return w/2+(lane-1)*w*(.09+.2*y);}
  function hamster(x,y,size,bounce){
    const r=size;
    ellipse(x,y+r*.7,r*1.13,r*.25,'#294b3c33');
    ellipse(x-r*.48,y+r*.5+Math.sin(bounce)*r*.07,r*.25,r*.17,'#855937');ellipse(x+r*.48,y+r*.5-Math.sin(bounce)*r*.07,r*.25,r*.17,'#855937');
    ellipse(x,y-r*.05,r*.83,r*.86,'#bd8045');
    for(const d of [-1,1]){ellipse(x+d*r*.58,y-r*.62,r*.29,r*.32,'#c9874c');ellipse(x+d*r*.58,y-r*.63,r*.17,r*.20,'#e7aa94');}
    ellipse(x,y-r*.04,r*.74,r*.69,'#d99d5b');ellipse(x,y+r*.23,r*.59,r*.45,'#ffdfae');
    ellipse(x-r*.35,y+r*.05,r*.15,r*.09,'#e7a388');ellipse(x+r*.35,y+r*.05,r*.15,r*.09,'#e7a388');
    for(const d of [-1,1]){ellipse(x+d*r*.25,y-r*.14,r*.065,r*.085,'#273a31');ellipse(x+d*r*.23,y-r*.17,r*.021,r*.026,'#fff8e7');}
    ellipse(x,y+r*.04,r*.08,r*.055,'#845248');
    ctx.strokeStyle='#845248';ctx.lineWidth=Math.max(1,r*.033);ctx.beginPath();ctx.arc(x-r*.06,y+r*.09,r*.07,0,Math.PI);ctx.arc(x+r*.06,y+r*.09,r*.07,0,Math.PI);ctx.stroke();
    path([[x-r*.66,y+r*.35],[x+r*.66,y+r*.35],[x+r*.57,y+r*.49],[x-r*.57,y+r*.49]],'#bb583d');
    path([[x+r*.48,y+r*.39],[x+r*1.05,y+r*.48],[x+r*.84,y+r*.65]],'#c36146');
  }
  function draw(t,dt){
    const biome=game?.biome??0,scroll=game?.scrolled??0;
    const themes=[['#dbe9ce','#96ba8c','#b4c99c','#e0d5a7','#b6a26f'],['#efd9b7','#c79266','#dfb37c','#e5c49c','#c39360'],['#233f4a','#375a59','#42695a','#7c9b87','#516f5e']];
    const [sky,hill,grass,road,edge]=themes[biome];
    const gradient=ctx.createLinearGradient(0,0,0,h);gradient.addColorStop(0,sky);gradient.addColorStop(.6,grass);gradient.addColorStop(1,grass);ctx.fillStyle=gradient;ctx.fillRect(0,0,w,h);
    ellipse(w*.79,h*.17,w*.045,w*.045,biome===2?'#f3e8b7':'#fff1b6');
    if(biome===2)for(let i=0;i<22;i++)ellipse((Math.sin(i*91)+1)*w/2,(Math.cos(i*73)+1)*h*.17,1,1,'#dfdfb9');
    path([[0,h*.32],[w*.1,h*.20],[w*.32,h*.34],[w*.55,h*.22],[w*.76,h*.32],[w,h*.19],[w,h],[0,h]],hill);
    path([[0,h*.42],[w*.18,h*.33],[w*.43,h*.40],[w*.67,h*.31],[w,h*.42],[w,h],[0,h]],grass);
    path([[w*.43,h*.34],[w*.57,h*.34],[w*.94,h],[w*.06,h]],edge);
    path([[w*.44,h*.34],[w*.56,h*.34],[w*.91,h],[w*.09,h]],road);
    for(let i=0;i<20;i++){
      const p=((i/20+scroll*.17)%1),y=h*(.32+.73*p),spread=w*(.11+.4*p);
      const side=i%2?-1:1,x=w/2+side*spread;
      ellipse(x,y,3+7*p,2+3*p,biome===2?'#68917c':'#8fa96c');
      if(i%3===0){ellipse(x+6,y-5,2+p*2,2+p*2,biome===2?'#c4d7a4':'#f5e5a8');}
    }
    ctx.strokeStyle=biome===2?'#a6c0a34d':'#b396615c';ctx.lineWidth=2;
    for(let i=0;i<10;i++){
      const py=((i/10+scroll*.15)%1),y=h*(.35+.72*py),spread=w*(.022+.09*py);
      for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(w/2+side*spread,y);ctx.lineTo(w/2+side*(spread+2),y+h*.024*(.3+py));ctx.stroke();}
    }
    const objects=game?.objects??[{kind:'seed',lane:0,y:.24},{kind:'seed',lane:0,y:.4},{kind:'rock',lane:2,y:.4},{kind:'supply',lane:1,y:.16}];
    for(const obj of [...objects].sort((a,b)=>a.y-b.y)){
      if(obj.y<0)continue;
      const y=h*(.34+.67*obj.y),x=laneX(obj.lane,obj.y),s=Math.max(7,w/35)*(.4+.85*obj.y);
      ellipse(x,y+s*.65,s*.85,s*.25,'#2d42372a');
      if(obj.kind==='seed'){
        ellipse(x,y,s*.37,s*.67,'#af7e32',.4);ellipse(x-s*.06,y-s*.07,s*.29,s*.56,'#f5c951',.4);
        ctx.strokeStyle='#ffeaa1';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x-s*.15,y+s*.25);ctx.lineTo(x+s*.15,y-s*.3);ctx.stroke();
      }else if(obj.kind==='rock'){
        path([[x-s,y+s*.5],[x-s*.8,y-s*.6],[x+s*.15,y-s],[x+s,y-s*.1],[x+s*.7,y+s*.6]],'#737d72');
        path([[x-s*.8,y-s*.6],[x+s*.15,y-s],[x+s*.3,y-s*.2],[x-s*.2,y+s*.1]],'#9ba192');
      }else{
        ctx.fillStyle='#b77e45';ctx.fillRect(x-s*.7,y-s*.65,s*1.4,s*1.3);ctx.fillStyle='#e4b16b';ctx.fillRect(x-s*.63,y-s*.6,s*1.26,s*.2);
        ctx.strokeStyle='#f7d998';ctx.lineWidth=s*.13;ctx.strokeRect(x-s*.5,y-s*.42,s,s*.85);ctx.beginPath();ctx.moveTo(x-s*.5,y-s*.42);ctx.lineTo(x+s*.5,y+s*.43);ctx.stroke();
      }
    }
    const target=game?.lane??1;playerLane+=(target-playerLane)*Math.min(1,dt*16);
    const px=laneX(playerLane,.82),py=h*(.34+.67*.82),r=Math.min(33,w/12);
    const moving=game&&!game.done&&!game.waiting();
    const bounce=reduced?0:t*.011;
    if(game?.shield>0){ctx.strokeStyle='#b9e7d2';ctx.lineWidth=3;ctx.fillStyle='#b9e7d233';ctx.beginPath();ctx.arc(px,py,r*1.35,0,Math.PI*2);ctx.fill();ctx.stroke();}
    ctx.globalAlpha=game?.invincible>0&&Math.floor(t/90)%2?.4:1;
    hamster(px,py+(moving&&!reduced?Math.sin(bounce)*2:0),r,bounce);ctx.globalAlpha=1;
  }
  function resize(){
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(2,devicePixelRatio||1);w=rect.width;h=rect.height;
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function frame(t){
    const dt=lastFrame?Math.min(.05,(t-lastFrame)/1000):0;lastFrame=t;
    if(game&&!game.done){game.tick(dt);for(const event of game.events.splice(0)){if(event.kind!=='seed')toast(event.text);beep(event.kind);}update();if(game.done)finish();}
    draw(t,dt);$('toast').classList.toggle('show',t<toastUntil);requestAnimationFrame(frame);
  }
  $('start').addEventListener('click',()=>start('live'));$('practice').addEventListener('click',()=>start('practice'));
  $('pause').addEventListener('click',pause);$('restart').addEventListener('click',()=>start(game?.mode??'practice'));
  $('left').addEventListener('click',()=>game?.move(-1));$('right').addEventListener('click',()=>game?.move(1));
  $('shield').addEventListener('click',()=>{if(game?.activateShield())beep('shield');});
  $('sound').addEventListener('click',()=>{sound=!sound;$('sound').textContent=sound?'Sound on':'Sound off';$('sound').setAttribute('aria-pressed',String(sound));$('sound').setAttribute('aria-label',sound?'Disable game sound':'Enable game sound');beep('seed');});
  document.addEventListener('keydown',e=>{
    if(!game||game.done||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.altKey||e.ctrlKey||e.metaKey)return;
    if(['ArrowLeft','a','A','ArrowRight','d','D'].includes(e.key)){e.preventDefault();game.move(['ArrowLeft','a','A'].includes(e.key)?-1:1);}
    else if(e.code==='Space'&&e.target.tagName!=='BUTTON'){e.preventDefault();if(game.activateShield())beep('shield');}
    else if(e.key.toLowerCase()==='p'||e.key==='Escape'){e.preventDefault();pause();}
  });
  let touchX=null;
  canvas.addEventListener('pointerdown',e=>{touchX=e.clientX;canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointerup',e=>{if(touchX!==null&&Math.abs(e.clientX-touchX)>20)game?.move(e.clientX>touchX?1:-1);touchX=null;});
  canvas.addEventListener('pointercancel',()=>{touchX=null;});
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden&&game&&!game.done&&!game.paused)pause();
    if(!document.hidden){lastFrame=0;void feed();}
  });
  new ResizeObserver(resize).observe(canvas);journal();resize();void feed();
  setInterval(()=>{feedDisplay();if(!document.hidden)void feed();},1000);
  requestAnimationFrame(frame);
})();
