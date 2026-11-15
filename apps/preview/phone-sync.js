(function(){
'use strict';
var base='http://__RS_BRIDGE_HOST__:8790/',key='__RS_PHONE_TV_KEY__',rev=null,busy=false,dirty=false,serial=0;
function visible(){return !document.hidden&&!document.webkitHidden;}
function request(op,extra,done){
 var x=new XMLHttpRequest(),finished=false,data={key:key,op:op};
 if(extra)for(var k in extra)if(Object.prototype.hasOwnProperty.call(extra,k))data[k]=extra[k];
 function finish(code,p){if(finished)return;finished=true;done(code,p);}
 try{x.open('POST',base+'tv',true);x.setRequestHeader('Content-Type','text/plain');x.timeout=8000;x.onreadystatechange=function(){if(x.readyState===4){var p=null;try{p=JSON.parse(x.responseText);}catch(e){}finish(x.status,p);}};x.onerror=x.ontimeout=function(){finish(0,null);};x.send(JSON.stringify(data));}catch(e){finish(0,null);}
}
function pulse(){
 if(busy||!visible()||(!dirty&&window.rsPreferences.isOpen()))return;
 busy=true;
 var writing=dirty&&rev!==null,stamp=serial;
 request(writing?'write':'read',writing?{revision:rev,preferences:window.rsPreferences.snapshot()}:null,function(code,p){
  busy=false;
  if((code!==200&&code!==409)||!p||typeof p.revision!=='number')return;
  var changed=rev!==p.revision;rev=p.revision;
  if(writing&&code===200){if(stamp===serial)dirty=false;return;}
  if(!p.preferences){dirty=true;return;}
  if(!writing&&dirty&&stamp!==serial)return;
  if(code===409||changed){dirty=false;window.rsPreferences.receive(p.preferences);}
 });
}
var opened=false,restore=null,pairSerial=0;
function el(id){return document.getElementById(id);}
function close(){if(!opened)return;opened=false;pairSerial++;el('phone-overlay').style.display='none';el('phone-pin').textContent='';if(restore&&restore.focus)restore.focus();restore=null;}
el('phone-close').onclick=close;
window.rsPhoneSync={changed:function(){dirty=true;serial++;pulse();},isOpen:function(){return opened;},handleKey:function(e){e.preventDefault();if(e.keyCode===461||e.keyCode===27||(e.keyCode===13&&!e.repeat))close();},pair:function(){
 if(opened)return;opened=true;restore=document.activeElement;var stamp=++pairSerial;
 el('phone-overlay').style.display='block';el('phone-address').textContent=base;el('phone-pin').textContent='Подключение…';el('phone-close').focus();
 request('pair',null,function(code,p){if(!opened||stamp!==pairSerial)return;if(code===200&&p&&typeof p.pin==='string'){el('phone-pin').textContent=p.pin;}else{el('phone-pin').textContent='Сервер недоступен';}});
}};
pulse();setInterval(pulse,6000);
document.addEventListener('visibilitychange',pulse);document.addEventListener('webkitvisibilitychange',pulse);
})();
