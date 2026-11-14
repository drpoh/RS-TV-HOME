"""Exact speech intents, bound only to the living-room TV."""
from fast_route import normalize
from pathlib import Path
import subprocess
CUSTOM={"RS TV Home":"com.rs.tvhome","RS Family Frame":"com.rs.familyframe"}
TV='__RS_VOICE_TV_ENTITY__'
GROUPS={
 'YouTube AdFree':('ютуб','youtube','you tube','ю туб','ютюб'),
 'OttPlayer':('отт плеер','ott player','ottplayer','оттплеер','отт плейер','айпи тв','iptv'),
 'Netflix':('нетфликс','netflix'),
 'Yle Areena':('yle areena','юле арена','иле арена','уле арена'),
 'Веб-браузер':('браузер','веб браузер','интернет браузер'),
 'RS TV Home':('главное меню телевизора','главное меню','rs tv home','эр эс тв хоум','меню телевизора'),
 'Media Station X':('media station x','медиа стейшн икс','медиа станция икс'),
 'RS Family Frame':('фотографии','семейные фотографии','фоторамку','фоторамка','фотоальбом','rs family frame'),
 'SmartShare':('smartshare','смарт шар'),
 'Screen Share':('трансляцию экрана','трансляцию экрана компьютера','экран компьютера','screen share','скрин шер'),
 'ТВ (LiveTV)':('эфирное тв','эфирное телевидение','телеканалы'),
 'HDMI-1':('hdmi 1','hdmi один','аш ди эм ай один','аш ди эм ай 1'),
 'HDMI-2':('hdmi 2','hdmi два','аш ди эм ай два','аш ди эм ай 2'),
 'HDMI-3':('hdmi 3','hdmi три','аш ди эм ай три','аш ди эм ай 3')
}
ACTIONS={}
for source,names in GROUPS.items():
    for name in names:
        for prefix in ('открой ','запусти ','включи ','покажи ','переключи на ','переключись на '):
            ACTIONS[normalize(prefix+name)]=('select_source',{'source':source})
for phrase in ('телевизор громче','сделай телевизор громче','увеличь громкость телевизора','прибавь громкость телевизора','включи телевизор громче','прибавь звук телевизора'):
    ACTIONS[phrase]=('volume_up',{})
for phrase in ('телевизор тише','сделай телевизор тише','уменьши громкость телевизора','убавь громкость телевизора','сделай звук телевизора тише','убавь звук телевизора'):
    ACTIONS[phrase]=('volume_down',{})
def match(text):
    return ACTIONS.get(normalize(text))
def launch_custom(source):
    app=CUSTOM[source]
    cli=Path.home()/'lg-webos-tools/node_modules/.bin/ares-launch'
    try:
        result=subprocess.run([str(cli),'--device','__RS_TV_DEVICE_ALIAS__',app],capture_output=True,text=True,timeout=18)
        return result.returncode==0 and ('Launched application '+app) in result.stdout
    except (OSError,subprocess.TimeoutExpired):return False
def execute(action,get_state,send,receive,launcher=launch_custom):
    service,data=action
    state=get_state(TV)
    if state.get('state') in ('off','unavailable','unknown','standby',None):
        return False,'Телевизор выключен или недоступен.'
    if service=='select_source':
        sources=state.get('attributes',{}).get('source_list',[])
        if data['source'] not in sources:
            if data['source'] in CUSTOM:
                if launcher(data['source']):return True,'Открываю '+data['source']+'.'
                return False,'Не удалось подтвердить запуск приложения.'
            return False,'Этот источник сейчас недоступен.'
    send({'id':2,'type':'call_service','domain':'media_player','service':service,'target':{'entity_id':TV},'service_data':data})
    for _ in range(50):
        msg=receive()
        if msg.get('id')==2 and msg.get('type')=='result':
            if not msg.get('success'):return False,'Телевизор не принял команду.'
            if service=='select_source':return True,'Открываю '+data['source']+'.'
            return True,'Громкость телевизора изменена.'
    return False,'Ответ телевизора не получен.'
