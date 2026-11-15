(function(){
'use strict';
var root=document.getElementById('remote-indicator'),battery=document.getElementById('remote-charge'),fill=document.getElementById('remote-charge-fill'),signal=document.getElementById('remote-signal'),label=document.getElementById('remote-state'),busy=false;
function display(p){
 var connected=!!(p&&p.connected),valid=connected&&typeof p.battery==='number'&&p.battery>=0&&p.battery<=100;
 battery.textContent=valid?p.battery+'%':'—%';fill.style.width=(valid?p.battery:0)+'%';fill.style.background=valid&&p.battery<=20?'#ffab9f':'#a4e7c1';
 var rssi=connected&&typeof p.rssi==='number'?p.rssi:null,bars=rssi===null?0:rssi>=-55?4:rssi>=-67?3:rssi>=-78?2:1;
 signal.className='remote-signal bars-'+bars;
 root.className='remote-indicator '+(connected?'online':'offline');
 label.textContent=!p?'Пульт: нет данных':!connected?'BT: нет связи':!p.ready?'BT: восстановление':!p.pointer?'BT: без курсора':rssi===null?'BT: есть связь':'BT';
}
function refresh(){if(busy||document.hidden||document.webkitHidden)return;busy=true;var x=new XMLHttpRequest(),finished=false;
 function done(p){if(finished)return;finished=true;busy=false;display(p);}
 try{x.open('GET','http://__RS_BRIDGE_HOST__:8787/api/indicator',true);x.timeout=4000;x.onreadystatechange=function(){if(x.readyState===4){try{done(x.status===200?JSON.parse(x.responseText):null);}catch(e){done(null);}}};x.onerror=x.ontimeout=function(){done(null);};x.send();}catch(e){done(null);}
}
refresh();setInterval(refresh,8000);document.addEventListener('visibilitychange',refresh);document.addEventListener('webkitvisibilitychange',refresh);
})();
