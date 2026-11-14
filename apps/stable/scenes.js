(function(){
var key="__RS_ACTION_KEY__", pending=false, arm=0, selected='', last=0;
window.rsRunScene=function(id,label,msg){
 var now=Date.now();if(pending||now-last<500)return;last=now;
 if(id==='off'){
  if(selected!==id||now-arm>5000){selected=id;arm=now;msg('Нажми ещё раз OK в течение 5 секунд, чтобы выключить весь свет.');return;}
 }
 selected='';arm=0;pending=true;msg('Выполняется: '+label+'…');
 var x=new XMLHttpRequest(),done=false;
 function finish(ok){if(done)return;done=true;pending=false;msg(ok?'Команда принята: '+label:'Нет подтверждения: '+label+' (проверь Home Assistant)');}
 try{x.open('POST','http://__RS_BRIDGE_HOST__:8786/scene',true);x.setRequestHeader('Content-Type','text/plain');x.timeout=25000;x.onreadystatechange=function(){if(x.readyState===4){var ok=false;try{ok=x.status===200&&JSON.parse(x.responseText).ok===true;}catch(e){}finish(ok);}};x.onerror=x.ontimeout=function(){finish(false);};x.send(JSON.stringify({scene:id,key:key}));}catch(e){finish(false);}
};
})();