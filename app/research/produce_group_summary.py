"""Create a local Codex summary from already authorized target-group records.
Never emits credentials or group text to stdout, and never sends to WeChat.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab import Engine,Settings,Store
store=Store()
try:
    settings=Settings()
    result=Engine(settings,store).summarize_history()
    output=ROOT/'.local/group-summary.txt'
    output.write_text(result['reply'],encoding='utf-8')
    report={k:v for k,v in result.items() if k!='reply'}
    report.update(at=datetime.now(timezone.utc).isoformat(),reply_chars=len(result['reply']),output_file=output.name)
    (ROOT/'.local/group-summary-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
finally:store.db.close()
