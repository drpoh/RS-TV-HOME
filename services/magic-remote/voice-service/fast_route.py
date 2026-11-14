"""Exact-match read-only fast path; never guesses a device or changes its state."""
import re,math,unicodedata
TEMP='__RS_SAUNA_ENTITY__'
READY='__RS_VOICE_SAUNA_READY__'
def normalize(s):
    s=unicodedata.normalize('NFKC',s).casefold().replace('ё','е')
    return re.sub(r'\s+',' ',re.sub(r'[?!.,;:]+',' ',s)).strip()
def answer(text,get_state):
    s=normalize(text)
    if s in {'какая температура в сауне','какая температура в сауна','какая температура сауна','какая температура сауны','температура сауны','температура в сауне','сколько градусов в сауне','сколько градусов в сауна','сколько градусов сауна','сколько градусов в сауне сейчас','какая сейчас температура в сауне'}:
        d=get_state(TEMP)
        if d.get('attributes',{}).get('unit_of_measurement')!='°C':return None
        try:v=float(d['state'])
        except (ValueError,KeyError,TypeError):return None
        if not math.isfinite(v) or not -40<=v<=150:return None
        return 'Температура в сауне: '+str(round(v,1)).replace('.',',')+' градуса.'
    if s in {'сауна готова','готова ли сауна','готова сауна','сауна уже готова','готова ли уже сауна'}:
        d=get_state(READY)
        if d.get('state')=='on':return 'Сауна готова.'
        if d.get('state')=='off':return 'Сауна пока не готова.'
    return None
