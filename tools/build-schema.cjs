// Node.js / Squeek Sprint / compile the pinned official draft-2020-12 status schema.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const Ajv=require('ajv/dist/2020');
const addFormats=require('ajv-formats');
const standalone=require('ajv/dist/standalone').default;
const esbuild=require('esbuild');
const root=path.resolve(__dirname,'..');
const ajv=new Ajv({code:{source:true},allErrors:true,strict:true});
addFormats(ajv,['date','date-time','uuid']);
// The engine additionally range-checks the consumed uint64 with BigInt.
for(const bits of [64,96])ajv.addFormat(`uint${bits}-decimal`,/^(0|[1-9][0-9]*)$/);
const schema=JSON.parse(fs.readFileSync(path.join(root,'docs/status.schema.json'),'utf8'));
const validate=ajv.compile(schema);
esbuild.buildSync({stdin:{contents:standalone(ajv,validate),resolveDir:root,sourcefile:'compiled-status.cjs'},bundle:true,platform:'browser',format:'iife',globalName:'SqueekStatusSchema',minify:true,legalComments:'inline',outfile:path.join(root,'status-validator.js'),footer:{js:'if(typeof module!=="undefined"&&module.exports)module.exports=SqueekStatusSchema;'}});
console.log('Built status-validator.js from docs/status.schema.json');
