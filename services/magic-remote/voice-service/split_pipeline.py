"""One STT run, then either a read-only answer or one intent run."""
import time
from fast_route import answer
from tv_route import match,execute
def run(send,receive,binary,pcm,pipeline,get_state,progress=lambda x:None):
    if not isinstance(pcm,bytes) or not 0<len(pcm)<=256000 or len(pcm)%2:raise ValueError('Invalid PCM')
    t=time.monotonic()
    r=dict(stt_ok=False,intent_completed=False,intent_ok=False,tts_ready=False,reply='',error='')
    send(dict(id=1,type='assist_pipeline/run',start_stage='stt',end_stage='stt',pipeline=pipeline,input={'sample_rate':16000,'no_vad':True},timeout=120))
    handler=None;text=None;sent=False
    for _ in range(500):
        m=receive()
        if m.get('id')!=1:continue
        if m.get('type')=='result' and not m.get('success'):raise RuntimeError('STT rejected')
        if m.get('type')!='event':continue
        e=m.get('event',{});k=e.get('type');d=e.get('data') or {}
        if k=='run-start':handler=d.get('runner_data',{}).get('stt_binary_handler_id')
        elif k=='stt-start' and not sent:
            if type(handler)!=int or not 0<=handler<=255:raise RuntimeError('Invalid handler')
            prefix=bytes([handler]);begin=time.monotonic()
            for i in range(0,len(pcm),320):binary(prefix+pcm[i:i+320])
            binary(prefix);sent=True
            r.update(upload_seconds=round(time.monotonic()-begin,3),audio_seconds=round(len(pcm)/32000,3))
        elif k=='stt-end':
            text=d.get('stt_output',{}).get('text')
            r.update(stt_ok=isinstance(text,str) and bool(text.strip()),stt_seconds=round(time.monotonic()-t,2))
        elif k=='error':
            r['error']=str(d.get('code','stt_error'))[:80];return r
        elif k=='run-end':break
    if not sent or not r['stt_ok']:
        r['error']='no_stt_text';return r
    progress('processing')
    try:reply=answer(text,get_state)
    except Exception:reply=None
    if reply is not None:
        r.update(route='fast',processed_locally=True,intent_completed=True,intent_ok=True,reply=reply,intent_seconds=round(time.monotonic()-t,2))
        return r
    action=match(text)
    if action is not None:
        # Once matched, never fall back to RS AI, even if TV outcome is uncertain.
        try:ok,reply=execute(action,get_state,send,receive)
        except Exception:ok,reply=False,'Не удалось подтвердить команду телевизору.'
        r.update(route='tv_fast',processed_locally=True,intent_completed=True,intent_ok=ok,reply=reply,intent_seconds=round(time.monotonic()-t,2),error='' if ok else 'tv_command_unconfirmed')
        return r
    # Exactly one intent execution. Never retry on error or timeout.
    send(dict(id=2,type='assist_pipeline/run',start_stage='intent',end_stage='intent',pipeline=pipeline,input={'text':text},timeout=120))
    for _ in range(500):
        m=receive()
        if m.get('id')!=2:continue
        if m.get('type')=='result' and not m.get('success'):
            r['error']='intent_rejected';return r
        if m.get('type')!='event':continue
        e=m.get('event',{});k=e.get('type');d=e.get('data') or {}
        if k=='intent-end':
            out=d.get('intent_output') or {};resp=out.get('response') or {}
            local=d.get('processed_locally')
            r.update(intent_completed=True,intent_ok=resp.get('response_type') in ('query_answer','action_done'),processed_locally=local if isinstance(local,bool) else None,route='local' if local is True else 'rs_ai' if local is False else 'unknown',intent_seconds=round(time.monotonic()-t,2),reply=str(((resp.get('speech') or {}).get('plain') or {}).get('speech') or '')[:500])
        elif k=='error':
            r['error']=str(d.get('code','intent_error'))[:80];return r
        elif k=='run-end':
            if not r['intent_completed']:r['error']='intent_not_completed'
            return r
    raise RuntimeError('Intent event limit')
