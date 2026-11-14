(function(){
'use strict';
var items=[
['OTT Player','IPTV','IPTV','es.ottplayer.widget','ott'],
['YouTube','Видео','▶','youtube.leanback.v4','youtube'],
['Включить кофе-машину','Только питание','☕','coffee_power','coffee'],
['Фоторамка','Семейные фото и видео','Фото','com.rs.familyframe','family'],
['Браузер','Интернет','WEB','com.webos.app.browser','browser'],
['Screen Share','Экран ноутбука','Cast','com.webos.app.miracast','cast'],
['Дневной свет','Освещение','','day','scene-tile'],
['Кино','Приглушённый свет','','movie','scene-tile'],
['Утро','Сценарий света','','morning','scene-tile'],
['Выключить свет','Подтверждение','','off','scene-tile scene-off']
],buttons=[],current=0,activeBridge=null,pending=false,status=document.getElementById('status');
var APP_COUNT=6,SCENE_COUNT=4,PANEL_START=APP_COUNT+SCENE_COUNT,SETTINGS=PANEL_START+2,CATALOG=SETTINGS+1;
var appDefaults=items.slice(0,APP_COUNT);
if(window.rsPreferences)items=window.rsPreferences.ordered(appDefaults).concat(items.slice(APP_COUNT));
function msg(s){status.textContent=s;if(window.rsCatalog&&window.rsCatalog.isOpen())window.rsCatalog.status(s);}
function pad(n){return n<10?'0'+n:String(n);}
function clock(){var d=new Date(),days=['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];document.getElementById('clock').textContent=pad(d.getHours())+':'+pad(d.getMinutes());document.getElementById('date').textContent=days[d.getDay()]+', '+pad(d.getDate())+'.'+pad(d.getMonth()+1)+'.'+d.getFullYear();}
function size(){var s=document.getElementById('screen'),z=Math.min(window.innerWidth/1280,window.innerHeight/720);s.style.left=((window.innerWidth-1280*z)/2)+'px';s.style.top=((window.innerHeight-720*z)/2)+'px';s.style.webkitTransform='scale('+z+')';s.style.transform='scale('+z+')';}
function visible(i){return !!buttons[i]&&buttons[i].style.display!=='none';}
function select(i){if(!visible(i))return;buttons[current].className=buttons[current].className.replace(/ selected/g,'');current=i;buttons[current].className+=' selected';buttons[current].focus();}
function moveFocus(k){
 var rows=[[CATALOG,SETTINGS],[0,1,2],[3,4,5],[PANEL_START,PANEL_START+1],[APP_COUNT,APP_COUNT+1,APP_COUNT+2,APP_COUNT+3]],r=-1,c=-1,i,j;
 for(i=0;i<rows.length;i++)for(j=0;j<rows[i].length;j++)if(rows[i][j]===current){r=i;c=j;}
 if(r<0)return current;
 if(k===37||k===39){var step=k===37?-1:1;for(i=c+step;i>=0&&i<rows[r].length;i+=step)if(visible(rows[r][i]))return rows[r][i];return current;}
 var rect=buttons[current].getBoundingClientRect(),x=(rect.left+rect.right)/2,dir=k===38?-1:1;
 for(i=r+dir;i>=0&&i<rows.length;i+=dir){var best=-1,dist=Infinity;for(j=0;j<rows[i].length;j++){var n=rows[i][j];if(!visible(n))continue;var q=buttons[n].getBoundingClientRect(),d=Math.abs((q.left+q.right)/2-x);if(d<dist){best=n;dist=d;}}if(best>=0)return best;}
 return current;
}
function launch(n){if(pending)return;if(n===CATALOG){window.rsCatalog.open();return;}if(n===SETTINGS){window.rsPreferences.open();return;}if(n>=PANEL_START){window.rsOpenPanel(n===PANEL_START?"camera":"chart");return;}var item=items[n];if(n>=APP_COUNT||item[3]==='coffee_power'){window.rsRunScene(item[3],item[0],msg);return;}launchItem(item);}
function launchItem(item){if(pending)return;msg('Открываем '+item[0]+'…');if(typeof PalmServiceBridge==='undefined'){msg('API запуска недоступен на этой версии webOS.');return;}pending=true;var urls=['luna://com.webos.applicationManager/launch','luna://com.palm.applicationManager/launch'];var i=0;function call(){try{var b=new PalmServiceBridge();activeBridge=b;b.onservicecallback=function(raw){var r;try{r=JSON.parse(raw);}catch(e){r={returnValue:false};} if(r.returnValue){pending=false;msg('');return;}if(i<urls.length){call();return;}pending=false;msg('Не удалось открыть '+item[0]+': '+(r.errorText||'ошибка API'));};b.call(urls[i++],JSON.stringify({id:item[3]}));}catch(e){if(i<urls.length&&i>0){call();return;}pending=false;msg('Ошибка API запуска.');}}call();setTimeout(function(){if(pending){pending=false;msg('Телевизор не ответил на команду.');}},6500);}
function node(tag,clazz,txt){var el=document.createElement(tag);el.className=clazz;el.textContent=txt;return el;}
for(var j=0;j<items.length;j++){(function(i){var item=items[i],b=document.createElement('button');b.type='button';b.className='tile '+item[4];if(i<APP_COUNT)b.appendChild(node('span','mark',item[2]));b.appendChild(node('span','label',item[0]));b.appendChild(node('span','detail',item[1]));b.onclick=function(){select(i);launch(i);};b.onfocus=function(){if(current!==i){buttons[current].className=buttons[current].className.replace(/ selected/g,'');current=i;b.className+=' selected';}};document.getElementById(i<APP_COUNT?'tiles':'scenes').appendChild(b);buttons.push(b);})(j);}
for(var k=0;k<2;k++){(function(i){var b=document.getElementById(i===PANEL_START?'camera-panel':'chart-panel');buttons.push(b);b.onclick=function(){select(i);launch(i);};b.onfocus=function(){if(current!==i){buttons[current].className=buttons[current].className.replace(/ selected/g,'');current=i;b.className+=' selected';}};})(PANEL_START+k);}
var sb=document.getElementById('settings-button');buttons.push(sb);
sb.onclick=function(){select(SETTINGS);launch(SETTINGS);};sb.onfocus=function(){if(current!==SETTINGS){buttons[current].className=buttons[current].className.replace(/ selected/g,'');current=SETTINGS;sb.className+=' selected';}};
var cb=document.getElementById('catalog-button');buttons.push(cb);
cb.onclick=function(){select(CATALOG);launch(CATALOG);};cb.onfocus=function(){if(current!==CATALOG){buttons[current].className=buttons[current].className.replace(/ selected/g,'');current=CATALOG;cb.className+=' selected';}};
window.rsCatalog.configure(launchItem,function(){select(CATALOG);});
window.rsPreferences.configure(appDefaults,function(order){
 items=order.concat(items.slice(APP_COUNT));
 for(var i=0;i<APP_COUNT;i++){
  var b=buttons[i],it=items[i];
  b.className='tile '+it[4]+(current===i?' selected':'');
  b.children[0].textContent=it[2];b.children[1].textContent=it[0];b.children[2].textContent=it[1];
 }
},function(){select(SETTINGS);},function(){launchItem(['RS Magic Remote','Калибровка пульта','','com.rs.magicremote']);});
document.getElementById('close-panel').onclick=function(){window.rsClosePanel();select(current);};
document.addEventListener('keydown',function(e){var k=e.keyCode,next=current;if(window.rsCatalog.isOpen()){window.rsCatalog.key(e);return;}if(window.rsPreferences.isOpen()){window.rsPreferences.key(e);return;}if(window.rsPanelOpen){if(k===461||k===27||k===13){e.preventDefault();window.rsClosePanel();select(current);}else if(k>=37&&k<=40)e.preventDefault();return;}
if(k>=37&&k<=40){e.preventDefault();select(moveFocus(k));}if(k===13){e.preventDefault();if(!e.repeat)launch(current);}if(k===461||(k===27)){e.preventDefault();if(window.PalmSystem&&PalmSystem.platformBack)PalmSystem.platformBack();else window.close();}},false);
document.addEventListener('visibilitychange',function(){if(!document.hidden&&!document.webkitHidden&&!window.rsPreferences.isOpen()&&!window.rsCatalog.isOpen()){pending=false;msg('');select(current);}},false);
window.addEventListener('resize',size,false);size();clock();setInterval(clock,1000);select(0);if(window.PalmSystem&&PalmSystem.stageReady)PalmSystem.stageReady();
})();
