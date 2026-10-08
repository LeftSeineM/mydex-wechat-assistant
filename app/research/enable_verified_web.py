import json
from pathlib import Path
import re
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
proof=json.loads((ROOT/'.local/web-search-probe.json').read_text(encoding='utf-8'))
if not proof.get('passed') or not proof.get('web_search_executed'):raise ValueError('Search was not tested')
base='http://127.0.0.1:8769'
with urllib.request.urlopen(base,timeout=5) as response:html=response.read(300000).decode('utf-8')
token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
request=urllib.request.Request(base+'/api/settings',b'{"web_search_enabled":true}',
                              {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=5) as response:result=json.load(response)
print(json.dumps({'web_search_enabled':result['web_search_enabled'],'shell_execution_enabled':False}))
