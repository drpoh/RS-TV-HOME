(function(){
'use strict';
var apps=[
['Media Station X','Мультимедиа','MSX','de.benzac.msx'],
['VK Видео','Установлено · не проверено','VK','vkvideo'],
['Rutube','Установлено · не проверено','RT','rutube'],
['SmartShare','Медиа и USB','USB','com.webos.app.smartshare'],
['Homebrew','Каталог приложений','HB','org.webosbrew.hbchannel'],
['Speedtest','Проверка сети','Speed','com.lgerp.speedtest'],
['Ministra','IPTV','TV','com.ministra.app.player'],
['Stalker Player','IPTV','TV','com.stalker.app.player'],
['Иви','Установлено · не проверено','ivi','ivi'],
['ТНТ MUSIC','Музыка','TNT','tntmusic'],
['Первый','Телеканал','1','channelone'],
['СТС','Телеканал','CTC','ctc.media'],
['Europa Plus TV','Музыка','EP','europaplustv'],
['Уведомления','Системные','INFO','com.webos.app.notificationcenter'],
['Назад','Вернуться на главный экран','','']
],buttons=[],current=0,opened=false,run=null,closed=null;
function el(id){return document.getElementById(id);}
function select(n){if(n<0||n>=buttons.length)return;current=n;buttons[n].focus();}
function expanded(value){el('catalog-button').setAttribute('aria-expanded',value?'true':'false');el('catalog-arrow').textContent=value?'▴':'▾';}
function close(){if(!opened)return;opened=false;el('catalog-overlay').style.display='none';expanded(false);if(closed)closed();}
function act(i){if(!apps[i][3])close();else if(run)run(apps[i]);}
function show(){
 if(opened)return;opened=true;el('catalog-status').textContent='';el('catalog-apps').innerHTML='';buttons=[];
 for(var i=0;i<apps.length;i++)(function(n){
  var b=document.createElement('button'),small=document.createElement('small');b.type='button';b.textContent=apps[n][0];small.textContent=apps[n][1];b.appendChild(small);
  b.onfocus=function(){current=n;};b.onclick=function(){current=n;act(n);};el('catalog-apps').appendChild(b);buttons.push(b);
 })(i);
 el('catalog-overlay').style.display='block';expanded(true);el('catalog-overlay').onclick=function(e){if(e.target===el('catalog-overlay'))close();};select(current);
}
window.rsCatalog={configure:function(fn,onClose){run=fn;closed=onClose;},open:show,isOpen:function(){return opened;},status:function(s){el('catalog-status').textContent=s;},key:function(e){var k=e.keyCode,n=current;if(k===461||k===27){e.preventDefault();close();return;}if(k===13){e.preventDefault();if(!e.repeat)act(current);return;}if(k===37&&n%3>0)n--;if(k===39&&n%3<2&&n+1<buttons.length)n++;if(k===38&&n>=3)n-=3;if(k===40&&n+3<buttons.length)n+=3;if(k>=37&&k<=40){e.preventDefault();select(n);}}};
})();
