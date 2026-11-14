"""Bounded, private timing history. No transcripts, audio, or credentials."""
import json
from pathlib import Path

FIELDS=('version','phase','updated','route','processed_locally','stt_ok','intent_ok','intent_completed','speaker_ok','notification_ok','audio_seconds','upload_seconds','stt_seconds','intent_seconds','speaker_seconds','notification_seconds','notification_reason','elapsed','error')
def append_result(path,result):
    path=Path(path)
    try:
        old=json.loads(path.read_text())
    except (OSError,ValueError):
        old=[]
    if not isinstance(old,list):old=[]
    row={k:result[k] for k in FIELDS if k in result}
    # Append at most once per completed capture. Drop any unknown fields.
    rows=[{k:x[k] for k in FIELDS if k in x} for x in old if isinstance(x,dict)]
    rows=(rows+[row])[-100:]
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(rows,ensure_ascii=False))
    tmp.replace(path)
