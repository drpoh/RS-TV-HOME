"""Self-contained synthetic pointer tests; no hardware or private profiles."""
from precision_v3 import Precision

def measure(raw, gain=12, sweep=180, n=100):
    p=Precision()
    total=0
    for _ in range(n):
        total+=p.emit(*p.sample(raw,0,.01,gain,20,85,True,sweep))[0]
    return total

assert measure(0)==0
assert measure(10)==0
assert 0<measure(80)<measure(2500)
assert measure(80,sweep=350)==measure(80,sweep=100)
assert measure(2500,sweep=150)==measure(2500,sweep=150,gain=25)
p=Precision()
for _ in range(20):
    p.emit(*p.sample(6000,0,.01,12,20,85,True))
assert all(p.emit(*p.sample(0,0,.01,12,20,85,True))==(0,0) for _ in range(20))
print('V3_SYNTHETIC_TEST_OK')
