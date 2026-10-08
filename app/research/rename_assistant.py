import json
import re
import urllib.request
BASE='http://127.0.0.1:8769'
with urllib.request.urlopen(BASE,timeout=5) as response:html=response.read(300000).decode('utf-8')
token=re.search(r'<meta name="lab-token" content="([^"]+)"',html).group(1)
with urllib.request.urlopen(BASE+'/api/state',timeout=5) as response:state=json.load(response)
prompt=state['settings']['system_prompt']
prompt=re.sub(r'^你是微信群研究助手[^。]*。','你是群研究助手Mydex。',prompt)
request=urllib.request.Request(BASE+'/api/settings',json.dumps({'bot_name':'Mydex','system_prompt':prompt}).encode(),
          {'Content-Type':'application/json','X-Lab-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=5) as response:result=json.load(response)
if result['bot_name']!='Mydex':raise ValueError('Name not applied')
print(json.dumps({'assistant_name':'Mydex','reply_prefix':'Mydex：','startup_phrase':'我是群研究助手Mydex'},ensure_ascii=False))
