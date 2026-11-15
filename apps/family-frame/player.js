(function(){
'use strict';
var base='http://__RS_BRIDGE_HOST__:8788',editKey='__RS_FRAME_KEY__',all=[],items=[],index=0,layer=0,delay=10,paused=false,timer=null,watch=null,hideTimer=null,seq=0,loaded=false,pending=false,albumSeq=0,signature=null,mode='',filter='all',random=true,clockOn=true,angle=0,saved=0,hiddenCount=0,errors=0,menu=false,confirm=false,editBusy=false,controls=[],focus=0,choice=0;
function el(id){return document.getElementById(id);}
var v=el('video');
try{var prefs=JSON.parse(localStorage.getItem('rs-family-frame.prefs.v2')||'{}');if(typeof prefs.delay==='number'&&prefs.delay>=5&&prefs.delay<=120)delay=prefs.delay;if(['all','photo','video'].indexOf(prefs.filter)>=0)filter=prefs.filter;if(typeof prefs.random==='boolean')random=prefs.random;if(typeof prefs.clockOn==='boolean')clockOn=prefs.clockOn;}catch(e){}
function persist(){try{localStorage.setItem('rs-family-frame.prefs.v2',JSON.stringify({delay:delay,filter:filter,random:random,clockOn:clockOn}));}catch(e){}}
function say(msg){el('notice').textContent=msg;el('bar').className=menu?'hidden':'';clearTimeout(hideTimer);hideTimer=setTimeout(function(){el('notice').textContent='';if(loaded)el('bar').className='hidden';},4500);}
function count(){el('count').textContent=items.length?(index+1)+' / '+items.length+' · '+(mode==='video'?'Видео':delay+' сек.')+(paused?' · Пауза':''):'';el('menu-note').textContent=items.length?(index+1)+' / '+items.length+' · '+(mode==='video'?'Видео':'Фото')+' · '+angle+'°'+(angle!==saved?' · Поворот не сохранён':''):'Нет файлов для показа';}
function clear(){clearTimeout(timer);clearTimeout(watch);}
function schedule(){clearTimeout(timer);if(!paused&&items.length>1&&mode!=='video')timer=setTimeout(function(){show(index+1);},delay*1000);}
function stopVideo(){v.onended=v.onerror=v.onplaying=v.onwaiting=v.onstalled=v.onloadeddata=null;try{v.pause();v.removeAttribute('src');v.load();}catch(e){}v.className='hidden';}
function empty(msg){loaded=false;el('empty').className='';el('message').textContent=msg;if(!menu)el('bar').className='';}
function fail(ticket){if(ticket!==seq)return;clear();stopVideo();errors++;say('Файл недоступен');if(errors>=items.length){paused=true;empty('Не удалось воспроизвести файлы. Откройте меню.');return;}if(!paused&&items.length>1)timer=setTimeout(function(){show(index+1);},2000);}
function watchdog(ticket){clearTimeout(watch);watch=setTimeout(function(){fail(ticket);},30000);}
function layout(node,a){var w=window.innerWidth||1280,h=window.innerHeight||720,swap=a===90||a===270,nw=swap?h:w,nh=swap?w:h;node.style.width=nw+'px';node.style.height=nh+'px';node.style.left=(w-nw)/2+'px';node.style.top=(h-nh)/2+'px';node.style.webkitTransform='rotate('+a+'deg)';node.style.transform='rotate('+a+'deg)';}
function applyRotation(){layout(mode==='video'?v:el('p'+layer),angle);count();}
function playing(){if(!paused&&mode==='video'){var ticket=seq;watchdog(ticket);try{var play=v.play();if(play&&play.catch)play.catch(function(){if(!paused)fail(ticket);});}catch(e){fail(ticket);}}else if(mode!=='video')schedule();}
function show(n){
 if(!items.length)return;clear();var ticket=++seq;stopVideo();index=(n+items.length)%items.length;var item=items[index];mode=item.type;angle=saved=item.rotation||0;
 if(mode==='video'){
  layout(v,angle);
  v.onended=function(){if(ticket===seq&&!paused)show(index+1);};v.onerror=function(){fail(ticket);};
  v.onloadeddata=function(){if(ticket!==seq)return;clearTimeout(watch);loaded=true;errors=0;el('empty').className='hidden';v.className='';count();};
  v.onplaying=function(){if(ticket!==seq)return;clearTimeout(watch);loaded=true;errors=0;el('empty').className='hidden';v.className='';count();};
  v.onwaiting=v.onstalled=function(){if(!paused)watchdog(ticket);};
  v.src=base+'/video/'+item.id;v.className='';el('empty').className='hidden';if(!paused)playing();
  count();return;
 }
 var next=1-layer,img=new Image(),url=base+'/photo/'+item.id;
 watchdog(ticket);
 img.onload=function(){if(ticket!==seq)return;clearTimeout(watch);layout(el('p'+next),angle);el('p'+next).style.backgroundImage='url("'+url+'")';el('p'+next).style.opacity='1';el('p'+layer).style.opacity='0';layer=next;loaded=true;errors=0;el('empty').className='hidden';count();schedule();};
 img.onerror=function(){fail(ticket);};img.src=url;count();
}
function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1)),t=a[i];a[i]=a[j];a[j]=t;}return a;}
function order(a){if(!random)return a.slice();var p=[],b=[],r=[];for(var i=0;i<a.length;i++)(a[i].type==='video'?b:p).push(a[i]);shuffle(p);shuffle(b);while(p.length||b.length){for(var j=0;j<3&&p.length;j++)r.push(p.pop());if(b.length)r.push(b.pop());}return r;}
function rebuild(force){var old=items[index]&&items[index].id,prev=items[index],i,list=all.filter(function(a){return filter==='all'||filter===a.type;}),map={},next=[];
 if(!force&&random){for(i=0;i<list.length;i++)map[list[i].id]=list[i];for(i=0;i<items.length;i++)if(map[items[i].id]){next.push(map[items[i].id]);delete map[items[i].id];}items=next.concat(order(list.filter(function(a){return !!map[a.id];})));}else items=order(list);
 if(!items.length){++seq;clear();stopVideo();mode='';el('p0').style.opacity=el('p1').style.opacity='0';empty('Нет файлов выбранного типа. Измените режим показа.');count();return;}
 for(i=0;i<items.length;i++)if(items[i].id===old){index=i;if(prev&&saved===angle){angle=saved=items[i].rotation||0;applyRotation();}count();return;}
 show(force?0:Math.min(index,items.length-1));}
function refresh(){
 if(pending||editBusy)return;pending=true;var x=new XMLHttpRequest(),finished=false,ticket=++albumSeq;
 function done(){if(finished)return false;finished=true;if(ticket!==albumSeq)return false;pending=false;return true;}
 x.open('GET',base+'/api/album',true);x.timeout=6000;
 x.onreadystatechange=function(){if(x.readyState!==4||!done())return;if(x.status!==200){if(!loaded)empty('Альбом недоступен. Проверяем подключение.');return;}
  try{var a=JSON.parse(x.responseText),fresh=a.items||[],sig=[],i;hiddenCount=a.hiddenCount||0;
   for(i=0;i<fresh.length;i++)sig.push(fresh[i].id+':'+(fresh[i].rotation||0));sig.sort();sig=sig.join(',');
   if(sig===signature){if(menu)render(focus);return;}signature=sig;all=fresh;rebuild(false);if(menu)render(focus);
  }catch(e){if(!loaded)empty('Не удалось прочитать альбом.');}
 };
 x.onerror=x.ontimeout=function(){if(done()&&!loaded)empty('Альбом недоступен.');};
 try{x.send();}catch(e){done();empty('Нет соединения с Raspberry Pi.');}
}
function edit(op,callback){if(editBusy)return;var item=items[index];if(op!=='restore'&&!item)return;editBusy=true;albumSeq++;pending=false;var x=new XMLHttpRequest(),finished=false,data={op:op,key:editKey};if(item)data.id=item.id;if(op==='rotate')data.rotation=angle;
 function done(ok){if(finished)return;finished=true;editBusy=false;if(ok){callback();signature=null;refresh();}else say('Не удалось сохранить. Проверьте подключение.');if(menu)render(focus);}
 try{x.open('POST',base+'/api/edit',true);x.setRequestHeader('Content-Type','text/plain');x.timeout=9000;x.onreadystatechange=function(){if(x.readyState===4)done(x.status===200);};x.onerror=x.ontimeout=function(){done(false);};x.send(JSON.stringify(data));}catch(e){done(false);}
}
function toggle(){paused=!paused;if(paused){clear();if(mode==='video')v.pause();}else {errors=0;playing();}count();say(paused?'Пауза':'Воспроизведение');}
function setPause(){if(!paused)toggle();}
function move(n){if(!editBusy){errors=0;show(index+n);if(menu)render(focus);}}
function rotate(n){if(!items.length)return;angle=(angle+n+360)%360;applyRotation();if(menu)render(focus);}
function save(){var a=angle,id=items[index]&&items[index].id;edit('rotate',function(){if(items[index]&&items[index].id===id){saved=a;items[index].rotation=a;}say('Поворот сохранён');});}
function confirmDelete(){if(!items.length||editBusy)return;setPause();confirm=true;choice=0;el('confirm').className='';el('no').focus();}
function dismiss(){confirm=false;el('confirm').className='hidden';if(menu)render(focus);}
function remove(){if(!confirm)return;dismiss();var id=items[index]&&items[index].id;edit('hide',function(){all=all.filter(function(a){return a.id!==id;});rebuild(false);hiddenCount++;say('Убрано из показа');});}
el('no').onclick=dismiss;el('yes').onclick=remove;el('no').onfocus=function(){choice=0;};el('yes').onfocus=function(){choice=1;};
function cycle(){var a=['all','photo','video'];filter=a[(a.indexOf(filter)+1)%3];persist();rebuild(true);render(focus);}
function interval(n){delay=Math.max(5,Math.min(120,delay+n));persist();count();schedule();render(focus);}
function closeMenu(){if(editBusy)return;menu=false;el('menu').className='hidden';say('');}
function openMenu(){if(menu)return;setPause();menu=true;el('menu').className='';el('bar').className='hidden';render(0);}
function add(label,fn,disabled,warn){var b=document.createElement('button'),n=controls.length;b.type='button';b.textContent=label;b.disabled=!!disabled;if(warn)b.className='warn';b.onfocus=function(){focus=n;};b.onclick=function(){if(!b.disabled&&!editBusy)fn();};el('actions').appendChild(b);controls.push(b);}
function select(n){if(controls[n]&&!controls[n].disabled){focus=n;controls[n].focus();}}
function render(n){if(!menu)return;el('actions').innerHTML='';controls=[];var no=!items.length;
 add(paused?'▶ Продолжить':'Ⅱ Пауза',function(){toggle();render(focus);},no);
 add('← Предыдущее',function(){move(-1);},no);add('Следующее →',function(){move(1);},no);add('Закрыть меню',closeMenu);
 add('↶ Повернуть 90°',function(){setPause();rotate(-90);},no);add('Повернуть 90° ↷',function(){setPause();rotate(90);},no);
 add('Сохранить поворот',save,no||angle===saved);add('Удалить…',confirmDelete,no,true);
 add('Режим: '+({all:'Все',photo:'Фото',video:'Видео'}[filter]),cycle);
 add('Фото: −5 сек.',function(){interval(-5);},delay<=5);add('Фото: '+delay+' сек. +',function(){interval(5);},delay>=120);
 add(random?'Порядок: случайный':'Порядок: по имени',function(){random=!random;persist();rebuild(true);render(focus);});
 add(clockOn?'Часы: вкл.':'Часы: выкл.',function(){clockOn=!clockOn;el('clock').className=clockOn?'':'hidden';persist();render(focus);});
 add('Вернуть удалённое',function(){edit('restore',function(){hiddenCount=Math.max(0,hiddenCount-1);say('Файл возвращён');});},!hiddenCount);
 count();if(!controls[n]||controls[n].disabled){for(n=0;n<controls.length&&controls[n].disabled;n++);}select(n);
}
el('bar').onclick=openMenu;el('p0').onclick=el('p1').onclick=v.onclick=openMenu;
document.addEventListener('keydown',function(e){
 var k=e.keyCode,back=k===461||k===27;
 if(confirm){if(back)dismiss();else if(k===37||k===39){choice=k===37?0:1;el(choice?'yes':'no').focus();}else if(k===13&&!e.repeat){if(choice)remove();else dismiss();}e.preventDefault();return;}
 if(menu){if(back)closeMenu();else if(k===13&&!e.repeat&&controls[focus])controls[focus].click();else if(k>=37&&k<=40){var step=k===37?-1:k===39?1:k===38?-4:4,n=focus+step;while(n>=0&&n<controls.length){if(Math.abs(step)===1&&Math.floor(n/4)!==Math.floor(focus/4))break;if(!controls[n].disabled){select(n);break;}n+=step;}}else return;e.preventDefault();return;}
 if(k===37||k===39){move(k===37?-1:1);say('');}
 else if(k===13&&!e.repeat)toggle();
 else if(k===38||k===40)openMenu();
 else if(back){++seq;clear();stopVideo();if(window.PalmSystem&&PalmSystem.platformBack)PalmSystem.platformBack();else window.close();return;}
 else return;e.preventDefault();
});
function clock(){var d=new Date(),h=d.getHours(),m=d.getMinutes();el('clock').textContent=(h<10?'0':'')+h+':'+(m<10?'0':'')+m;}
window.addEventListener('resize',function(){applyRotation();});
el('clock').className=clockOn?'':'hidden';clock();setInterval(clock,15000);refresh();setInterval(refresh,30000);
})();
