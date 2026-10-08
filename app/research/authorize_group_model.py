"""Apply the human's explicit model-content consent to the running local app.
No message body, API key, credential, or CSRF token is printed.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
url='http://127.0.0.1:8769'
with urllib.request.urlopen(url,timeout=5) as response:
    html=response.read(300000).decode('utf-8')
token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
request=urllib.request.Request(url+'/api/settings',json.dumps({'group_model_authorized':True}).encode(),
                              {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=5) as response:
    result=json.load(response)
if result.get('group_model_authorized') is not True:raise ValueError('Consent not applied')
report={'at':datetime.now(timezone.utc).isoformat(),'group':result['group'],
        'provider':'codex','source':'explicit_human_question_reply',
        'scope':['target_group_text','target_group_quotes','target_group_file_metadata'],
        'database_keys_exported':False,'wechat_credentials_exported':False,'automatic_wechat_sending':False}
(ROOT/'.local/model-authorization.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'consent_applied':True,'provider':result['provider'],'keys_exported':False}))
