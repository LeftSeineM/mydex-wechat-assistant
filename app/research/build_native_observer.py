"""Build pinned source with existing GCC; all binaries remain under D:/Software."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DEPENDENCY=Path('D:/Software/WeChatGroupLab/research/minhook-v1.3.4')
COMMIT='c3fcafdc10146beb5919319d0683e44e3c30d537'
OUT=Path('D:/Software/WeChatGroupLab/research-tools/native-observer')
GCC=Path('C:/Program Files/mingw64/bin/gcc.exe')
def run(args):
    result=subprocess.run([str(a) for a in args],text=True,capture_output=True,timeout=90)
    if result.returncode:raise RuntimeError(result.stderr or result.stdout)
    return result
if run(['git','-C',DEPENDENCY,'rev-parse','HEAD']).stdout.strip()!=COMMIT:
    raise ValueError('Unexpected upstream commit')
if run(['git','-C',DEPENDENCY,'status','--porcelain']).stdout.strip():
    raise ValueError('Dependency source has local modifications')
OUT.mkdir(parents=True,exist_ok=True)
sources=[DEPENDENCY/'src'/name for name in ['hook.c','buffer.c','trampoline.c','hde/hde64.c']]
sources += [HERE/'native_observer.c']
run([GCC,'-O2','-Wall','-Wextra','-Werror','-static-libgcc','-shared',
     '-I'+str(DEPENDENCY/'include'),*sources,'-o',OUT/'wx-native-observer-v6.dll'])
run([GCC,'-O2','-Wall','-Wextra','-Werror','-static-libgcc',HERE/'native_fixture.c',
     '-o',OUT/'wx-native-fixture.exe'])
artifacts={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
           [OUT/'wx-native-observer-v6.dll',OUT/'wx-native-fixture.exe']}
manifest={'upstream':'https://github.com/TsudaKageyu/minhook','commit':COMMIT,
          'artifacts':artifacts,'client_execution_verified':False,
          'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[HERE/'native_fixture.c',HERE/'native_observer.h']}}
(OUT/'build.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
