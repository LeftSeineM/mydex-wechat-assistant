"""Resolve target-group stack RVAs to static unwind functions on disk."""
from bisect import bisect_right
import hashlib,json,struct,subprocess
from pathlib import Path
import lief
from run_native_observer import CLIENT,EXPECTED_SHA256,ROOT
data=CLIENT.read_bytes()
if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:raise ValueError('Client changed')
pe=lief.PE.parse(str(CLIENT));base=pe.optional_header.imagebase
s=next(s for s in pe.sections if s.name=='.pdata')
raw=data[s.pointerto_raw_data:s.pointerto_raw_data+s.sizeof_raw_data]
functions=sorted((a,b) for a,b,_ in struct.iter_unpack('<III',raw[:len(raw)//12*12]) if a and b>a)
starts=[a for a,b in functions]
report=json.loads((ROOT/'.local/native-trace.json').read_text(encoding='utf-8'))
folder=ROOT/'.local/send-callers';folder.mkdir(exist_ok=True)
result=[]
for stack in report.get('call_stacks',[]):
    for value in stack['rvas']:
        rva=int(value,16);index=bisect_right(starts,rva)-1
        if index<0 or not functions[index][0]<=rva<functions[index][1]:continue
        begin,end=functions[index]
        record={'return_rva':value,'function_rva':hex(begin),'end_rva':hex(end),'size':end-begin}
        filename=folder/(hex(begin)+'.asm')
        if not filename.exists():
            output=subprocess.run([r'C:/Program Files/mingw64/bin/objdump.exe','-d','-M','intel',
                 '--start-address='+hex(base+begin),'--stop-address='+hex(base+end),str(CLIENT)],
                 text=True,capture_output=True,timeout=30,check=True).stdout
            filename.write_text(output,encoding='utf-8')
        result.append(record)
(folder/'resolved.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
