"""Launch only this project's hidden workers outside a transient shell job.
No client restart, login, injection, task scheduling, or automatic version bypass.
"""
import argparse,json,os
from pathlib import Path
import subprocess,sys
import psutil
from external_reader import Reader
from run_native_observer import CLIENT,ROOT
WORKERS={'panel':(ROOT/'server.py',[]),
         'outbound':(ROOT/'research/trace_v7/run.py',['--watch-status']),
         'receive':(ROOT/'research/run_native_receiver.py',['--watch-status']),
         'keys':(ROOT/'research/run_key_observer.py',['--watch-status'])}
def start(pid,reload=(),only=()):
    with Reader(pid) as process:
        if process.image_path().resolve()!=(CLIENT.parent.parent/'Weixin.exe').resolve():raise ValueError('Unexpected client')
    launched={};existing={}
    for process in psutil.process_iter(['pid','cmdline','exe']):
        try:
            args=process.info['cmdline'] or []
            for name,(script,_) in WORKERS.items():
                if str(script) in args:
                    if name in reload and name in ('panel','keys'):
                        allowed={Path(sys.executable).resolve(),Path(sys._base_executable).resolve()}
                        if Path(process.info['exe']).resolve() not in allowed:raise ValueError('Unexpected worker executable')
                        process.terminate()
                        try:process.wait(timeout=5)
                        except psutil.TimeoutExpired:process.kill();process.wait(timeout=5)
                    else:existing[name]=process.pid
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    flags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB
    for name,(script,args) in WORKERS.items():
        if only and name not in only:continue
        if name in existing:launched[name]={'pid':existing[name],'reused':True};continue
        arguments=[sys.executable,'-u',str(script)]
        if name!='panel':arguments+=['--pid',str(pid),*args]
        with (ROOT/'.local'/f'{name}-background.stdout.log').open('ab') as out, (ROOT/'.local'/f'{name}-background.stderr.log').open('ab') as err:
            child=subprocess.Popen(arguments,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=out,stderr=err,
                                   creationflags=flags,close_fds=True)
        launched[name]={'pid':child.pid,'reused':False}
    (ROOT/'.local/background-pids.json').write_text(json.dumps(launched,indent=2),encoding='utf-8')
    return launched
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--pid',type=int,required=True)
    parser.add_argument('--reload',action='append',choices=['panel','keys'],default=[])
    parser.add_argument('--only',action='append',choices=list(WORKERS),default=[])
    args=parser.parse_args()
    print(json.dumps(start(args.pid,args.reload,args.only)))
