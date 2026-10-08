import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from history_reader import TargetHistory
from research.history_vfs import HistoryView
r=TargetHistory(group="示例朋友群")
path=next(p for p in r.keys if Path(p).name=='contact.db');key,salt=r.keys[path]
with HistoryView(path,key,salt) as view:
    rows=view.query('SELECT username,nick_name FROM contact WHERE username=?',('wxid_example000001',))
    tables=view.query("SELECT name,sql FROM sqlite_master WHERE type='table' AND (lower(name) LIKE '%room%' OR lower(name) LIKE '%member%')")
print(json.dumps({'member':rows,'group_schema':tables},ensure_ascii=False))
