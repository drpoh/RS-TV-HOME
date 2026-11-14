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
window.rsPhoneSync={changed:function(){dirty=true;serial++;pulse();},pair:function(){
 var info=document.getElementById('settings-info');info.textContent='Подключение…';
 request('pair',null,function(code,p){if(code===200&&p&&typeof p.pin==='string'){info.textContent='На телефоне: '+base+' · Код: '+p.pin+' · Только домашний Wi-Fi';}else{info.textContent='Панель телефона недоступна';}});
}};
pulse();setInterval(pulse,6000);
document.addEventListener('visibilitychange',pulse);document.addEventListener('webkitvisibilitychange',pulse);
})();
