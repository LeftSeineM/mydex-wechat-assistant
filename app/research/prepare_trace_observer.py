"""Generate a separate version of the already tested passive observer.
It records only target-group call-stack RVAs, never text, keys, or send calls.
The active v6 sources and binary are left untouched.
"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE/'trace_v7'
OUT.mkdir(exist_ok=True)
def replace(text,before,after):
    if text.count(before)!=1:raise ValueError('Unexpected baseline: '+before[:60])
    return text.replace(before,after)

header=(HERE/'native_observer.h').read_text(encoding='utf-8')
header=replace(header,'char marker[64];','char marker[64];\n    char target_room[128];')
header=replace(header,'typedef uintptr_t (*LabTarget)', '''typedef struct {
    volatile LONG ready,hits;
    DWORD count,thread_id;
    uint64_t rvas[24];
} LabTrace;

typedef uintptr_t (*LabTarget)''')
(OUT/'native_observer.h').write_text(header,encoding='utf-8')
native=(HERE/'native_observer.c').read_text(encoding='utf-8')
native=replace(native,'static SRWLOCK shape_lock=SRWLOCK_INIT;', '''__declspec(dllexport) LabTrace lab_traces[4];
static SRWLOCK trace_lock=SRWLOCK_INIT;
static char target_room[128];
static SRWLOCK shape_lock=SRWLOCK_INIT;''')
native=replace(native,'static void inspect_object(uintptr_t object) {', '''static void record_trace(void) {
    if (!TryAcquireSRWLockExclusive(&trace_lock)) return;
    void *frames[32]={0}; uint64_t rvas[24]={0}; DWORD count=0;
    USHORT n=CaptureStackBackTrace(1,32,frames,NULL);
    for (USHORT i=0;i<n && count<24;i++) {
        uintptr_t p=(uintptr_t)frames[i];
        if (p>=module_base && p<module_base+module_size) rvas[count++]=p-module_base;
    }
    if (count) for (size_t i=0;i<4;i++) {
        LabTrace *s=&lab_traces[i];
        if (s->ready && s->count==count && !memcmp(s->rvas,rvas,count*8)) {
            InterlockedIncrement(&s->hits); break;
        }
        if (!s->ready) {
            s->count=count;s->thread_id=GetCurrentThreadId();
            memcpy(s->rvas,rvas,count*8);s->hits=1;
            MemoryBarrier();InterlockedExchange(&s->ready,1);break;
        }
    }
    ReleaseSRWLockExclusive(&trace_lock);
}

static void inspect_object(uintptr_t object) {''')
native=replace(native,'record_diagnostic(&diagnostic);', '''record_diagnostic(&diagnostic);
    if (diagnostic.type_value==1 && diagnostic.room_kind==1 && !strcmp(room,target_room)) record_trace();''')
native=replace(native,'!memchr(cfg.marker,0,sizeof(cfg.marker))) return 1;',
               '!memchr(cfg.marker,0,sizeof(cfg.marker)) || !memchr(cfg.target_room,0,sizeof(cfg.target_room))) return 1;')
native=replace(native,'cfg.fixture!=configured_fixture || strcmp(cfg.marker,marker)',
               'cfg.fixture!=configured_fixture || strcmp(cfg.marker,marker) || strcmp(cfg.target_room,target_room)')
native=replace(native,'memcpy(marker,cfg.marker,length+1); marker_size=length;',
               'memcpy(marker,cfg.marker,length+1); marker_size=length;\n    memcpy(target_room,cfg.target_room,strlen(cfg.target_room)+1);')
(OUT/'native_observer.c').write_text(native,encoding='utf-8')
fixture=(HERE/'native_fixture.c').read_text(encoding='utf-8')
fixture=replace(fixture,'.marker="WXPAIR1006"};','.marker="WXPAIR1006",.target_room="123456@chatroom"};')
(OUT/'native_fixture.c').write_text(fixture,encoding='utf-8')
build=(HERE/'build_native_observer.py').read_text(encoding='utf-8').replace('research-tools/native-observer','research-tools/native-trace').replace('wx-native-observer-v6.dll','wx-native-observer-v7.dll')
(OUT/'build.py').write_text(build,encoding='utf-8')
runner=(HERE/'run_native_observer.py').read_text(encoding='utf-8')
runner=replace(runner,'from external_reader import Reader','sys.path.insert(0,str(Path(__file__).resolve().parents[1]))\nfrom external_reader import Reader')
runner=replace(runner,'ROOT=Path(__file__).resolve().parents[1]','ROOT=Path(__file__).resolve().parents[2]')
runner=runner.replace('research-tools/native-observer','research-tools/native-trace').replace('wx-native-observer-v6.dll','wx-native-observer-v7.dll')
runner=replace(runner,"('marker',C.c_char*64)]","('marker',C.c_char*64),('target_room',C.c_char*128)]")
runner=replace(runner,'class NativeControl(Reader):', '''class Trace(C.Structure):
    _fields_=[('ready',W.LONG),('hits',W.LONG),('count',W.DWORD),('thread_id',W.DWORD),('rvas',C.c_uint64*24)]

class NativeControl(Reader):''')
runner=replace(runner,"(ROOT/'research'/name)","(ROOT/'research/trace_v7'/name)")
runner=replace(runner,"report['text_diagnostics']=", "traces=(Trace*4).from_buffer_copy(process.read(base+exports['lab_traces'],C.sizeof(Trace)*4))\n    report['call_stacks']=[{'hits':t.hits,'thread_id':t.thread_id,'rvas':[hex(r) for r in t.rvas[:t.count]]} for t in traces if t.ready==1 and 0<t.count<=24]\n    report['text_diagnostics']=")
runner=runner.replace('native-observer-fixture.json','native-trace-fixture.json').replace('native-observer.json','native-trace.json').replace('native-observer-events.jsonl','native-trace-events.jsonl').replace('native-watch-','native-trace-watch-')
runner=replace(runner,"config=Config(0x574c4231,seconds,int(fixture),0,marker.encode('utf-8'))", "room='123456@chatroom' if fixture else json.loads((ROOT/'.local/outbound-sample-evidence.json').read_text(encoding='utf-8-sig'))['room_id_candidate']\n        config=Config(0x574c4231,seconds,int(fixture),0,marker.encode('utf-8'),room.encode('ascii'))")
runner=replace(runner,"report['passed']=child.returncode==0", "report['trace_capture_verified']=bool(report['call_stacks'])\n            report['passed']=report['trace_capture_verified'] and child.returncode==0")
(OUT/'run.py').write_text(runner,encoding='utf-8')
print('Prepared separate passive call-stack observer sources')
