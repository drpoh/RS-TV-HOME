'use strict';
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const nodes={},intervals=[],actions=[];
let playCount=0,loadCount=0,now=0;
function node(id){
 return nodes[id]||(nodes[id]={
  id,className:'',style:{},children:[],innerHTML:'',
  textContent:'',disabled:false,onclick:null,onfocus:null,
  focus(){document.activeElement=this;if(this.onfocus)this.onfocus();},
  appendChild(n){this.children.push(n);},removeAttribute(){},
  pause(){},load(){loadCount++;},play(){playCount++;},
  get currentTime(){return this._time||0;},set currentTime(v){this._time=v;}
 });
}
const document={activeElement:null,hidden:false,webkitHidden:false,
 getElementById:node,createElement:t=>node('created-'+Math.random()),
 addEventListener(){}};
const window={innerWidth:1280,innerHeight:720,addEventListener(){},PalmSystem:null};
const album={items:[{id:'a'.repeat(24),type:'video',rotation:0}],hiddenCount:0};
class XHR {
 open(method,url){this.url=url;this.method=method;}
 send(){
  assert.equal(this.method,'GET');
  if(this.url.endsWith('/api/album')){
   this.status=200;this.responseText=JSON.stringify(album);this.readyState=4;this.onreadystatechange();
  }
 }
}
const future=[];
class Clock extends Date{constructor(...a){super(...(a.length?a:[now]));}static now(){return now;}}
const context={document,window,Date:Clock,XMLHttpRequest:XHR,localStorage:{getItem:()=>null,setItem(){}},
 setInterval(fn,ms){intervals.push({fn,ms});return intervals.length;},setTimeout(fn){future.push(fn);return future.length;},clearTimeout(){},Image:function(){},Math,JSON,isFinite,Number,console};
vm.runInNewContext(fs.readFileSync('apps/family-frame/player.js','utf8'),context);
const video=node('video');const tick=intervals.find(x=>x.ms===1000).fn;
assert.equal(playCount,1);
video.currentTime=2;now=2000;tick();
now=9000;tick();assert.equal(playCount,1);
now=11000;tick();assert.equal(playCount,2,'frozen video must be retried');
assert.equal(nodes.notice.textContent,'Восстанавливаем воспроизведение видео…');
now=20000;tick();assert.equal(nodes.message.textContent,'Не удалось воспроизвести файлы. Откройте меню.');
assert.equal(playCount,2,'repeat stalls must not loop infinitely');
console.log('FRAME_PROGRESS_WATCHDOG_TEST_OK');
