"""Read Qt metaobjects in the pinned client binary; no process interaction."""
import hashlib,json,struct,sys
from pathlib import Path
import lief
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe_native import CLIENT,EXPECTED_SHA256

def main():
    blob=CLIENT.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=EXPECTED_SHA256:raise ValueError('Client changed')
    pe=lief.PE.parse(str(CLIENT));base=pe.optional_header.imagebase
    def raw(rva,size):
        for s in pe.sections:
            if s.virtual_address<=rva and rva+size<=s.virtual_address+s.sizeof_raw_data:
                p=s.pointerto_raw_data+rva-s.virtual_address
                return blob[p:p+size]
        raise ValueError('Outside file')
    def rva(offset):
        for s in pe.sections:
            if s.pointerto_raw_data<=offset<s.pointerto_raw_data+s.sizeof_raw_data:
                return s.virtual_address+offset-s.pointerto_raw_data
        raise ValueError('Outside section')
    results=[]
    for name in ('mmui::ChatInputView','mmui::MessageView'):
        term=name.encode()+b'\0';pos=blob.find(term)
        while pos>=0:
            string_rva=rva(pos)
            for header in range((string_rva-8)//4*4,max(0,string_rva-8192),-4):
                try:
                    ref,length,alloc,offset=struct.unpack('<iiQq',raw(header,24))
                except ValueError:continue
                if ref!=-1 or header+offset!=string_rva or length!=len(term)-1:continue
                pointer=struct.pack('<Q',base+header);where=blob.find(pointer)
                while where>=0:
                    site=rva(where)
                    if site%8==0:
                        try:
                            metadata,metacall=struct.unpack('<QQ',raw(site+8,16))
                            values=struct.unpack('<14I',raw(metadata-base,56))
                            revision,classname,ci_count,ci_data,method_count,method_data=values[:6]
                            if revision not in (7,8,9,10,11,12,13) or method_count>300:raise ValueError('Not Qt')
                            def text(index):
                                item_address=header+index*24
                                ref,size,alloc,off=struct.unpack('<iiQq',raw(item_address,24))
                                if size>512:raise ValueError('Size')
                                return raw(item_address+off,size).decode('utf-8')
                            methods=[]
                            width=6 if revision>=9 else 5
                            for i in range(method_count):
                                item=struct.unpack('<'+'I'*width,raw(metadata-base+4*(method_data+i*width),4*width))
                                methods.append({'index':i,'name':text(item[0]),'argc':item[1],'parameters_offset':item[2],'flags':item[4]})
                            results.append({'class':name,'string_header':hex(header),'metaobject':hex(site-8),
                                            'metadata':hex(metadata-base),'metacall':hex(metacall-base),
                                            'revision':revision,'methods':methods})
                        except (ValueError,UnicodeDecodeError,struct.error):pass
                    where=blob.find(pointer,where+1)
            pos=blob.find(term,pos+1)
    (ROOT/'.local/quote-qt-meta.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))
if __name__=='__main__':main()
