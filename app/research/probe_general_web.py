"""A public-information-only probe for the newly enabled model search tool."""
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lab import Backend,Settings,DATA,codex_args
cfg=Settings().get();cfg['web_search_enabled']=True
cfg['system_prompt']='你是Mydex。请只使用只读联网搜索核实公开资料。不能调用命令、读取本机文件或其他工具。'
prompt='请用 web_search 查询 Python 官方网站 python.org 是否提供 Windows 下载入口，只回答一句话并附官方链接。必须实际搜索，不要仅凭记忆回答。'
start=time.monotonic()
cmd=codex_args(DATA/'codex-work',cfg['model'],True)
# A separate public-only probe: see whether the host feature gates web_search.
index=next((i for i in range(len(cmd)-1) if cmd[i]=='--disable' and cmd[i+1]=='code_mode_host'),None)
if index is not None:del cmd[index:index+2]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                      env=Backend.codex_environment(cfg),creationflags=subprocess.CREATE_NO_WINDOW)
out,_=proc.communicate((cfg['system_prompt']+'\n'+prompt).encode('utf-8'),timeout=120)
events=[json.loads(line) for line in out.decode('utf-8','replace').splitlines() if line.startswith('{')]
types=[e.get('item',{}).get('type') for e in events if e.get('type')=='item.completed']
answers=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
passed=proc.returncode==0 and 'web_search' in types and bool(answers)
report={'passed':passed,'web_search_executed':'web_search' in types,'item_types':types,
        'reply':answers[-1] if answers else '', 'exit_code':proc.returncode,'seconds':round(time.monotonic()-start,2),
        'group_content_used':False,
        'error_items':[e.get('item',{}) for e in events if e.get('item',{}).get('type')=='error']}
(ROOT/'.local/web-search-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if passed else 1)
