(function(){
'use strict';
var base='http://__RS_BRIDGE_HOST__:8786',prices=null,cameraBusy=false,lastCamera=0,lastPrice=0;
window.rsPanelOpen='';
var liveActive=false,liveTimer=null,liveImage=null,liveEpoch=0,liveDeadline=0;
function hidden(){return document.hidden===true||document.webkitHidden===true;}
function el(id){return document.getElementById(id);}
function fmt(v){return v.toFixed(1).replace('.',',');}
function clock(ms){var d=new Date(ms),h=d.getHours(),m=d.getMinutes();return (h<10?'0':'')+h+':'+(m<10?'0':'')+m;}
function currentDay(d){if(!d||!d.rows||!d.rows.length)return false;var now=Date.now();return d.rows[0].start<=now&&now<d.rows[d.rows.length-1].end;}
function draw(id,big){
 var cv=el(id),c=cv.getContext('2d'),w=cv.width,h=cv.height;
 c.clearRect(0,0,w,h);
 if(!currentDay(prices)){c.fillStyle='#c9daed';c.font=big?'26px Arial':'15px Arial';c.textAlign='left';c.textBaseline='alphabetic';c.fillText('Нет данных Nord Pool',12,big?55:40);if(big)el('overlay-info').textContent='Нет актуальных цен';return;}
 var r=prices.rows,left=big?65:30,top=big?30:7,bottom=big?50:24,pw=w-left-10,ph=h-top-bottom;
 var lo=Math.min(0,prices.min),hi=Math.max(1,prices.max),span=hi-lo,zero=top+hi/span*ph;
 c.font=big?'21px Arial':'12px Arial';c.textAlign='right';c.textBaseline='middle';
 for(var i=0;i<=3;i++){var v=lo+span*i/3,y=top+(hi-v)/span*ph;c.strokeStyle='#526980';c.lineWidth=1;c.beginPath();c.moveTo(left,y);c.lineTo(w-8,y);c.stroke();c.fillStyle='#afc5dc';c.fillText(fmt(v),left-5,y);}
 var now=Date.now(),idx=-1,step=pw/r.length,bar=Math.max(1,step-1);
 for(i=0;i<r.length;i++){v=r[i].value;var cur=r[i].start<=now&&now<r[i].end;if(cur)idx=i;
 var f=(v-prices.min)/Math.max(.001,prices.max-prices.min);c.fillStyle=cur?'#f9e6a7':f>.67?'#e47d78':f>.35?'#e6c481':'#7dc5a9';
 var by=top+(hi-v)/span*ph;c.fillRect(left+i*step,Math.min(by,zero),bar,Math.max(1,Math.abs(zero-by)));
 if(cur){c.strokeStyle='#ffffff';c.strokeRect(left+i*step,Math.min(by,zero),bar,Math.max(1,Math.abs(zero-by)));}}
 c.fillStyle='#c4d7ed';c.textAlign='center';c.textBaseline='top';
 for(i=0;i<r.length;i++){var date=new Date(r[i].start);if(date.getMinutes()===0&&date.getHours()%4===0)c.fillText(clock(r[i].start),left+i*step+step/2,h-bottom+5);}
 if(big){var info='Мин. '+fmt(prices.min)+' · Макс. '+fmt(prices.max)+' ¢/кВт·ч';if(idx>=0)info+=' · Сейчас '+fmt(r[idx].value)+' ¢/кВт·ч';el('overlay-info').textContent=info;}
}
window.rsSetPrices=function(d){prices=currentDay(d)?d:null;lastPrice=prices?Date.now():0;el('price-summary').textContent=prices?'мин '+fmt(prices.min)+' / макс '+fmt(prices.max)+' ¢':'—';draw('price-chart',false);if(window.rsPanelOpen==='chart')draw('big-chart',true);};

function stopLive(){
 liveActive=false;liveEpoch++;
 if(liveTimer){clearTimeout(liveTimer);liveTimer=null;}
 if(liveImage){liveImage.onload=null;liveImage.onerror=null;liveImage.removeAttribute('src');liveImage=null;}
 var cv=el('live-camera');cv.getContext('2d').clearRect(0,0,cv.width,cv.height);
 cv.style.display='none';el('big-camera').style.display='block';
}
function liveFallback(message){
 stopLive();
 if(window.rsPanelOpen!=='camera'||hidden())return;
 el('overlay-info').textContent=message+' · режим снимков';
 camera();
}
function liveNext(epoch){
 if(!liveActive||epoch!==liveEpoch)return;
 if(hidden()||window.rsPanelOpen!=='camera'){stopLive();return;}
 if(Date.now()>liveDeadline){liveFallback('Время просмотра истекло · откройте камеру снова');return;}
 var im=new Image();liveImage=im;var done=false;
 function finish(ok){
  if(done||epoch!==liveEpoch)return;
  done=true;clearTimeout(liveTimer);liveTimer=null;im.onload=null;im.onerror=null;liveImage=null;
  if(!ok){im.removeAttribute('src');liveFallback('Прямой эфир недоступен');return;}
  var cv=el('live-camera'),ctx=cv.getContext('2d'),w=im.naturalWidth||im.width,h=im.naturalHeight||im.height;
  if(!w||!h){liveFallback('Нет изображения');return;}
  var scale=Math.min(cv.width/w,cv.height/h),dw=w*scale,dh=h*scale;
  ctx.fillStyle='#0d1627';ctx.fillRect(0,0,cv.width,cv.height);
  try{ctx.drawImage(im,(cv.width-dw)/2,(cv.height-dh)/2,dw,dh);}
  catch(e){liveFallback('Видео не поддерживается');return;}
  cv.style.display='block';el('big-camera').style.display='none';
  el('overlay-info').textContent='Прямой эфир · до 3 кадров/с · без звука';
  liveTimer=setTimeout(function(){liveNext(epoch);},350);
 }
 im.onload=function(){finish(true);};im.onerror=function(){finish(false);};
 liveTimer=setTimeout(function(){finish(false);},15000);
 im.src=base+'/live.jpg?t='+Date.now();
}
function startLive(){
 if(liveActive||hidden()||window.rsPanelOpen!=='camera')return;
 liveActive=true;liveDeadline=Date.now()+600000;
 el('overlay-info').textContent='Подключение прямого эфира…';
 liveNext(++liveEpoch);
}
function camera(){if(el('camera-panel').style.display==='none'&&window.rsPanelOpen!=='camera')return;if(cameraBusy||hidden()||liveActive||window.rsPanelOpen==='chart')return;cameraBusy=true;var img=new Image(),done=false;
 function finish(ok){if(done)return;done=true;clearTimeout(t);img.onload=null;img.onerror=null;cameraBusy=false;if(ok){lastCamera=Date.now();el('camera-preview').src=img.src;if(window.rsPanelOpen==='camera'&&!liveActive)el('big-camera').src=img.src;el('camera-state').textContent='Снимок '+clock(lastCamera);if(window.rsPanelOpen==='camera'&&!liveActive)el('overlay-info').textContent='Снимок '+clock(lastCamera)+' · обновление каждые 15 секунд';}else{img.removeAttribute('src');el('camera-state').textContent='Камера недоступна';if(window.rsPanelOpen==='camera'&&!liveActive)el('overlay-info').textContent='Камера недоступна · повтор подключения';}}
 var t=setTimeout(function(){finish(false);},28000);img.onload=function(){finish(true);};img.onerror=function(){finish(false);};img.src=base+'/camera.jpg?t='+Date.now();
}
window.rsOpenPanel=function(kind){window.rsPanelOpen=kind;el('panel-overlay').style.display='block';el('panel-title').textContent=kind==='camera'?'Камера крыльца':'Nord Pool · сегодня';el('camera-full').style.display=kind==='camera'?'block':'none';el('chart-full').style.display=kind==='chart'?'block':'none';if(kind==='camera'){if(lastCamera&&Date.now()-lastCamera<60000)el('big-camera').src=el('camera-preview').src;startLive();}else draw('big-chart',true);el('close-panel').focus();};
window.rsClosePanel=function(){stopLive();window.rsPanelOpen='';el('panel-overlay').style.display='none';};
function shown(){if(hidden()){stopLive();return;}if(window.rsPanelOpen==='camera')startLive();else camera();}
window.addEventListener('pagehide',stopLive,false);
document.addEventListener('visibilitychange',shown,false);document.addEventListener('webkitvisibilitychange',shown,false);
camera();setInterval(camera,15000);setInterval(function(){if(lastCamera&&Date.now()-lastCamera>60000){el('camera-preview').removeAttribute('src');el('big-camera').removeAttribute('src');el('camera-state').textContent='Нет свежего снимка';}if(lastPrice&&(Date.now()-lastPrice>240000||!currentDay(prices)))window.rsSetPrices(null);else if(prices&&!hidden()){draw('price-chart',false);if(window.rsPanelOpen==='chart')draw('big-chart',true);}},30000);
draw('price-chart',false);
})();
