"""Load final supervisor binding support without interrupting model replies."""
import json
from pathlib import Path
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'research'))
from start_background import start
end=time.monotonic()+50;quiet=0
while time.monotonic()<end:
    with urllib.request.urlopen('http://127.0.0.1:8769/api/state',timeout=8) as response:state=json.load(response)
    busy=any(s.get('model_busy') for s in state['group_states']) or state['native_sender'].get('pending')
    busy=busy or any(d['state']=='sending' for d in state['outbox'])
    quiet=0 if busy else quiet+1
    if quiet>=2:break
    time.sleep(.8)
else:raise TimeoutError('Replies still active; existing service kept running')
print(json.dumps(start(55832,reload=['panel'],only=['panel'])))
