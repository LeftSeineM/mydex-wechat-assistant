"""Build the native text-wrapper shim with the existing compiler, on D only."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path('D:/Software/WeChatGroupLab/research-tools/native-sender');OUT.mkdir(parents=True,exist_ok=True)
GCC=r'C:/Program Files/mingw64/bin/gcc.exe'
for source,name,extra in [('native_sender.c','wx-native-sender-v1.dll',['-shared']),('send_fixture.c','wx-send-fixture.exe',[])]:
    result=subprocess.run([GCC,'-O2','-Wall','-Wextra','-Werror','-static-libgcc',*extra,str(HERE/source),'-o',str(OUT/name)],capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError(result.stderr)
report={'artifacts':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('wx-native-sender-v1.dll','wx-send-fixture.exe')},
        'sources':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('native_sender.c','native_sender.h','send_fixture.c')},
        'client_delivery_verified':False}
(OUT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
