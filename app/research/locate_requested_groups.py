"""Read-only candidate locator for exactly two user-requested group names.

No arbitrary memory dump: outputs only matching names and nearby room IDs.
Candidates still require structural/database corroboration before sending.
"""
import json,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from m_session_assistant import check_session
from external_reader import Reader
DATA=ROOT/'.local/quote-m-session'

def main():
    session=json.loads((DATA/'session.json').read_text(encoding='utf-8'));check_session(session)
    terms=['深圳实践','因为我们是无44']
    hits=[];total=0;started=time.monotonic()
    with Reader(session['pid']) as proc:
        for base,size in proc.regions():
            for offset in range(0,size,1046528):
                try:data=proc.read(base+offset,min(1048576,size-offset))
                except OSError:continue
                total+=len(data)
                for term in terms:
                    for encoding in ('utf-8','utf-16-le'):
                        needle=term.encode(encoding);at=data.find(needle)
                        while at>=0:
                            nearby=data[max(0,at-768):min(len(data),at+768)]
                            rooms=sorted(set(m.decode() for m in re.findall(rb'\d{7,15}@chatroom',nearby)))
                            rooms16=sorted(set(m.decode('utf-16-le') for m in re.findall(rb'(?:[0-9]\x00){7,15}@\x00c\x00h\x00a\x00t\x00r\x00o\x00o\x00m\x00',nearby)))
                            hits.append({'term':term,'encoding':encoding,'address':hex(base+offset+at),'nearby_room_candidates':sorted(set(rooms+rooms16))})
                            at=data.find(needle,at+len(needle))
            if total>536870912 or time.monotonic()-started>30:break
    report={'read_only':True,'candidates_not_verified':True,'hits':hits,'read_bytes':total}
    (DATA/'requested-group-candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
