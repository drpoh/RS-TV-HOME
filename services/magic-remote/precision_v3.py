"""Gain curve with independent aiming and sweep speed; immediate stop."""
import math

class Precision:
    def __init__(self):
        self.reset()
    def reset(self):
        self.filtered=[0.,0.]
        self.frac=[0.,0.]
        self.active=False
        self.quiet=0.
        self.emit_cap=115
    def sample(self,x,y,dt,gain,deadzone,smoothing,acceleration,sweep=180):
        dt=max(.002,min(.025,dt))
        mag=math.hypot(x,y)
        if mag < deadzone*(.65 if self.active else 1.):
            self.quiet+=dt
            self.filtered=[v*.3 for v in self.filtered]
            self.frac=[0.,0.]
            if self.quiet>=.030:self.reset()
            return (0.,0.)
        self.active=True;self.quiet=0.
        scale=max(0.,1-deadzone*.65/max(mag,1.))
        x*=scale;y*=scale
        speed=math.hypot(x,y)
        # Fast gestures follow the raw signal with very little lag.
        tau=(.010+.070*smoothing/100.)/(1+(speed/350.)**1.4)
        alpha=1-math.exp(-dt/max(.001,tau))
        for i,v in enumerate((x,y)):
            if v*self.filtered[i]<0:
                self.filtered[i]*=.12;self.frac[i]=0.
            self.filtered[i]+=alpha*(v-self.filtered[i])
        speed=math.hypot(*self.filtered)
        # At low speed the aiming control is dominant. At high speed
        # its influence vanishes and the separate sweep setting takes over.
        t=max(0.,min(1.,(speed-140.)/1050.))
        t=t*t*(3-2*t) if acceleration else 0.
        slow=gain*.065
        fast=4.5*sweep/100.
        ratio=slow*(1-t)+fast*t
        vx,vy=(v*ratio for v in self.filtered)
        norm=math.hypot(vx,vy)
        limit=(min(11000.,5200.*sweep/100.)+max(0.,sweep-220.)*38.) if acceleration else 4200.
        self.emit_cap=115+int(max(0.,sweep-220.)*.38) if acceleration else 115
        if norm>limit:
            vx*=limit/norm;vy*=limit/norm
        return vx*dt,vy*dt
    def emit(self,dx,dy):
        result=[]
        for i,v in enumerate((dx,dy)):
            v+=self.frac[i];n=int(v);self.frac[i]=v-n
            result.append(max(-self.emit_cap,min(self.emit_cap,n)))
        return tuple(result)
