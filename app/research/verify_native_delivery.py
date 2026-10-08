"""Verify the fixed send test in authenticated records of the bound group only."""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from history_reader import TargetHistory

TEXT = '小研：群助手自动发送测试1007，收到这条消息就说明回发成功。'
reader = TargetHistory()
found = []
for path in reader.message_paths():
    result = reader.fetch(path, reader.name)
    for event in result['events']:
        if event['content'] == TEXT and event['is_self'] and event['created'] >= 1791304200:
            found.append({key: event[key] for key in ('id', 'created', 'local_id', 'database', 'room_id', 'is_self')})
report = {'at': datetime.now(timezone.utc).isoformat(), 'group_name': reader.name,
          'target_group_only': True, 'native_delivery_verified': bool(found),
          'server_record_verified': any(r['id'].isdigit() and int(r['id']) != 0 for r in found),
          'matches': found}
(ROOT/'.local/native-delivery-proof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report))
