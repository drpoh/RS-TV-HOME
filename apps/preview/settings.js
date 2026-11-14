(function(){
'use strict';
var KEY='rs-tv-home.preferences.v1',themes=['blue','violet','forest','graphite'],names=['Синий','Фиолетовый','Зелёный','Графит'];
var pref={theme:'blue',order:[],hidden:[]},defaults=[],change=null,closed=null,opened=false,pick=0,focusIndex=0,controls=[],openRemote=null,displayPage=false,keys=['outdoor','indoor','sauna','price','camera','chart'],labels=['На улице','В доме','Сауна','Nord Pool','Камера крыльца','График цен'];
function el(id){return document.getElementById(id);}
try{var parsed=JSON.parse(localStorage.getItem(KEY)||'null');if(parsed&&themes.indexOf(parsed.theme)>=0)pref.theme=parsed.theme;if(parsed&&Object.prototype.toString.call(parsed.order)==='[object Array]')pref.order=parsed.order.map(function(id){return id==='fi.yle.areena'?'coffee_power':id;}).filter(function(id){return id!=='netflix'&&id!=='com.webos.app.livetv';});if(parsed&&Object.prototype.toString.call(parsed.hidden)==='[object Array]')pref.hidden=parsed.hidden.filter(function(k){return keys.indexOf(k)>=0;});}catch(e){}
function ordered(list){var result=[],used={};for(var i=0;i<pref.order.length&&i<32;i++){for(var j=0;j<list.length;j++)if(list[j][3]===pref.order[i]&&!used[list[j][3]]){used[list[j][3]]=true;result.push(list[j]);}}for(j=0;j<list.length;j++)if(!used[list[j][3]])result.push(list[j]);return result;}
function enabled(k){return pref.hidden.indexOf(k)<0;}
function apply(){document.body.className='theme-'+pref.theme;for(var i=0;i<4;i++)el('ha-'+keys[i]).parentNode.style.display=enabled(keys[i])?'':'none';el('camera-panel').style.display=enabled('camera')?'':'none';el('chart-panel').style.display=enabled('chart')?'':'none';el('camera-panel').parentNode.style.display=enabled('camera')||enabled('chart')?'':'none';el('ha-outdoor').parentNode.parentNode.style.display=keys.slice(0,4).some(enabled)?'':'none';}
function showDisplay(focus){
 displayPage=true;el('settings-main').style.display='none';el('display-settings').style.display='block';
 var groups=['display-metrics','display-panels','display-actions'];for(var j=0;j<groups.length;j++)el(groups[j]).innerHTML='';controls=[];
 for(var i=0;i<keys.length;i++)(function(n){var k=keys[n];make(n<4?'display-metrics':'display-panels',labels[n]+(enabled(k)?' · Вкл':' · Выкл'),function(){if(enabled(k))pref.hidden.push(k);else pref.hidden=pref.hidden.filter(function(x){return x!==k;});apply();save();showDisplay(n);},enabled(k));})(i);
 make('display-panels','Показать всё',function(){pref.hidden=[];apply();save();showDisplay(6);});
 make('display-panels','Назад',function(){rebuild(themes.length+defaults.length+7);});
 make('display-actions','Готово',close);select(focus);
}
function save(){if(window.rsPhoneSync)window.rsPhoneSync.changed();try{localStorage.setItem(KEY,JSON.stringify(pref));el('settings-info').textContent='Настройки сохранены';}catch(e){el('settings-info').textContent='Настройки действуют до закрытия приложения: хранилище недоступно';}}
function select(n){if(n<0||n>=controls.length)return;focusIndex=n;controls[n].focus();}
function make(parent,label,fn,chosen){var b=document.createElement('button'),n=controls.length;b.type='button';b.textContent=label;if(chosen)b.className='chosen';b.onfocus=function(){focusIndex=n;};b.onclick=function(){focusIndex=n;fn();};el(parent).appendChild(b);controls.push(b);}
function rebuild(focus){
 displayPage=false;el('settings-main').style.display='block';el('display-settings').style.display='none';
 var ids=['theme-options','order-options','move-options','other-options'];
 for(var i=0;i<ids.length;i++)el(ids[i]).innerHTML='';
 controls=[];var list=ordered(defaults);
 for(i=0;i<themes.length;i++)(function(n){make('theme-options',names[n],function(){pref.theme=themes[n];apply();save();rebuild(n);},pref.theme===themes[n]);})(i);
 for(i=0;i<list.length;i++)(function(n){make('order-options',(n+1)+'. '+list[n][0],function(){pick=n;rebuild(4+n);el('settings-info').textContent='Выбрано: '+list[n][0];},n===pick);})(i);
 make('move-options','← Раньше',function(){move(Math.max(0,pick-1),themes.length+list.length);});
 make('move-options','Позже →',function(){move(Math.min(list.length-1,pick+1),themes.length+list.length+1);});
 make('move-options','В начало',function(){move(0,themes.length+list.length+2);});
 make('move-options','Сброс порядка',function(){pref.order=[];pick=0;change(ordered(defaults));save();rebuild(themes.length+list.length+3);});
 make('other-options','Сброс темы',function(){pref.theme='blue';apply();save();rebuild(themes.length+list.length+4);});
 make('other-options','Готово',close);
 make('other-options','Калибровка пульта',function(){if(openRemote){close();openRemote();}});
 make('other-options','Панель умного дома',function(){showDisplay(0);});
 make('other-options','Настройки с телефона',function(){if(window.rsPhoneSync)window.rsPhoneSync.pair();});
 select(focus);
}
function move(to,focus){var list=ordered(defaults);if(to===pick){el('settings-info').textContent='Приложение уже на этой позиции';return;}var item=list.splice(pick,1)[0];list.splice(to,0,item);pick=to;pref.order=list.map(function(x){return x[3];});change(list);save();rebuild(focus);}
function close(){if(!opened)return;opened=false;el('settings-overlay').style.display='none';if(closed)closed();}
window.rsPreferences={snapshot:function(){return {theme:pref.theme,order:ordered(defaults).map(function(x){return x[3];}),hidden:pref.hidden.slice()};},receive:function(p){if(!p||themes.indexOf(p.theme)<0||!Array.isArray(p.order)||!Array.isArray(p.hidden))return;pref.theme=p.theme;pref.order=p.order.filter(function(id){return defaults.some(function(x){return x[3]===id;});});pref.hidden=p.hidden.filter(function(k){return keys.indexOf(k)>=0;});apply();if(change)change(ordered(defaults));try{localStorage.setItem(KEY,JSON.stringify(pref));}catch(e){}if(opened){if(displayPage)showDisplay(focusIndex);else rebuild(focusIndex);}},ordered:ordered,configure:function(list,onChange,onClose,onRemote){openRemote=onRemote;defaults=list.slice();change=onChange;closed=onClose;apply();},open:function(){if(opened)return;opened=true;pick=0;el('settings-overlay').style.display='block';el('settings-info').textContent='';rebuild(Math.max(0,themes.indexOf(pref.theme)));},isOpen:function(){return opened;},key:function(e){var k=e.keyCode,n=focusIndex;if(k===461||k===27){e.preventDefault();if(displayPage)rebuild(themes.length+defaults.length+7);else close();return;}if(k===13){e.preventDefault();if(!e.repeat&&controls[n])controls[n].click();return;}if(k>=37&&k<=40&&controls[n]){var r=controls[n].getBoundingClientRect(),x=(r.left+r.right)/2,y=(r.top+r.bottom)/2,best=-1,score=Infinity;for(var j=0;j<controls.length;j++){if(j===n)continue;var q=controls[j].getBoundingClientRect(),dx=(q.left+q.right)/2-x,dy=(q.top+q.bottom)/2-y,h=k===37||k===39,primary=h?dx:dy,secondary=h?dy:dx;if(primary*(k===37||k===38?-1:1)<=1)continue;if(h&&Math.abs(secondary)>10)continue;var cost=Math.abs(primary)*4+Math.abs(secondary);if(cost<score){score=cost;best=j;}}if(best>=0)n=best;}if(k>=37&&k<=40){e.preventDefault();select(n);}}};
})();
