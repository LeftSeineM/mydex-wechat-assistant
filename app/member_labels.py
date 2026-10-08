"""Group-scoped display labels. Raw identifiers remain internal to storage."""
import json
from pathlib import Path
import re
import threading
from lab import DATA
_lock=threading.Lock();_stamp=None;_cache={}
def labels(room,data=DATA):
    global _stamp,_cache
    path=Path(data)/'member-labels.json'
    try:stamp=(str(path),path.stat().st_mtime_ns)
    except OSError:return {}
    with _lock:
        if stamp!=_stamp:
            value=json.loads(path.read_text(encoding='utf-8'));cache={}
            for g in value['groups']:
                for name in g['aliases']:cache[name]=g['labels']
            _cache=cache;_stamp=stamp
        return _cache.get(room,{})
def display_sender(sender,room,data=DATA):
    if not sender.startswith('wxid_'):return sender
    return labels(room,data).get(sender,'一位群友')
def prettify_reply(text,room,data=DATA):
    return re.sub(r'@?wxid_[A-Za-z0-9]+',lambda m:display_sender(m.group(0).lstrip('@'),room,data),text)

def varint(data,pos):
    value=0
    for shift in range(0,70,7):
        if pos>=len(data):raise ValueError('EOF')
        byte=data[pos];pos+=1;value|=(byte&127)<<shift
        if not byte&128:return value,pos
    raise ValueError('Varint')
def fields(data):
    pos=0;items=[]
    while pos<len(data):
        key,pos=varint(data,pos);number,wire=key>>3,key&7
        if not number:raise ValueError('Field')
        if wire==0:value,pos=varint(data,pos)
        elif wire==2:
            size,pos=varint(data,pos)
            if size>len(data)-pos:raise ValueError('Size')
            value=data[pos:pos+size];pos+=size
        elif wire in (1,5):
            size=8 if wire==1 else 4
            if size>len(data)-pos:raise ValueError('Size')
            value=data[pos:pos+size];pos+=size
        else:raise ValueError('Wire')
        items.append((number,wire,value))
    return items
def group_nicknames(blob):
    if not isinstance(blob,bytes) or len(blob)>2097152:raise ValueError('Group blob bound')
    result={}
    def walk(value,depth=0):
        if depth>8:return
        try:items=fields(value)
        except ValueError:return
        strings={}
        for n,w,v in items:
            if w==2 and len(v)<=512:
                try:strings[n]=v.decode('utf-8')
                except UnicodeDecodeError:pass
        if re.fullmatch(r'wxid_[A-Za-z0-9]+',strings.get(1,'')) and strings.get(2,'').strip():
            result[strings[1]]=' '.join(strings[2].split())[:128]
            return
        for _,wire,value in items:
            if wire==2:walk(value,depth+1)
    walk(blob);return result
