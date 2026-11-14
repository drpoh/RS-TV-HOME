from full_pipeline import run,notify_tv,speak_yandex,SPEAKER
from collections import deque
def ev(k,d=None):return {'id':1,'type':'event','event':{'type':k,'data':d or {}}}
q=deque([ev('run-start',{'runner_data':{'stt_binary_handler_id':4}}),ev('stt-start'),ev('stt-end',{'stt_output':{'text':'Температура'}}),ev('intent-start'),ev('intent-end',{'intent_output':{'response':{'response_type':'query_answer','speech':{'plain':{'speech':'Ответ'}}}}}),ev('run-end')])
commands=[];audio=[];phases=[]
r=run(commands.append,q.popleft,audio.append,bytes(640),'test',phases.append,pace=False)
assert r['stt_ok'] and r['intent_ok'] and not r['tts_ready'] and r['reply']=='Ответ'
assert len(commands)==1 and commands[0]['end_stage']=='intent'
assert audio[-1]==b'\x04' and phases==['processing']
assert notify_tv(commands.append,lambda:{'id':4,'type':'result','success':True},r['reply'])
assert commands[-1]['service']=='__RS_VOICE_TV_NOTIFY__'
q=deque([ev('intent-end',{'intent_output':{'response':{'response_type':'action_done'}}}),ev('error',{'code':'tts-failed'})])
r=run(commands.append,q.popleft,audio.append,bytes(640),'test',pace=False)
assert r['intent_ok'] and not r['tts_ready'] and r['error']=='tts-failed'
print('FULL_PIPELINE_OFFLINE_TEST_OK')

assert speak_yandex(commands.append,lambda:{'id':3,'type':'result','success':True},'Голосовой ответ')
assert commands[-1]['target']['entity_id']==SPEAKER
assert commands[-1]['service_data']['media_content_type']=='text'
assert commands[-1]['service_data']['media_content_id']=='Голосовой ответ'
assert not speak_yandex(commands.append,lambda:{'id':3,'type':'result','success':False},'Проверка')
print('YANDEX_OUTPUT_OFFLINE_TEST_OK')

commands=[]
assert speak_yandex(commands.append,lambda:{'id':3,'type':'result','success':True},'Ответ')
assert notify_tv(commands.append,lambda:{'id':4,'type':'result','success':True},'Ответ')
assert [x['id'] for x in commands]==[3,4]
print('REQUEST_ORDER_TEST_OK')

# All PCM bytes must arrive in order, without the former real-time delay.
pcm=bytes(range(256))*125
audio=[]
q=deque([ev('run-start',{'runner_data':{'stt_binary_handler_id':4}}),ev('stt-start'),ev('stt-end',{'stt_output':{'text':'тест'}}),ev('run-end')])
r=run(lambda x:None,q.popleft,audio.append,pcm,'test',pace=False)
assert b''.join(x[1:] for x in audio[:-1])==pcm
assert all(x[:1]==bytes([4]) for x in audio)
assert audio[-1]==bytes([4])
assert r['audio_bytes']==len(pcm)
assert r['audio_seconds']==1
print('BUFFERED_UPLOAD_TEST_OK',r['upload_seconds'])

for local,expected in [(True,'local'),(False,'rs_ai'),(None,'unknown')]:
    payload={'intent_output':{'response':{'response_type':'query_answer','speech':{'plain':{'speech':'Ответ'}}}}}
    if local is not None:payload['processed_locally']=local
    q=deque([ev('run-start',{'runner_data':{'stt_binary_handler_id':4}}),ev('stt-start'),ev('stt-end',{'stt_output':{'text':'тест'}}),ev('intent-end',payload),ev('run-end')])
    requests=[]
    r=run(requests.append,q.popleft,lambda x:None,bytes(640),'hybrid',pace=False)
    assert len(requests)==1 and requests[0]['pipeline']=='hybrid'
    assert r['route']==expected and r['intent_ok']
print('HYBRID_ROUTE_TEST_OK')
