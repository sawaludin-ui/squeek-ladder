// Node.js / Squeek Sprint / deterministic allowlisted source + deployment synchronization.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const authored=['index.html','sprint.css','sprint.js','favicon.svg','README.md','DEPLOY.md'];
const runtime=['sprint-engine.js','status-validator.js'];
function copy(from,to){
  const data=fs.readFileSync(from);
  if(fs.existsSync(to)&&fs.readFileSync(to).equals(data))return;
  fs.mkdirSync(path.dirname(to),{recursive:true});
  fs.writeFileSync(to+'.build-tmp',data);fs.renameSync(to+'.build-tmp',to);
}
for(const file of authored)copy(path.join(root,'src',file),path.join(root,file));
for(const file of [...authored,...runtime])copy(path.join(root,file),path.join(root,'site',file));
for(const file of [...authored,...runtime]){
  if(!fs.readFileSync(path.join(root,file)).equals(fs.readFileSync(path.join(root,'site',file))))throw Error('Deployment drift: '+file);
}
console.log('Synced and verified '+(authored.length+runtime.length)+' allowlisted source files to site/');
