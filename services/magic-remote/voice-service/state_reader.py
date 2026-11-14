"""Read only the explicitly allowed entities through the existing local HA session."""
import json,urllib.request
BASE='http://__RS_HA_HOST__:8123/api/states/'
ALLOWED={'__RS_SAUNA_ENTITY__','__RS_VOICE_SAUNA_READY__','__RS_VOICE_TV_ENTITY__'}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def read_state(entity,token):
    if entity not in ALLOWED:raise ValueError('Entity not allowed')
    req=urllib.request.Request(BASE+entity,headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=3) as response:
        value=json.loads(response.read(262144))
    if value.get('entity_id')!=entity:raise ValueError('Unexpected entity')
    return value
