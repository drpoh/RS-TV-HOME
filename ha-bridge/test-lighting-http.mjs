import {mkdtempSync,readFileSync,writeFileSync,copyFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import net from 'node:net';
const port=await new Promise((resolve,reject)=>{const s=net.createServer();s.once('error',reject);s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});});
const dir=mkdtempSync(join(tmpdir(),'rs-light-test-'));
let p;
try{
 const source=readFileSync(new URL('./server.mjs',import.meta.url),'utf8').replaceAll('__RS_BRIDGE_HOST__','127.0.0.1').replaceAll('__RS_TV_HOST__','127.0.0.1').replace('__RS_MCP_CLIENT_PATH__','./fake.mjs').replace('port=8786','port='+port);
 writeFileSync(join(dir,'server.mjs'),source);
 copyFileSync(new URL('./lighting.mjs',import.meta.url),join(dir,'lighting.mjs'));
 const key='a'.repeat(64);writeFileSync(join(dir,'scene-key'),key);
 writeFileSync(join(dir,'lighting.json'),JSON.stringify([{id:'room',label:'Room',lights:[{id:'lamp',label:'Lamp',entity:'light.example'}]}]));
 writeFileSync(join(dir,'fake.mjs'),`let state='off';export async function connectMcp(){return {callTool:async({name,arguments:a})=>{if(name==='ha_get_state')return {structuredContent:{data:{states:{'light.example':{state}}}}};if(name==='ha_call_service'){if(a.domain!=='light'||a.entity_id!=='light.example')throw Error('bad target');state=a.service==='turn_on'?'on':'off';return {structuredContent:{success:true}};}throw Error('unexpected call');}}}export async function closeMcp(){}`);
 p=spawn(process.execPath,[join(dir,'server.mjs')],{stdio:['ignore','pipe','pipe']});
 await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('timeout')),5000);p.once('error',reject);p.once('exit',()=>reject(Error('exit')));p.stdout.once('data',()=>{clearTimeout(timer);resolve();});});
 const base='http://127.0.0.1:'+port;
 let r=await fetch(base+'/lights');assert.equal(r.status,200);assert.equal((await r.json()).rooms[0].lights[0].state,'off');
 async function post(b){return fetch(base+'/light',{method:'POST',headers:{'Content-Type':'text/plain'},body:JSON.stringify(b)});}
 assert.equal((await post({id:'lamp',state:'on',key:'bad'})).status,403);
 assert.equal((await post({id:'unknown',state:'on',key})).status,403);
 assert.equal((await post({id:'lamp',state:'toggle',key})).status,403);
 assert.equal((await post({id:'lamp',state:'on',key})).status,200);
 r=await fetch(base+'/lights');assert.equal((await r.json()).rooms[0].lights[0].state,'on');
 console.log('LIGHTING_HTTP_MOCK_OK');
}finally{if(p)p.kill();rmSync(dir,{recursive:true,force:true});}
