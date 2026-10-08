"""Decode only the two requested contact records in current client page cache.

SQLite record column order is from this version's previously authenticated
contact schema. Nearby unrelated strings are never treated as associations.
"""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from m_session_assistant import check_session
from external_reader import Reader
DATA=ROOT/'.local/quote-m-session'

def varint(data,pos):
    value=0
    for i in range(9):
        b=data[pos];pos+=1
        if i==8:return (value<<8)|b,pos
        value=(value<<7)|(b&127)
        if b<128:return value,pos
    raise ValueError('Varint')

def contact_record(data,start):
    header,pos=varint(data,start)
    if not 23<=header<=128 or start+header>len(data):raise ValueError('Header')
    serial=[]
    while pos<start+header:
        value,pos=varint(data,pos);serial.append(value)
    if pos!=start+header or len(serial)!=22 or serial[0]!=0:raise ValueError('Contact schema')
    if serial[1]<13 or serial[1]%2!=1 or serial[11]<13 or serial[11]%2!=1:raise ValueError('Types')
    body=start+header;values={}
    for index,kind in enumerate(serial):
        size={0:0,1:1,2:2,3:3,4:4,5:6,6:8,7:8,8:0,9:0}.get(kind,(kind-12)//2 if kind>=12 else -1)
        if size<0 or size>1048576:raise ValueError('Field size')
        if index in (1,11,18):
            if body+size>len(data):raise ValueError('Truncated')
            chunk=data[body:body+size]
            values[index]=chunk.decode('utf-8') if kind>=13 and kind%2 else (kind-8 if kind in (8,9) else int.from_bytes(chunk,'big',signed=True))
        body+=size
    if not re.fullmatch(r'\d{7,15}@chatroom',str(values[1])) or values[18]!=1:raise ValueError('Not joined group')
    if not ('深圳实践' in str(values[11]) or str(values[11]).startswith('因为我们是无44')):raise ValueError('Not requested')
    return {'room_id':values[1],'name':values[11],'is_in_chat_room':True,'record_size':body-start}

def main():
    session=json.loads((DATA/'session.json').read_text(encoding='utf-8'));check_session(session)
    hits=json.loads((DATA/'requested-group-candidates.json').read_text(encoding='utf-8'))['hits'];records=[];seen=set()
    with Reader(session['pid']) as process:
        for hit in hits:
            if hit['encoding']!='utf-8':continue
            address=int(hit['address'],16)
            try:data=process.read(address-2048,12288)
            except OSError:continue
            for start in range(2048):
                try:record=contact_record(data,start)
                except (ValueError,IndexError,UnicodeDecodeError):continue
                origin=address-2048+start
                if origin in seen:continue
                seen.add(origin);records.append({**record,'record_address':hex(origin)})
    report={'pid':session['pid'],'process_created':session['created'],
            'account_root':session['account_roots'][0],'source':'decoded_current_client_contact_cache',
            'records':records,'other_contact_fields_exported':False}
    (DATA/'requested-contact-cache.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
