'use strict';
// Isolated browser simulation: no physical TV, user media, or Home Assistant writes.
const assert=require('assert'),fs=require('fs'),vm=require('vm');
const nodes={},intervals=[],future=[],listeners={};
let playCount=0,now=0,loading=0;
function node(id){
 return nodes[id]||(nodes[id]={
  id,className:'',style:{},children:[],innerHTML:'',textContent:'',disabled:false,
  focus(){document.activeElement=this;if(this.onfocus)this.onfocus();},
  appendChild(n){this.children.push(n);},removeAttribute(){},
  pause(){},load(){loading++;},play(){playCount++;},
  get currentTime(){return this._time||0;},set currentTime(v){this._time=v;}
 });
}
const document={activeElement:null,hidden:false,webkitHidden:false,
 getElementById:node,createElement:t=>node('created-'+Math.random()),
 addEventListener(name,fn){listeners[name]=fn;}};
const window={innerWidth:1280,innerHeight:720,addEventListener(){},PalmSystem:null};
const album={items:[
 {id:'a'.repeat(24),type:'video',rotation:0},
 {id:'b'.repeat(24),type:'video',rotation:270},
 {id:'c'.repeat(24),type:'photo',rotation:0}
],hiddenCount:0};
class XHR {
 open(method,url){this.url=url;this.method=method;}
 send(){
  assert.equal(this.method,'GET');
  if(this.url.endsWith('/api/album')){
   this.status=200;this.responseText=JSON.stringify(album);this.readyState=4;this.onreadystatechange();
  }
 }
}
class Image {
 set src(val){this._src=val;if(this.onload)this.onload();}
}
class Clock extends Date{constructor(...a){super(...(a.length?a:[now]));}static now(){return now;}}
const context={document,window,Date:Clock,XMLHttpRequest:XHR,
 localStorage:{getItem:()=>JSON.stringify({random:false}),setItem(){}},
 setInterval(fn,ms){intervals.push({fn,ms});return intervals.length;},
 setTimeout(fn,ms){future.push({fn,ms});return future.length;},
 clearTimeout(){},Image,Math,JSON,isFinite,Number,console};
vm.runInNewContext(fs.readFileSync('apps/family-frame/player.js','utf8'),context);
const video=node('video'),tick=intervals.find(x=>x.ms===1000).fn;
assert.equal(playCount,1);
assert.equal(nodes.count.textContent,'1 / 3 · Видео');
assert.equal(video.style.transform,'rotate(90deg)', 'all video has an additional 90° clockwise rotation');
assert(nodes['menu-note'].textContent.includes('90°'));

// A one-minute loss of network buffering must not skip, restart, or shorten a video.
video.currentTime=1;now=2000;tick();now=120000;tick();
assert.equal(nodes.count.textContent,'1 / 3 · Видео');
assert.equal(playCount,1,'must not restart the source on buffering');
assert.equal(nodes.notice.textContent,'Буферизация видео — ожидаем загрузку…');
assert(!future.some(x=>x.ms===30000),'no playback timeout can skip video');
video.currentTime=11;now=125000;tick();assert.equal(nodes.count.textContent,'1 / 3 · Видео');

// Native end event is the only automatic normal transition for video.
video.onended();assert.equal(nodes.count.textContent,'2 / 3 · Видео');
assert.equal(video.style.transform,'rotate(0deg)', 'saved per-video adjustment adds to global 90° rotation');
assert.equal(playCount,2);
now=500000;tick();assert.equal(nodes.count.textContent,'2 / 3 · Видео');
video.onended();assert.equal(nodes.count.textContent,'3 / 3 · 10 сек.');
assert.equal(nodes.p1.style.transform,'rotate(0deg)', 'photo rotation remains unchanged');
assert(future.some(x=>x.ms===10000),'photo slideshow timer remains intact');
console.log('FRAME_FULL_VIDEO_AND_ROTATION_TEST_OK');
