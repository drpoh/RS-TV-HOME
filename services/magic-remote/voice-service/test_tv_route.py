from tv_route import match,execute,TV
from split_pipeline import run
from collections import deque
for phrase,expected in [('открой ютуб','YouTube AdFree'),('Запусти Netflix','Netflix'),('Покажи семейные фотографии','RS Family Frame'),('Включи трансляцию экрана компьютера','Screen Share'),('Переключи на HDMI 2','HDMI-2')]:
    assert match(phrase)==('select_source',{'source':expected}),phrase
assert match('телевизор громче')==('volume_up',{})
for phrase in ['не открывай ютуб','открой ютуб и выключи свет','громче','включи свет на кухне','выключи телевизор']:
    assert match(phrase) is None,phrase
calls=[]
on=lambda e:{'state':'on','attributes':{'source_list':['Screen Share','YouTube AdFree']}}
assert execute(match('открой ютуб'),on,calls.append,lambda:{'id':2,'type':'result','success':True})[0]
assert len(calls)==1 and calls[0]['target']['entity_id']==TV
assert not execute(match('открой ютуб'),lambda e:{'state':'off'},calls.append,lambda:None)[0]
assert len(calls)==1
assert not execute(match('открой нетфликс'),on,calls.append,lambda:None)[0]
assert len(calls)==1
def ev(k,d=None):return {'id':1,'type':'event','event':{'type':k,'data':d or {}}}
for success in [True,False]:
    q=deque([ev('run-start',{'runner_data':{'stt_binary_handler_id':6}}),ev('stt-start'),ev('stt-end',{'stt_output':{'text':'открой ютуб'}}),ev('run-end'),{'id':2,'type':'result','success':success}])
    calls=[]
    r=run(calls.append,q.popleft,lambda x:None,bytes(640),'test',on)
    assert len(calls)==2 and calls[1]['type']=='call_service'
    assert r['route']=='tv_fast' and r['intent_ok']==success
print('TV_VOICE_OFFLINE_TEST_OK')

assert match('открой smartshare')==('select_source',{'source':'SmartShare'})
assert match('включи фоторамку')==('select_source',{'source':'RS Family Frame'})
