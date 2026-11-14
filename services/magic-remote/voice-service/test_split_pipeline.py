from collections import deque
from split_pipeline import run
from fast_route import answer
def state(e):return {'state':'26.25','attributes':{'unit_of_measurement':'°C'}}
assert '26,2' in answer('Какая температура в сауне?',state)
assert answer('Включи свет на кухне',state) is None
assert answer('Какая температура в сауне и выключи свет',state) is None
assert answer('Сауна готова?',lambda e:{'state':'off'})=='Сауна пока не готова.'
assert answer('Какая температура в сауне?',lambda e:{'state':'unavailable','attributes':{'unit_of_measurement':'°C'}}) is None
def ev(i,k,d=None):return dict(id=i,type='event',event={'type':k,'data':d or {}})
def trial(text,extra):
    q=deque([ev(1,'run-start',{'runner_data':{'stt_binary_handler_id':5}}),ev(1,'stt-start'),ev(1,'stt-end',{'stt_output':{'text':text}}),ev(1,'run-end')]+extra)
    req=[];audio=[]
    r=run(req.append,q.popleft,audio.append,bytes(640),'test',state)
    assert b''.join(x[1:] for x in audio[:-1])==bytes(640)
    return r,req
r,req=trial('Какая температура в сауне?',[])
assert r['route']=='fast' and r['intent_ok'] and len(req)==1
r,req=trial('Включи свет на кухне',[ev(2,'intent-end',{'processed_locally':False,'intent_output':{'response':{'response_type':'action_done','speech':{'plain':{'speech':'Готово'}}}}}),ev(2,'run-end')])
assert r['route']=='rs_ai' and len(req)==2 and req[1]['input']['text']=='Включи свет на кухне'
r,req=trial('Включи свет на кухне',[ev(2,'error',{'code':'timeout'})])
assert len(req)==2 and r['error']=='timeout' and not r['intent_ok']
print('SPLIT_FAST_ROUTE_TEST_OK')
