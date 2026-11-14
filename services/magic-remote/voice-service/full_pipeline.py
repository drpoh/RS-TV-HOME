"""Single Assist run per deliberate PTT. Never replay a failed command."""
import time

def run(send_json, receive, send_binary, pcm, pipeline, progress=lambda phase:None, pace=True):
    if not isinstance(pcm,bytes) or not 0<len(pcm)<=256000 or len(pcm)%2:
        raise ValueError('Invalid capture')
    send_json({'id':1,'type':'assist_pipeline/run','start_stage':'stt','end_stage':'intent','pipeline':pipeline,'input':{'sample_rate':16000,'no_vad':True},'timeout':120})
    result={'stt_ok':False,'intent_completed':False,'intent_ok':False,'tts_ready':False,'reply':'','error':''}
    handler=None; sent=False
    started=time.monotonic()
    deadline=started+125
    for _ in range(500):
        if time.monotonic()>deadline:raise RuntimeError('Pipeline timeout')
        msg=receive()
        if msg.get('id')!=1:continue
        if msg.get('type')=='result' and not msg.get('success'):
            raise RuntimeError('Pipeline rejected')
        if msg.get('type')!='event':continue
        event=msg.get('event',{});kind=event.get('type');d=event.get('data') or {}
        if kind=='run-start':
            handler=d.get('runner_data',{}).get('stt_binary_handler_id')
        elif kind=='stt-start' and not sent:
            if type(handler)!=int or not 0<=handler<=255:raise RuntimeError('Invalid audio handler')
            prefix=bytes([handler]);begin=time.monotonic()
            for i in range(0,len(pcm),320):
                if pace:
                    delay=begin+i/32000-time.monotonic()
                    if delay>0:time.sleep(delay)
                send_binary(prefix+pcm[i:i+320])
            send_binary(prefix);sent=True
            result['upload_seconds']=round(time.monotonic()-begin,3)
            result['audio_seconds']=round(len(pcm)/32000,3)
            result['audio_bytes']=len(pcm)
        elif kind=='stt-end':
            result['stt_ok']=bool(d.get('stt_output',{}).get('text','').strip())
            result['stt_seconds']=round(time.monotonic()-started,2)
        elif kind=='intent-start':progress('processing')
        elif kind=='intent-end':
            output=d.get('intent_output') or {}
            response=output.get('response') or {}
            result['intent_completed']=True
            local=d.get('processed_locally')
            result['processed_locally']=local if isinstance(local,bool) else None
            result['route']='local' if local is True else 'rs_ai' if local is False else 'unknown'
            result['intent_seconds']=round(time.monotonic()-started,2)
            result['intent_ok']=response.get('response_type') in ('action_done','query_answer')
            speech=(response.get('speech') or {}).get('plain') or {}
            result['reply']=str(speech.get('speech') or '')[:500]
        elif kind=='tts-start':progress('synthesizing')
        elif kind=='tts-end':
            result['tts_ready']=bool((d.get('tts_output') or {}).get('url'))
        elif kind=='error':
            result['error']=str(d.get('code','pipeline_error'))[:80]
            return result
        elif kind=='run-end':return result
    raise RuntimeError('Pipeline event limit')

def notify_tv(send_json,receive,text):
    if not isinstance(text,str) or not text.strip():return False
    send_json({'id':4,'type':'call_service','domain':'notify','service':'__RS_VOICE_TV_NOTIFY__','service_data':{'message':text[:250]}})
    for _ in range(40):
        r=receive()
        if r.get('id')==4 and r.get('type')=='result':return bool(r.get('success'))
    return False


SPEAKER='__RS_VOICE_SPEAKER__'
def speak_yandex(send_json,receive,text):
    # Use speech mode, never execute the text as an Alice command.
    if not isinstance(text,str) or not text.strip():return False
    text=' '.join(text.replace('<',' ').replace('>',' ').split())[:500]
    send_json({'id':3,'type':'call_service','domain':'media_player','service':'play_media','target':{'entity_id':SPEAKER},'service_data':{'media_content_type':'text','media_content_id':text}})
    for _ in range(40):
        r=receive()
        if r.get('id')==3 and r.get('type')=='result':return bool(r.get('success'))
    return False

def notify_tv_diagnostic(send_json,receive,text,get_state):
    if not isinstance(text,str) or not text.strip():return False,'empty_reply'
    try:
        state=get_state('__RS_VOICE_TV_ENTITY__').get('state')
        if state in ('off','unavailable','unknown','standby'):
            return False,'tv_'+state
    except Exception:
        pass
    send_json({'id':4,'type':'call_service','domain':'notify','service':'__RS_VOICE_TV_NOTIFY__','service_data':{'message':text[:250]}})
    for _ in range(40):
        r=receive()
        if r.get('id')==4 and r.get('type')=='result':
            if r.get('success'):return True,'ok'
            code=str((r.get('error') or {}).get('code','failed'))
            if not code.replace('_','').replace('-','').isalnum():code='failed'
            return False,code[:60]
    return False,'no_result'
