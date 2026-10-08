import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
r=TargetHistory(group="示例朋友群")
reports=[]
for path in r.message_paths():
    result=r.fetch(path,r.name)
    reports.append({'file':Path(path).name,'target':result['target_table'],'stored':result['stored_rows'],'new':len(result['events'])})
print(json.dumps({'name':r.name,'room':r.room,'shards':reports},ensure_ascii=False))
