"""Inspect only the requested member's record inside the selected room blob."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.history_vfs import HistoryView
needle=b'wxid_example000001'
def varint(data,pos):
    value=0
    for shift in range(0,70,7):
        if pos>=len(data):raise ValueError('EOF')
        byte=data[pos];pos+=1;value|=(byte&127)<<shift
        if not byte&128:return value,pos
    raise ValueError('varint')
def fields(data):
    pos=0;items=[]
    while pos<len(data):
        key,pos=varint(data,pos);number,wire=key>>3,key&7
        if not number:raise ValueError('field')
        if wire==0:value,pos=varint(data,pos)
        elif wire==2:
            size,pos=varint(data,pos)
            if size>len(data)-pos:raise ValueError('size')
            value=data[pos:pos+size];pos+=size
        elif wire in (1,5):
            size=8 if wire==1 else 4
            if size>len(data)-pos:raise ValueError('size')
            value=data[pos:pos+size];pos+=size
        else:raise ValueError('wire')
        items.append((number,wire,value))
    return items
def containing(data,path=(),depth=0):
    if depth>8:return []
    try:items=fields(data)
    except ValueError:return []
    children=[]
    for number,wire,value in items:
        if wire==2 and needle in value and value!=needle:
            children+=containing(value,path+(number,),depth+1)
    if children:return children
    if any(w==2 and v==needle for _,w,v in items):
        texts=[]
        for n,w,v in items:
            if w==2 and len(v)<512:
                try:texts.append([n,v.decode('utf-8')])
                except UnicodeDecodeError:pass
        return [{'path':path,'fields':texts}]
    return []
r=TargetHistory(group="示例朋友群");path=next(p for p in r.keys if Path(p).name=='contact.db');key,salt=r.keys[path]
with HistoryView(path,key,salt) as view:
    row=view.query('SELECT ext_buffer FROM chat_room WHERE username=?',(r.room,))
    blob=row[0][0] if row else b''
    if not isinstance(blob,bytes) or len(blob)>2097152:raise ValueError('Unexpected group blob')
    result={'bytes':len(blob),'requested_member':containing(blob)}
(ROOT/'.local/requested-member-nickname.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
