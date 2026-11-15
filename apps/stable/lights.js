(function(){
'use strict';
var base='http://__RS_BRIDGE_HOST__:8786',key='__RS_ACTION_KEY__';
var active=false, rooms=[], current='', focusId='', readBusy=false, actionBusy=false, epoch=0, signature='', last=0, closeCallback=null;
function el(id){return document.getElementById(id);}
function make(tag,cls,txt){var n=document.createElement(tag);n.className=cls;if(txt)n.textContent=txt;return n;}
function message(s){el('light-status').textContent=s;}
function nodes(){return Array.prototype.slice.call(el('lights-overlay').querySelectorAll('button[data-focus]'));}
function selectedRoom(){for(var i=0;i<rooms.length;i++)if(rooms[i].id===current)return rooms[i];return null;}
function focus(id){var a=nodes(),n=null;for(var i=0;i<a.length;i++)if(a[i].getAttribute('data-focus')===id)n=a[i];if(!n)n=a[0];if(n){focusId=n.getAttribute('data-focus');n.focus();}}
function btn(id,cls,txt,fn){var n=make('button',cls,txt);n.type='button';n.setAttribute('data-focus',id);n.onfocus=function(){focusId=id;};n.onclick=fn;return n;}
function render(restore){
 var old=focusId,r=selectedRoom();
 if(!r&&rooms.length){current=rooms[0].id;r=rooms[0];}
 var left=el('light-rooms'),right=el('light-devices');left.textContent='';right.textContent='';
 for(var i=0;i<rooms.length;i++)(function(room){
  var b=btn('room-'+room.id,'light-room'+(room.id===current?' active':''),room.label,function(){current=room.id;render(false);focus('room-'+room.id);});
  left.appendChild(b);
 })(rooms[i]);
 el('light-room-title').textContent=r?r.label:'Свет';
 if(r)for(var j=0;j<r.lights.length;j++)(function(l){
   var b=btn('device-'+l.id,'light-device '+l.state,'',function(){command(l);});
   b.appendChild(make('span','light-bulb',l.state==='on'?'●':'○'));
   b.appendChild(make('span','light-label',l.label));
   b.appendChild(make('span','light-switch',l.state==='on'?'Вкл':l.state==='off'?'Выкл':'Недоступно'));
   if(l.state==='unavailable')b.setAttribute('aria-disabled','true');
   right.appendChild(b);
 })(r.lights[j]);
 if(restore)focus(old);
}
function request(method,path,payload,done){
 var x=new XMLHttpRequest(),ended=false;
 function finish(v){if(ended)return;ended=true;done(v);}
 try{x.open(method,base+path,true);x.timeout=25000;x.onreadystatechange=function(){if(x.readyState===4){try{finish(x.status===200?JSON.parse(x.responseText):null);}catch(e){finish(null);}}};x.onerror=x.ontimeout=function(){finish(null);};if(method==='POST')x.setRequestHeader('Content-Type','text/plain');x.send(payload?JSON.stringify(payload):null);}catch(e){finish(null);}
}
function refresh(force){
 if(!active||readBusy||actionBusy||document.hidden||document.webkitHidden)return;
 if(!force&&Date.now()-last<4000)return;
 readBusy=true;var e=epoch;
 request('GET','/lights',null,function(d){
  if(e!==epoch)return;readBusy=false;if(!active)return;
  last=Date.now();
  if(!d||!Array.isArray(d.rooms)){
   if(rooms.length){for(var i=0;i<rooms.length;i++)for(var j=0;j<rooms[i].lights.length;j++)rooms[i].lights[j].state='unavailable';render(true);}
   message('Нет связи с Home Assistant');return;
  }
  var sig=JSON.stringify(d.rooms);if(sig!==signature){signature=sig;rooms=d.rooms;render(true);}
  message(d.available?(rooms.length?'Состояние обновлено · OK — переключить':'Освещение пока не настроено'):'Нет данных от Home Assistant');
 });
}
function command(l){
 if(actionBusy||l.state==='unavailable')return;
 // Ignore an in-flight stale poll rather than swallowing a button press.
 actionBusy=true;readBusy=false;var e=++epoch;message('Выполняется: '+l.label+'…');
 request('POST','/light',{id:l.id,state:l.state==='on'?'off':'on',key:key},function(d){
  if(e!==epoch)return;actionBusy=false;message(d&&d.ok?'Команда принята · проверка состояния…':'Команда не подтверждена');signature='';last=0;
  if(active){refresh(true);setTimeout(function(){refresh(true);},3000);}
 });
}
function close(){active=false;epoch++;readBusy=false;actionBusy=false;el('lights-overlay').style.display='none';if(closeCallback)closeCallback();}
window.rsLights={isOpen:function(){return active;},open:function(cb){active=true;epoch++;closeCallback=cb;rooms=[];current='';signature='';last=0;readBusy=false;actionBusy=false;el('lights-overlay').style.display='block';render(false);message('Подключение…');focus('close');refresh(true);},
 key:function(e){var k=e.keyCode||e.which;if(k===461||k===27){e.preventDefault();close();return;}if(k<13)return;
  var n=document.activeElement,r=selectedRoom(),v=focusId;
  if(k===13){e.preventDefault();if(!e.repeat&&n&&n.click)n.click();return;}
  if(k<37||k>40)return;e.preventDefault();
  if(v==='close'){if(k===40&&rooms.length)focus('room-'+current);return;}
  if(v.indexOf('room-')===0){
   if(k===39&&r&&r.lights.length){focus('device-'+r.lights[0].id);return;}
   if(k===38||k===40){var ri=0;for(var i=0;i<rooms.length;i++)if('room-'+rooms[i].id===v)ri=i;var next=ri+(k===38?-1:1);if(next<0)focus('close');else if(next<rooms.length){current=rooms[next].id;render(false);focus('room-'+current);}return;}
  }
  if(v.indexOf('device-')===0&&r){if(k===37){focus('room-'+current);return;}var di=0;for(var j=0;j<r.lights.length;j++)if('device-'+r.lights[j].id===v)di=j;
   if(k===38&&di===0){focus('close');return;}var nextD=di+(k===38?-1:k===40?1:0);if(r.lights[nextD])focus('device-'+r.lights[nextD].id);
  }
 }
};
el('lights-close').onclick=close;el('lights-close').onfocus=function(){focusId='close';};
setInterval(function(){refresh(false);},6000);
document.addEventListener('visibilitychange',function(){if(active&&!document.hidden)refresh(true);});
})();
