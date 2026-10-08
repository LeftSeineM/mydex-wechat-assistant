"""Read-only checks. Never installs hooks or starts/sends to WeChat."""
import hashlib
import importlib
import json
import platform
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1] / 'app'
EXPECTED = '10f8e995453e2da46d4f2b5080cd6da1f13cc5147746adc119ceae38cb039de5'

def main():
    checks = {'windows_x64_python312': sys.platform == 'win32' and platform.machine().lower() in ('amd64','x86_64') and sys.version_info[:2] == (3,12)}
    for name in ('psutil','apsw','Crypto','cryptography','zstandard','lief'):
        try:
            importlib.import_module(name)
            checks[name] = True
        except (ImportError,OSError):
            checks[name] = False
    sys.path.insert(0, str(APP))
    try:
        from probe_native import CLIENT
        checks['client_exact_hash'] = CLIENT.is_file() and hashlib.sha256(CLIENT.read_bytes()).hexdigest() == EXPECTED
    except ImportError:
        checks['client_exact_hash'] = False
    data = APP / '.local/quote-m-session'
    required = ['session.json','history-file-profile.json','history-keys.dpapi',
                'quote-sample-evidence.json','group-binding.json','monitored-groups.json',
                'reply-scope.json','native-sender-settings.json']
    checks['account_files_present'] = all((data/name).is_file() for name in required)
    checks['model_credential_present'] = (APP/'.local/paratera-api-key.dpapi').is_file()
    checks['native_fixture_proof_present'] = (APP/'.local/account-sender-fixture.json').is_file()
    checks['live_binding_valid'] = False
    if all(checks.values()) or (all(v for k,v in checks.items() if k!='live_binding_valid')):
        try:
            from m_session_assistant import check_session
            from session_history import SessionHistory
            from account_scope import load_scope
            check_session(json.loads((data/'session.json').read_text(encoding='utf-8')))
            SessionHistory(data)
            load_scope(data)
            from research.worker_sender_v6.run import verified,action
            verified(False)
            session = json.loads((data/'session.json').read_text(encoding='utf-8'))
            status = action(session['pid'],'status',data=data)
            checks['live_binding_valid'] = status['phase']==2 and bool(status['worker_thread'])
        except Exception:
            pass
    print(json.dumps({'checks':checks,'ready':all(checks.values()),'sends_performed':0},indent=2))
    return 0 if all(checks.values()) else 2

if __name__ == '__main__':
    raise SystemExit(main())
