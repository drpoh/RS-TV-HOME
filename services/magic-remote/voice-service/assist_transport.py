"""Offline-tested Assist STT adapter; no microphone access or automatic commands."""
import json
import wave
import time
MAX_BYTES = 16000 * 2 * 15

def pcm_from_wav(path):
    with wave.open(str(path), 'rb') as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1,2,16000):
            raise ValueError('Need mono signed 16-bit PCM at 16000 Hz')
        if not 0 < w.getnframes() <= 16000*15:
            raise ValueError('Audio duration invalid')
        return w.readframes(w.getnframes())

def transcribe(send_json, recv_json, send_binary, pcm, pipeline=None, *, trace=None, pace=True):
    """Use a dedicated, already authenticated HA websocket, with receive timeout.
    STT only: never execute an intent. PCM must be decoded and verified first.
    """
    if not isinstance(pcm,bytes) or not 0<len(pcm)<=MAX_BYTES or len(pcm)%2:
        raise ValueError('Invalid PCM length')
    cmd={'id':1,'type':'assist_pipeline/run','start_stage':'stt',
         'end_stage':'stt','input':{'sample_rate':16000,'no_vad':True},'timeout':120}
    history=[] if trace is None else trace
    if pipeline:cmd['pipeline']=pipeline
    send_json(cmd)
    handler=None;sent=False;text=None;started=time.monotonic();ended=False
    for _ in range(100):
        try:msg=recv_json()
        except Exception as exc:
            if ended:raise RuntimeError('Pipeline ended without STT text') from exc
            raise
        if msg.get('id')!=1:continue
        if msg.get('type')=='result' and not msg.get('success'):
            raise RuntimeError('Pipeline rejected: '+str(msg.get('error',{}).get('code','unknown')))
        if msg.get('type')!='event':continue
        e=msg.get('event',{});kind=e.get('type');data=e.get('data',{})
        history.append({'type':kind,'data_keys':sorted((data or {}).keys()),'elapsed_s':round(time.monotonic()-started,2)})
        print('HA_EVENT:',kind,flush=True)
        if kind=='error':raise RuntimeError('Assist STT failed: '+str((data or {}).get('code','unknown')))
        if kind=='run-start':
            handler=data['runner_data']['stt_binary_handler_id']
            if type(handler)!=int or not 0<=handler<=255:raise ValueError('Invalid handler')
        elif kind=='stt-start' and not sent:
            if handler is None:raise RuntimeError('Missing handler')
            prefix=bytes([handler])
            begin=time.monotonic()
            for i in range(0,len(pcm),320):
                if pace:
                    delay=begin+i/32000-time.monotonic()
                    if delay>0:time.sleep(delay)
                send_binary(prefix+pcm[i:i+320])
            history.append({'type':'audio-sent','bytes':len(pcm)})
            send_binary(prefix);sent=True
        elif kind=='stt-end':
            text=(data or {}).get('stt_output',{}).get('text')
            history[-1]['text_present']=isinstance(text,str)
            history[-1]['text_length']=len(text) if isinstance(text,str) else 0
        elif kind=='run-end':
            if sent and isinstance(text,str):return text
            ended=True
    raise RuntimeError('Too many pipeline events')
