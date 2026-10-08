"""Recheck key reverse-engineering claims against disk bytes, never a process."""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from probe_native import CLIENT,EXPECTED_SHA256
import lief

data=CLIENT.read_bytes()
if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:raise ValueError('Client build changed')
pe=lief.PE.parse(str(CLIENT));base=pe.optional_header.imagebase

def read(rva,size):
    section=next(s for s in pe.sections if s.virtual_address<=rva and rva+size<=s.virtual_address+s.sizeof_raw_data)
    offset=section.pointerto_raw_data+rva-section.virtual_address
    return data[offset:offset+size]

checks=[]
def expect(name,rva,value):
    if read(rva,len(value))!=value:raise AssertionError(name+' mismatch at '+hex(rva))
    checks.append({'claim':name,'evidence_rva':hex(rva),'expected_hex':value.hex(),'passed':True})

for site,target in [(0x6f4cc6,0x766680),(0x7666aa,0x766780),
                    (0x54b1eae,0x178f040),(0x178f08c,0x178f100),
                    (0x178f1ea,0x3981a30),(0x178f234,0x1793050),
                    (0x178f241,0x1793c90),(0x1794716,0x17f3750),
                    (0x18523cf,0x17f7a00),(0x106fdaf,0x2e7d0e0),
                    (0x106fed8,0x67ab70),(0x2e7cc94,0x67ab70)]:
    expect('direct call to '+hex(target),site,b'\xe8'+struct.pack('<i',target-site-5))

for name,rva,code in [
    ('shared allocation size 0x7a8',0x6f4c88,'b9a8070000'),
    ('object zero-fill size 0x798',0x6f4cb2,'41b898070000'),
    ('text type field +0x118 set to 1',0x54b042d,'c7801801000001000000'),
    ('text string length +0x768 initialized',0x7666ff,'48c7866807000000000000'),
    ('text string capacity +0x770 initialized to 15',0x76670a,'48c786700700000f000000'),
    ('recipient string length +0xc0 initialized',0x766820,'48c781c000000000000000'),
]:expect(name,rva,bytes.fromhex(code))

for rva,literal in [(0x8fc0da8,'micromsg.NewSyncResponse'),(0x93d3d58,'micromsg.CmdList'),
                    (0x93d3cd8,'micromsg.CmdItem'),(0x8e3d0b8,'micromsg.SKBuiltinBuffer_t')]:
    expect('type-name literal '+literal,rva,literal.encode())
for site,target in [(0x8fc0d50,0x1070420),(0x93d3d00,0x2e7d480),
                    (0x93d3c80,0x2e7cea0),(0x8e3d060,0x67ae00),
                    (0x9805978,0x54b1e10)]:
    expect('virtual slot points to '+hex(target),site,struct.pack('<Q',base+target))

profile=json.loads((ROOT/'.local/abi/profile.json').read_text())
if profile['client_sha256']!=EXPECTED_SHA256:raise AssertionError('Stale profile')
for function in profile['functions']:
    code=read(int(function['rva'],16),function['size'])
    if hashlib.sha256(code).hexdigest()!=function['code_sha256']:raise AssertionError('Stale function evidence')
report={'client_sha256':EXPECTED_SHA256,'mode':'static_disk_bytes_only','checks':checks,
        'function_hashes_checked':len(profile['functions']),
        'live_receive_verified':False,'live_send_verified':False,'instrumentation_stability_verified':False}
(ROOT/'.local/abi/verified-findings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'static_assertions_passed':len(checks),'function_hashes_checked':len(profile['functions']),
                  'client_touched':False,'live_channel_verified':False}))
