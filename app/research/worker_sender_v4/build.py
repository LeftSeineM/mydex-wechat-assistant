"""Build the native text-wrapper shim with the existing compiler, on D only."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path('D:/Software/WeChatGroupLab/research-tools/worker-sender-v4');OUT.mkdir(parents=True,exist_ok=True)
GCC=r'C:/Program Files/mingw64/bin/gcc.exe'
DEPENDENCY=Path('D:/Software/WeChatGroupLab/research/minhook-v1.3.4')
for source,name,extra in [('native_sender.c','wx-worker-sender-v4.dll',['-shared']),('send_fixture.c','wx-send-fixture.exe',[])]:
    sources=[str(HERE/source)]
    if extra:sources+=[str(DEPENDENCY/'src'/p) for p in ('hook.c','buffer.c','trampoline.c','hde/hde64.c')]
    result=subprocess.run([GCC,'-O2','-Wall','-Wextra','-Werror','-static-libgcc',*extra,'-I'+str(DEPENDENCY/'include'),*sources,'-o',str(OUT/name)],capture_output=True,text=True,timeout=60)
    if result.returncode:raise RuntimeError(result.stderr)
report={'artifacts':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ('wx-worker-sender-v4.dll','wx-send-fixture.exe')},
        'sources':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('native_sender.c','native_sender.h','send_fixture.c')},
        'client_delivery_verified':False}
(OUT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
