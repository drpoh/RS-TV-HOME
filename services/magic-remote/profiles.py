"""Personal calibration and allowlisted shortcut destinations."""
PROFILE={'gain':42.,'sweep':280,'smoothing':95,'deadzone':12,'xaxis':3,'yaxis':1,'pointer':True,'acceleration':True,'auto_bias':True}
RANGES={'gain':(24,60),'sweep':(160,400),'smoothing':(90,100),'deadzone':(4,20)}
SPECIAL=('NETFLIX','MOVIES','PRIME','RED','GREEN','YELLOW','BLUE')
APPS={'netflix':('Netflix','netflix'),'ott':('OTT Player','es.ottplayer.widget'),'youtube':('YouTube','youtube.leanback.v4'),'home':('RS TV Home','com.rs.tvhome'),'magic':('Калибровка пульта','com.rs.magicremote'),'msx':('Media Station X','de.benzac.msx'),'yle':('YLE Areena','fi.yle.areena'),'live':('Эфирное ТВ','com.webos.app.livetv'),'gallery':('Gallery3D','me.mariotaku.gallery3d'),'vk':('VK Видео','vkvideo'),'rutube':('Rutube','rutube')}
SHORTCUT_DEFAULTS={'NETFLIX':'netflix','MOVIES':'none','PRIME':'none','RED':'native','GREEN':'native','YELLOW':'native','BLUE':'native'}
def allowed(slot,target):
    return slot in SPECIAL and (target in APPS or target=='none' or (target=='native' and slot in SPECIAL[3:]))
def motion_of(settings):
    return {k:settings[k] for k in PROFILE}
