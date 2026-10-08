"""Extend the proven worker queue to exactly two user-authorized groups."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE/'worker_sender_v2';OUT=HERE/'worker_sender_v3';OUT.mkdir(exist_ok=True)
c=(OLD/'native_sender.c').read_text(encoding='utf-8')
c=c.replace('static char bound_room[128];','')
c=c.replace('static DWORD perform_send(void *parameter)', '''static BOOL allowed_room(const char *room,DWORD fixture) {
    if (fixture) return !strcmp(room,"123456@chatroom") || !strcmp(room,"654321@chatroom");
    return !strcmp(room,"90000000003@chatroom") || !strcmp(room,"90000000006@chatroom");
}
static DWORD perform_send(void *parameter)''')
c=c.replace('if (bound_room[0] && strcmp(bound_room,cfg.room)) {code=4;goto done;}',
            'if (!allowed_room(cfg.room,cfg.fixture)) {code=4;goto done;}')
c=c.replace('if (!bound_room[0]) strcpy(bound_room,cfg.room);','')
c=c.replace('static char worker_room[128];','')
c=c.replace('return !strcmp(text,worker_room);','return allowed_room(text,worker_fixture);')
c=c.replace('!memchr(cfg.room,0,sizeof(cfg.room)) || !room_valid(cfg.room)) return 1;',
            '!memchr(cfg.room,0,sizeof(cfg.room)) || !room_valid(cfg.room) || !allowed_room(cfg.room,cfg.fixture)) return 1;')
c=c.replace('worker_fixture=cfg.fixture;strcpy(worker_room,cfg.room);','worker_fixture=cfg.fixture;')
c=c.replace('strcmp(cfg.room,worker_room) || !strlen(cfg.body)', '!allowed_room(cfg.room,cfg.fixture) || !strlen(cfg.body)')
c=c.replace('__declspec(dllexport) DWORD WINAPI RunSend(void *parameter)', '''__declspec(dllexport) DWORD WINAPI AdoptWorker(void *parameter) {
    DWORD cfg[2];
    if (!read_local(parameter,cfg,sizeof(cfg)) || cfg[0]!=SEND_MAGIC || !cfg[1] || worker_state.phase!=2) return 50;
    if (worker_state.worker_thread) return 51;
    worker_state.worker_thread=cfg[1];return 0;
}
__declspec(dllexport) DWORD WINAPI RunSend(void *parameter)''')
(OUT/'native_sender.c').write_text(c,encoding='utf-8')
(OUT/'native_sender.h').write_bytes((OLD/'native_sender.h').read_bytes())
fixture=(OLD/'send_fixture.c').read_text(encoding='utf-8')
fixture=fixture.replace('strcmp(value(&request->room),"123456@chatroom") ||',
                        '(strcmp(value(&request->room),"123456@chatroom") && strcmp(value(&request->room),"654321@chatroom")) ||')
(OUT/'send_fixture.c').write_text(fixture,encoding='utf-8')
build=(OLD/'build.py').read_text(encoding='utf-8').replace('research-tools/worker-sender','research-tools/worker-sender-v3').replace('wx-worker-sender-v2.dll','wx-worker-sender-v3.dll')
(OUT/'build.py').write_text(build,encoding='utf-8')
runner=(OLD/'run.py').read_text(encoding='utf-8').replace('research-tools/worker-sender','research-tools/worker-sender-v3').replace('wx-worker-sender-v2.dll','wx-worker-sender-v3.dll').replace('worker-sender-fixture.json','multi-sender-fixture.json')
runner=runner.replace('def config(body, fixture):','def config(body, fixture, room=None):')
runner=runner.replace("room = '123456@chatroom'", "room = room or '123456@chatroom'\n        if room not in ('123456@chatroom','654321@chatroom'): raise ValueError('Wrong fixture group')")
runner=runner.replace("room = binding['room_id']", "room = room or binding['room_id']\n        groups = json.loads((ROOT/'.local/monitored-groups.json').read_text(encoding='utf-8'))\n        if room not in {g['room_id'] for g in groups}: raise ValueError('Group was not authorized')\n        if room not in ('90000000003@chatroom','90000000006@chatroom'): raise ValueError('Unsupported bound group')")
runner=runner.replace("def action(pid, command, body=TEST_TEXT, fixture=False):", "def action(pid, command, body=TEST_TEXT, fixture=False, room=None, adopt_thread=None):")
runner=runner.replace("cfg = config(body, fixture)","cfg = config(body, fixture, room)")
runner=runner.replace("elif command == 'stop':", "elif command == 'adopt':\n            if not isinstance(adopt_thread,int) or adopt_thread<=0:raise ValueError('Missing proven worker thread')\n            code=process.run(base+exports['AdoptWorker'],bytes((W.DWORD*2)(0x57535031,adopt_thread)),10000)\n        elif command == 'stop':")
runner=runner.replace("two_queue = action(child.pid, 'send', TEST_TEXT, True)", "two_queue = action(child.pid, 'send', TEST_TEXT, True, room='654321@chatroom')")
runner=runner.replace("worker_context_verified=passed, stop_verified=passed", "worker_context_verified=passed, stop_verified=passed, second_group_verified=passed")
runner=runner.replace("['install', 'send', 'status', 'stop']", "['install', 'send', 'status', 'stop','adopt']")
runner=runner.replace("parser.add_argument('--text', default=TEST_TEXT)", "parser.add_argument('--text', default=TEST_TEXT)\n    parser.add_argument('--room')\n    parser.add_argument('--adopt-thread',type=int)")
runner=runner.replace("action(args.pid, args.action, args.text)","action(args.pid, args.action, args.text,room=args.room,adopt_thread=args.adopt_thread)")
(OUT/'run.py').write_text(runner,encoding='utf-8')
print('Prepared v3; explicit two-group allowlist, single verified native worker queue')
