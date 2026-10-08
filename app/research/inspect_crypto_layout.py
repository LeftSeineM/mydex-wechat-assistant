"""On-disk complete-function extraction for the current crypto layout only."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import lief
from run_native_observer import CLIENT,EXPECTED_SHA256,ROOT
TARGETS=[0x1124b20,0x356b240,0x15de230,0x3569650,0x3569360,
         0x58325d0,0x5832530,0x5832400,0x58327a0,0x5832920]
data=CLIENT.read_bytes()
if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:raise ValueError('Unsupported build')
pe=lief.PE.parse(str(CLIENT));base=pe.optional_header.imagebase
pdata=next(s for s in pe.sections if s.name=='.pdata')
raw=data[pdata.pointerto_raw_data:pdata.pointerto_raw_data+pdata.sizeof_raw_data]
functions={a:b for a,b,_ in struct.iter_unpack('<III',raw[:len(raw)//12*12]) if a and b>a}
out=ROOT/'.local/crypto-static';out.mkdir(exist_ok=True);records=[]
for start in TARGETS:
    if start not in functions:
        # Review fixed 96-byte windows for leaf candidates, never execution.
        end=start+96;boundary='leaf_candidate_window'
    else:end=functions[start];boundary='pe_unwind'
    asm=subprocess.run([r'C:\Program Files\mingw64\bin\objdump.exe','-d','-M','intel',
                       '--start-address='+hex(base+start),'--stop-address='+hex(base+end),str(CLIENT)],
                       capture_output=True,text=True,check=True,timeout=30).stdout
    (out/(hex(start)+'.asm')).write_text(asm,encoding='utf-8')
    records.append({'rva':hex(start),'end':hex(end),'boundary':boundary})
(out/'profile.json').write_text(json.dumps({'client_sha256':EXPECTED_SHA256,'on_disk_only':True,'functions':records},indent=2),encoding='utf-8')
print(json.dumps(records))
