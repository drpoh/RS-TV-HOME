from tv_route import match,execute,TV,CUSTOM
calls=[];launches=[]
def launch(source):launches.append(source);return True
def state(entity):
    assert entity==TV
    return {'state':'on','attributes':{'source_list':['YouTube AdFree','Yle Areena','Веб-браузер']}}
for phrase,source in [('включи фоторамку','RS Family Frame'),('открой главное меню','RS TV Home')]:
    assert match(phrase)==('select_source',{'source':source})
    assert execute(match(phrase),state,calls.append,lambda:None,launch)[0]
assert launches==['RS Family Frame','RS TV Home'] and not calls
assert not execute(match('включи фоторамку'),lambda _: {'state':'off'},calls.append,lambda:None,launch)[0]
assert len(launches)==2
assert not execute(match('включи фоторамку'),state,calls.append,lambda:None,lambda _:False)[0]
assert not calls
for phrase,source in [('открой YLE Areena','Yle Areena'),('включи браузер','Веб-браузер')]:
    assert match(phrase)==('select_source',{'source':source})
    assert execute(match(phrase),state,calls.append,lambda:{'id':2,'type':'result','success':True},launch)[0]
assert len(calls)==2 and len(launches)==2
assert match('включи телевизор громче')==('volume_up',{})
assert match('открой фоторамку и выключи свет') is None
print('CUSTOM_APP_ROUTE_TEST_OK')
