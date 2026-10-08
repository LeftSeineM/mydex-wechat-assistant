"""Worker-thread sender v2. Leave the crashed direct-call version disabled."""
import hashlib
from pathlib import Path
import lief
from run_native_observer import CLIENT,EXPECTED_SHA256
HERE=Path(__file__).resolve().parent;OUT=HERE/'worker_sender_v2';OUT.mkdir(exist_ok=True)
data=CLIENT.read_bytes()
if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:raise ValueError('Client changed')
pe=lief.PE.parse(str(CLIENT))
def entry(rva):
    s=next(s for s in pe.sections if s.virtual_address<=rva< s.virtual_address+s.sizeof_raw_data)
    off=s.pointerto_raw_data+rva-s.virtual_address
    return ','.join('0x%02x'%b for b in data[off:off+24])
base=(HERE/'native_sender.c').read_text(encoding='utf-8')
base='#define _WIN32_WINNT 0x0600\n'+base
base=base.replace('#include <wchar.h>','#include <wchar.h>\n#include <intrin.h>\n#include "MinHook.h"')
base=base.replace('__declspec(dllexport) DWORD WINAPI RunSend(void *parameter)', 'static DWORD perform_send(void *parameter)')
base=base.replace('&RunSend,&pinned','&perform_send,&pinned')
base=base.replace('BOOL WINAPI DllMain(','''typedef uintptr_t (*CoreCall)(void *,void *,const void *,uint32_t);
typedef uintptr_t (*PumpCall)(void *);
typedef struct { DWORD magic; volatile LONG phase,pending; DWORD worker_thread;
    volatile LONG64 core_calls,pump_calls,queued,executed,context_failures;
    DWORD last_code,execution_thread; } WorkerState;
__declspec(dllexport) WorkerState worker_state={.magic=SEND_MAGIC};
static CoreCall core_original;static PumpCall pump_original;
static void *core_target,*pump_target;
static uintptr_t worker_base,worker_vtable;
static DWORD worker_fixture;
static char worker_room[128];
static SendConfig queued_config;
static SRWLOCK queue_lock=SRWLOCK_INIT;

static BOOL current_context_valid(void) {
    if (worker_fixture) {
        typedef BOOL (*Check)(void);
        Check check=(Check)(uintptr_t)GetProcAddress(GetModuleHandleW(NULL),"fixture_context_valid");
        return check && check();
    }
    DWORD index=0;uintptr_t vector=(uintptr_t)__readgsqword(0x58),tls=0,weak=0,context=0;
    if (!read_local((void *)(worker_base+0xb9141a0),&index,4) || index>4096 || !vector) return FALSE;
    if (!read_local((void *)(vector+index*8),&tls,8) || !tls) return FALSE;
    if (!read_local((void *)(tls+0x1f0),&weak,8) || !weak) return FALSE;
    return read_local((void *)weak,&context,8) && context!=0;
}
static BOOL target_message(const void *pair) {
    uintptr_t object=0,vptr=0;NativeString room;
    if (!pair || !read_local(pair,&object,8) || !object || !read_local((void *)object,&vptr,8) || vptr!=worker_vtable) return FALSE;
    if (!read_local((void *)(object+0xb0),&room,32) || room.length>100 || room.capacity<room.length) return FALSE;
    char text[128]={0};
    if (room.capacity==15 && room.length<=15) memcpy(text,room.data,(size_t)room.length);
    else if (room.capacity>=16 && room.capacity<=1048576) {
        uintptr_t p=0;memcpy(&p,room.data,8);
        if (!read_local((void *)p,text,(size_t)room.length)) return FALSE;
    } else return FALSE;
    return !strcmp(text,worker_room);
}
static void drain(void) {
    if (worker_state.phase!=2 || worker_state.worker_thread!=GetCurrentThreadId() ||
        InterlockedCompareExchange(&worker_state.pending,2,1)!=1) return;
    if (!current_context_valid()) {
        InterlockedIncrement64(&worker_state.context_failures);worker_state.last_code=30;
        InterlockedExchange(&worker_state.pending,0);return;
    }
    worker_state.execution_thread=GetCurrentThreadId();
    worker_state.last_code=perform_send(&queued_config);
    InterlockedIncrement64(&worker_state.executed);
    InterlockedExchange(&worker_state.pending,0);
}
static uintptr_t core_detour(void *manager,void *result,const void *pair,uint32_t flag) {
    DWORD before=GetLastError();BOOL target=target_message(pair);SetLastError(before);
    uintptr_t returned=core_original(manager,result,pair,flag);DWORD after=GetLastError();
    InterlockedIncrement64(&worker_state.core_calls);
    if (target && current_context_valid()) worker_state.worker_thread=GetCurrentThreadId();
    drain();SetLastError(after);return returned;
}
static uintptr_t pump_detour(void *task) {
    uintptr_t returned=pump_original(task);DWORD after=GetLastError();
    InterlockedIncrement64(&worker_state.pump_calls);drain();SetLastError(after);return returned;
}
__declspec(dllexport) DWORD WINAPI StopWorker(void *unused) {
    (void)unused;
    if (worker_state.phase==5) return 0;
    if (worker_state.phase!=2) return 40;
    InterlockedExchange(&worker_state.phase,4);
    InterlockedCompareExchange(&worker_state.pending,0,1);
    MH_STATUS a=MH_DisableHook(core_target),b=MH_DisableHook(pump_target);
    if (a!=MH_OK || b!=MH_OK) {worker_state.phase=-40;return 41;}
    worker_state.phase=5;return 0;
}
__declspec(dllexport) DWORD WINAPI InstallWorker(void *parameter) {
    SendConfig cfg;HMODULE pin=NULL,host=NULL;
    if (!read_local(parameter,&cfg,sizeof(cfg)) || cfg.magic!=SEND_MAGIC || cfg.fixture>1 ||
        !memchr(cfg.room,0,sizeof(cfg.room)) || !room_valid(cfg.room)) return 1;
    if (InterlockedCompareExchange(&worker_state.phase,1,0)!=0) return 2;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCWSTR)(uintptr_t)&InstallWorker,&pin)) return 3;
    worker_fixture=cfg.fixture;strcpy(worker_room,cfg.room);
    if (cfg.fixture) {
        host=GetModuleHandleW(NULL);
        core_target=(void *)(uintptr_t)GetProcAddress(host,"fixture_core");
        pump_target=(void *)(uintptr_t)GetProcAddress(host,"fixture_pump");
        worker_vtable=(uintptr_t)GetProcAddress(host,"fixture_message_vtable");
        if (!core_target || !pump_target || !worker_vtable) return 4;
    } else {
        host=GetModuleHandleW(L"Weixin.dll");if (!host) return 5;worker_base=(uintptr_t)host;
        core_target=(void *)(worker_base+0x178f100);pump_target=(void *)(worker_base+0xd823e0);worker_vtable=worker_base+0x8e53588;
        unsigned char code[24];
        static const unsigned char core_bytes[24]={CORE_ENTRY};
        static const unsigned char pump_bytes[24]={PUMP_ENTRY};
        if (!read_local(core_target,code,24) || memcmp(code,core_bytes,24) ||
            !read_local(pump_target,code,24) || memcmp(code,pump_bytes,24)) return 6;
    }
    if (MH_Initialize()!=MH_OK || MH_CreateHook(core_target,(void *)(uintptr_t)&core_detour,(void **)&core_original)!=MH_OK ||
        MH_CreateHook(pump_target,(void *)(uintptr_t)&pump_detour,(void **)&pump_original)!=MH_OK) return 7;
    if (MH_EnableHook(core_target)!=MH_OK) return 8;
    if (MH_EnableHook(pump_target)!=MH_OK) {MH_DisableHook(core_target);return 9;}
    worker_state.phase=2;return 0;
}
__declspec(dllexport) DWORD WINAPI RunSend(void *parameter) {
    SendConfig cfg;
    if (!read_local(parameter,&cfg,sizeof(cfg)) || cfg.magic!=SEND_MAGIC || cfg.fixture!=worker_fixture ||
        !memchr(cfg.room,0,sizeof(cfg.room)) || !memchr(cfg.body,0,sizeof(cfg.body)) ||
        strcmp(cfg.room,worker_room) || !strlen(cfg.body) || strlen(cfg.body)>3072 ||
        !MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,cfg.body,(int)strlen(cfg.body),NULL,0)) return 10;
    if (worker_state.phase!=2 || !TryAcquireSRWLockExclusive(&queue_lock)) return 11;
    DWORD result=0;
    if (worker_state.pending) result=12;
    else {memcpy(&queued_config,&cfg,sizeof(cfg));MemoryBarrier();InterlockedExchange(&worker_state.pending,1);InterlockedIncrement64(&worker_state.queued);}
    ReleaseSRWLockExclusive(&queue_lock);return result;
}

BOOL WINAPI DllMain(''')
base=base.replace('CORE_ENTRY',entry(0x178f100)).replace('PUMP_ENTRY',entry(0xd823e0))
(OUT/'native_sender.c').write_text(base,encoding='utf-8')
(OUT/'native_sender.h').write_text('#ifndef _WIN32_WINNT\n#define _WIN32_WINNT 0x0600\n#endif\n'+(HERE/'native_sender.h').read_text(encoding='utf-8'),encoding='utf-8')
fixture=(HERE/'send_fixture.c').read_text(encoding='utf-8')
fixture=fixture.replace('static volatile LONG bad,allocations;', '''static volatile LONG bad,allocations;static DWORD tls_index;
__declspec(dllexport) uintptr_t fixture_message_vtable[8];
__declspec(dllexport) BOOL fixture_context_valid(void) {return TlsGetValue(tls_index)==(void *)0x4142;}
__declspec(dllexport) __attribute__((noinline)) uintptr_t fixture_core(void *manager,void *result,const void *pair,uint32_t flag) {
    if (manager!=(void *)0x1234 || !pair || flag!=1) InterlockedIncrement(&bad);
    *(uintptr_t *)result=0x5555;return (uintptr_t)result;
}
__declspec(dllexport) __attribute__((noinline)) uintptr_t fixture_pump(void *task) {(void)task;return 0x6060;}
static DWORD WINAPI worker(void *argument) {
    (void)argument;TlsSetValue(tls_index,(void *)0x4142);
    unsigned char object[0x798]={0};uintptr_t vptr=(uintptr_t)fixture_message_vtable;
    memcpy(object,&vptr,8);NativeString room={.length=15,.capacity=15};strcpy(room.data,"123456@chatroom");memcpy(object+0xb0,&room,32);
    uintptr_t pair[2]={(uintptr_t)object,0};
    typedef uintptr_t (*CorePointer)(void *,void *,const void *,uint32_t);
    typedef uintptr_t (*PumpPointer)(void *);
    CorePointer volatile core=fixture_core;PumpPointer volatile pump=fixture_pump;
    ULONGLONG end=GetTickCount64()+6000;
    while (GetTickCount64()<end) {
        uintptr_t result=0;SetLastError(0x4545);
        uintptr_t returned=core((void *)0x1234,&result,pair,1);
        if (returned!=(uintptr_t)&result || result!=0x5555 || GetLastError()!=0x4545 || pump(NULL)!=0x6060) InterlockedIncrement(&bad);
        Sleep(50);
    }
    return 0;
}''').replace('    CoreCall_unused_placeholder\n','')
fixture=fixture.replace('if (unused || !request', 'if (!fixture_context_valid() || unused || !request')
fixture=fixture.replace('puts("ready");fflush(stdout);Sleep(4000);', '''tls_index=TlsAlloc();HANDLE thread=CreateThread(NULL,0,worker,NULL,0,NULL);
    if (!thread) return 2;
    puts("ready");fflush(stdout);WaitForSingleObject(thread,8000);CloseHandle(thread);TlsFree(tls_index);''')
(OUT/'send_fixture.c').write_text(fixture,encoding='utf-8')
build=(HERE/'build_native_sender.py').read_text(encoding='utf-8')
build=build.replace('research-tools/native-sender','research-tools/worker-sender').replace('wx-native-sender-v1.dll','wx-worker-sender-v2.dll')
build=build.replace("for source,name,extra in", "DEPENDENCY=Path('D:/Software/WeChatGroupLab/research/minhook-v1.3.4')\nfor source,name,extra in")
build=build.replace("result=subprocess.run([GCC", "sources=[str(HERE/source)]\n    if extra:sources+=[str(DEPENDENCY/'src'/p) for p in ('hook.c','buffer.c','trampoline.c','hde/hde64.c')]\n    result=subprocess.run([GCC")
build=build.replace("*extra,str(HERE/source),", "*extra,'-I'+str(DEPENDENCY/'include'),*sources,")
(OUT/'build.py').write_text(build,encoding='utf-8')
print('Prepared sender v2: remote entry queues; native work executes only on a verified Weixin message thread')
