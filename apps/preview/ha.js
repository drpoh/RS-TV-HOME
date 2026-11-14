(function(){
var ids=['outdoor','indoor','sauna','price'],last=0,busy=false,script=null,timeout=null;
function hidden(){return document.hidden===true||document.webkitHidden===true;}
function el(id){return document.getElementById(id);}
function clear(){if(window.rsSetPrices)window.rsSetPrices(null);for(var i=0;i<ids.length;i++)el('ha-'+ids[i]).textContent='—';el('ha-link').textContent='Home Assistant · нет данных';}
function release(){busy=false;if(timeout){clearTimeout(timeout);timeout=null;}if(script&&script.parentNode)script.parentNode.removeChild(script);script=null;}
window.rsHaUpdate=function(d){release();if(window.rsSetPrices)window.rsSetPrices(d&&d.priceDay);if(!d||!d.values){clear();return;}if(!d.available){clear();return;}last=Date.now();for(var i=0;i<ids.length;i++){var k=ids[i],n=d.values[k];el('ha-'+k).textContent=typeof n==='number'&&isFinite(n)?n.toFixed(1).replace('.',',')+(k==='price'?' ¢/кВт·ч':' °C'):'—';}el('ha-link').textContent='Home Assistant · онлайн';};
function fail(){release();if(!last||Date.now()-last>240000)clear();else el('ha-link').textContent='Home Assistant · повтор подключения';}
function refresh(){if(busy||hidden())return;busy=true;script=document.createElement('script');script.src='http://__RS_BRIDGE_HOST__:8786/status.js';script.onerror=fail;timeout=setTimeout(fail,35000);document.head.appendChild(script);}
function shown(){if(!hidden())refresh();}
document.addEventListener('visibilitychange',shown);document.addEventListener('webkitvisibilitychange',shown);refresh();setInterval(refresh,120000);setInterval(function(){if(last&&Date.now()-last>240000)clear();},30000);
})();