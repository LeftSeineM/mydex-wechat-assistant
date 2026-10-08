"""Read only minidump exception/module/context metadata. No memory streams.
Does not copy/upload the dump or read chat text, credentials or database keys.
"""
import argparse,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('path');args=parser.parse_args()
path=Path(args.path).resolve(strict=True)
allowed=Path(r'C:/Users/ExampleUser/AppData/Roaming/Tencent/xwechat/crashinfo/reports').resolve()
if path.parent!=allowed or path.suffix.lower()!='.dmp' or not path.name.startswith('Weixin_'):
    raise ValueError('Not a known local Weixin crash report')
with path.open('rb') as stream:
    def read(offset,size):
        if size>200000:raise ValueError('Metadata bound')
        stream.seek(offset);value=stream.read(size)
        if len(value)!=size:raise ValueError('Incomplete metadata')
        return value
    header=read(0,32)
    if header[:4]!=b'MDMP':raise ValueError('Not minidump')
    count,table=struct.unpack_from('<II',header,8)
    if count>128:raise ValueError('Too many streams')
    entries={kind:(size,rva) for kind,size,rva in struct.iter_unpack('<III',read(table,count*12))}
    modules=[]
    if 4 in entries:
        _,offset=entries[4];number=struct.unpack('<I',read(offset,4))[0]
        if number>1000:raise ValueError('Too many modules')
        for i in range(number):
            record=read(offset+4+i*108,108)
            base,size,checksum,stamp,name=struct.unpack_from('<QIIII',record)
            length=struct.unpack('<I',read(name,4))[0]
            if length>2048:raise ValueError('Module name too long')
            filename=read(name+4,length).decode('utf-16-le')
            modules.append((base,size,Path(filename).name))
    def location(address):
        for base,size,name in modules:
            if base<=address<base+size:return {'module':name,'rva':hex(address-base)}
        return {'null':address==0,'below_64k':address<65536}
    report={'filename':path.name,'file_modified':path.stat().st_mtime,'memory_streams_read':False}
    if 6 in entries:
        size,offset=entries[6]
        if size<168:raise ValueError('Exception metadata too short')
        record=read(offset,168)
        tid=struct.unpack_from('<I',record,0)[0];code,flags=struct.unpack_from('<II',record,8)
        address=struct.unpack_from('<Q',record,24)[0];parameters=struct.unpack_from('<I',record,32)[0]
        info=struct.unpack_from('<15Q',record,40);context_size,context_offset=struct.unpack_from('<II',record,160)
        report.update(thread_id=tid,exception_code=hex(code),exception_location=location(address),
                      access_type=info[0] if code==0xc0000005 and parameters>=2 else None,
                      access_location=location(info[1]) if code==0xc0000005 and parameters>=2 else None)
        if context_size>=256:
            context=read(context_offset,256)
            report['register_locations']={name:location(struct.unpack_from('<Q',context,off)[0]) for name,off in
                [('rax',120),('rcx',128),('rdx',136),('rbx',144),('rsp',152),('rbp',160),('rsi',168),('rdi',176),('r8',184),('r9',192),('rip',248)]}
    (ROOT/'.local/crash-metadata.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
