import http from 'node:http';
import {execFile,spawn} from 'node:child_process';
import {promisify} from 'node:util';
const runFile=promisify(execFile);
import {readFileSync} from 'node:fs';
import {timingSafeEqual} from 'node:crypto';
import {connectMcp,closeMcp} from '__RS_MCP_CLIENT_PATH__';
const host='__RS_BRIDGE_HOST__', port=8786;
const allowed=new Set([host,'__RS_TV_HOST__','127.0.0.1']);
const keys={
 outdoor:'__RS_OUTDOOR_ENTITY__',
 indoor:'__RS_INDOOR_ENTITY__',
 sauna:'__RS_SAUNA_ENTITY__',
 price:'__RS_PRICE_ENTITY__'
};
let cache=null, lastAttempt=0, inflight=null;
const sceneKey=readFileSync(new URL('./scene-key',import.meta.url),'utf8').trim();
const scenes=Object.freeze({day:'__RS_DAY_ENTITY__',movie:'__RS_MOVIE_ENTITY__',morning:'__RS_MORNING_ENTITY__',off:'__RS_OFF_ENTITY__',coffee_power:'__RS_COFFEE_POWER_ENTITY__'});
let queue=Promise.resolve(), sceneBusy=false, lastScene=0;
function serial(fn){const next=queue.then(fn,fn);queue=next.catch(()=>{});return next;}
function keyOK(value){return typeof value==='string'&&/^[0-9a-f]{64}$/.test(value)&&value.length===sceneKey.length&&timingSafeEqual(Buffer.from(value),Buffer.from(sceneKey));}
function reply(res,code,data){res.writeHead(code,{'Content-Type':'application/json; charset=utf-8','Access-Control-Allow-Origin':'*','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(JSON.stringify(data));}
async function activateScene(id){
 const c=await connectMcp();
 try{
  const r=await c.callTool({name:'ha_call_service',arguments:{domain:id==='coffee_power'?'switch':'scene',service:'turn_on',entity_id:scenes[id],wait:false}},undefined,{timeout:12000});
  let d=r.structuredContent;if(!d&&r.content?.[0]?.text){try{d=JSON.parse(r.content[0].text);}catch{}}
  return !r.isError&&d?.success===true;
 }finally{await closeMcp().catch(()=>{});}
}
async function sceneRequest(req,res){
 if(req.socket.remoteAddress!=='__RS_TV_HOST__'){return reply(res,403,{ok:false});}
 if(req.method!=='POST'){return reply(res,405,{ok:false});}
 if(!String(req.headers['content-type']||'').startsWith('text/plain'))return reply(res,415,{ok:false});
 let raw='';
 try{for await(const chunk of req){raw+=chunk.toString();if(raw.length>512){return reply(res,413,{ok:false});}}}catch{return reply(res,400,{ok:false});}
 let b;try{b=JSON.parse(raw);}catch{return reply(res,400,{ok:false});}
 if(!b||!keyOK(b.key)||!Object.hasOwn(scenes,b.scene))return reply(res,403,{ok:false});
 if(sceneBusy||Date.now()-lastScene<1500)return reply(res,429,{ok:false});
 sceneBusy=true;lastScene=Date.now();
 try{const ok=await serial(()=>activateScene(b.scene));return reply(res,ok?200:502,{ok});}
 catch{return reply(res,502,{ok:false});}finally{sceneBusy=false;}
}
function extract(r){
 let d=r.structuredContent;
 if(!d&&r.content?.[0]?.text) {try{d=JSON.parse(r.content[0].text);}catch{}}
 return d?.data;
}
async function collect(){
 let values={outdoor:null,indoor:null,sauna:null,price:null}, priceDay=null;
 try {
  const c=await connectMcp();
  for(const [key,entity_id] of Object.entries(keys)){
   try{
    const result=await c.callTool({name:'ha_get_state',arguments:{entity_id}},undefined,{timeout:6000});
    const d=extract(result), unit=key==='outdoor'?d?.attributes?.temperature_unit:d?.attributes?.unit_of_measurement;
    const raw=key==='outdoor'?d?.attributes?.temperature:d?.state; const n=Number(raw);
    if(key==='price'&&unit==='c/kWh'&&Array.isArray(d?.attributes?.raw_today)){
     const rows=d.attributes.raw_today.map(x=>({start:Date.parse(x.start),end:Date.parse(x.end),value:x.value})).filter(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&x.end>x.start&&typeof x.value==='number'&&Number.isFinite(x.value));
     const now=Date.now(),current=rows.findIndex(x=>x.start<=now&&now<x.end);
     if(rows.length>=23&&rows.length<=100&&current>=0)priceDay={rows,current,min:Math.min(...rows.map(x=>x.value)),max:Math.max(...rows.map(x=>x.value))};
    }
    if(raw!==''&&raw!=null&&Number.isFinite(n)&& (key==='price'?unit==='c/kWh':unit==='°C')){
     const date=Date.parse(d.last_updated||''); const age=Date.now()-date;
     const max=key==='price'?35*60000:key==='sauna'?30*60000:120*60000;
     if(Number.isFinite(age)&&age>=-60000&&age<max) values[key]=Math.round(n*10)/10;
    }
   }catch{}
  }
 }catch(e){console.warn('HA connection unavailable');}
 finally{await closeMcp().catch(()=>{});}
 cache={updated:Date.now(),values,priceDay,available:Object.values(values).some(v=>v!==null)};
 return cache;
}
async function snapshot(){
 if(cache&&Date.now()-cache.updated<90000)return cache;
 if(!inflight){lastAttempt=Date.now();inflight=serial(collect).finally(()=>{inflight=null;});}
 return inflight;
}
let cameraUrl=null, urlAt=0, jpeg=null, jpegAt=0, capturePending=null, captureFailed=0;
async function cameraSource(){
 if(cameraUrl&&Date.now()-urlAt<3600000)return cameraUrl;
 return serial(async()=>{
  if(cameraUrl&&Date.now()-urlAt<3600000)return cameraUrl;
  try{
   const c=await connectMcp();
   const r=await c.callTool({name:'ha_config_get_dashboard',arguments:{heading:'__RS_CAMERA_HEADING__',include_config:true}},undefined,{timeout:7000});
   const d=r.structuredContent||JSON.parse(r.content[0].text);
   const hit=d.matches?.find(x=>x.url_path==='__RS_DASHBOARD_PATH__'&&x.card_type==='custom:webrtc-camera');
   const u=new URL(hit?.card_config?.url||'');
   if(u.protocol!=='rtsp:'||u.hostname!=='__RS_CAMERA_HOST__')throw Error('source mismatch');
   cameraUrl=u.href;urlAt=Date.now();return cameraUrl;
  }finally{await closeMcp().catch(()=>{});}
 });
}
async function capture(){
 if(jpeg&&Date.now()-jpegAt<10000)return jpeg;
 if(Date.now()-captureFailed<12000)throw Error('camera retry cooldown');
 if(!capturePending)capturePending=(async()=>{
  try{
   const u=await cameraSource();
   const r=await runFile('/usr/bin/ffmpeg',['-nostdin','-hide_banner','-loglevel','error','-rtsp_transport','tcp','-timeout','5000000','-i',u,'-an','-frames:v','1','-vf','scale=640:-2','-q:v','5','-f','image2pipe','-vcodec','mjpeg','pipe:1'],{encoding:'buffer',timeout:13000,maxBuffer:1024*1024});
   const b=r.stdout;if(b.length<100||b[0]!==255||b[1]!==216)throw Error('not jpeg');
   jpeg=b;jpegAt=Date.now();return jpeg;
  }catch{captureFailed=Date.now();cameraUrl=null;throw Error('camera unavailable');}
 })().finally(()=>{capturePending=null;});
 return capturePending;
}

// Fullscreen only: a single bounded MJPEG producer, no recording.
let liveProcess=null,liveStarting=null,liveLease=0,liveFrame=null,liveAt=0,liveRetry=0,liveWaiters=0;
function stopLive(){
 const p=liveProcess;liveRetry=Date.now()+2500;liveProcess=null;liveFrame=null;liveAt=0;
 if(p){p.kill('SIGTERM');const t=setTimeout(()=>{if(p.exitCode===null&&p.signalCode===null)p.kill('SIGKILL');},2000);t.unref();}
}
const liveTimer=setInterval(()=>{
 if(liveProcess&&(Date.now()-liveLease>10000||Date.now()-liveAt>16000)) stopLive();
},1000);liveTimer.unref();
async function startLive(){
 if(liveProcess||liveStarting||Date.now()<liveRetry)return;
 liveStarting=(async()=>{
  try{
   const u=await cameraSource();
   if(Date.now()-liveLease>10000)return;
   let buf=Buffer.alloc(0);
   const p=spawn('/usr/bin/ffmpeg',['-nostdin','-hide_banner','-loglevel','error','-threads','2','-filter_threads','1','-rtsp_transport','tcp','-timeout','5000000','-i',u,'-an','-sn','-dn','-vf','fps=3,scale=640:-2','-threads','1','-q:v','6','-f','image2pipe','-vcodec','mjpeg','pipe:1'],{stdio:['ignore','pipe','ignore']});
   liveProcess=p;liveAt=Date.now();
   const end=()=>{if(liveProcess===p){liveProcess=null;liveFrame=null;liveAt=0;liveRetry=Date.now()+4000;}};
   p.on('error',end);p.on('close',end);
   p.stdout.on('error',()=>{if(liveProcess===p)stopLive();});
   p.stdout.on('data',chunk=>{
    if(liveProcess!==p)return;
    buf=Buffer.concat([buf,chunk]);
    if(buf.length>2*1024*1024){buf=Buffer.alloc(0);return;}
    while(buf.length>2){
     const start=buf.indexOf(Buffer.from([255,216]));
     if(start<0){buf=buf.subarray(buf.length-1);return;}
     if(start>0)buf=buf.subarray(start);
     const end=buf.indexOf(Buffer.from([255,217]),2);
     if(end<0)return;
     const frame=buf.subarray(0,end+2);buf=buf.subarray(end+2);
     if(frame.length>100&&frame.length<1024*1024){liveFrame=Buffer.from(frame);liveAt=Date.now();}
    }
   });
  }catch{liveRetry=Date.now()+4000;}
 })().finally(()=>{liveStarting=null;});
}
async function liveRequest(req,res){
 if(req.method!=='GET'){res.writeHead(405);return res.end();}
 if(liveWaiters>=2){res.writeHead(429);return res.end();}
 liveWaiters++;
 try{
  liveLease=Date.now();await startLive();
  const deadline=Date.now()+8500;
  while(!res.destroyed&&Date.now()<deadline){
   if(liveFrame&&Date.now()-liveAt<1800){
    const b=liveFrame;
    res.writeHead(200,{'Content-Type':'image/jpeg','Content-Length':b.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});return res.end(b);
   }
   if(!liveProcess&&!liveStarting)await startLive();
   await new Promise(r=>setTimeout(r,150));
  }
  if(!res.destroyed){res.writeHead(503,{'Cache-Control':'no-store'});res.end();}
 }finally{liveWaiters--;}
}
async function cameraRequest(req,res){
 if(req.method!=='GET'){res.writeHead(405);return res.end();}
 try{const b=liveFrame&&Date.now()-liveAt<1800?liveFrame:await capture();res.writeHead(200,{'Content-Type':'image/jpeg','Content-Length':b.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(b);}
 catch{res.writeHead(503,{'Cache-Control':'no-store'});res.end();}
}
const server=http.createServer(async(req,res)=>{
 if(!allowed.has(req.socket.remoteAddress)){res.writeHead(403);return res.end();}
 if(req.url==='/scene')return sceneRequest(req,res);
 if(req.url.split('?')[0]==='/live.jpg')return liveRequest(req,res);
 if(req.url.split('?')[0]==='/camera.jpg')return cameraRequest(req,res);
 if(req.method!=='GET'||!['/status.json','/status.js'].includes(req.url)){res.writeHead(404);return res.end();}
 try{
  const data=JSON.stringify(await snapshot()); const js=req.url==='/status.js';
  res.writeHead(200,{'Content-Type':js?'application/javascript; charset=utf-8':'application/json; charset=utf-8','Cache-Control':'no-store','Access-Control-Allow-Origin':'*','X-Content-Type-Options':'nosniff'});
  res.end(js?'window.rsHaUpdate('+data+');':data);
 }catch{res.writeHead(503);res.end();}
});
server.listen(port,host,()=>console.log('RS TV HA bridge listening (5 allowlisted actions)'));
