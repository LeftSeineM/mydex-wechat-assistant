"""Inspect only M's own profile, the work-base contact and fixed test markers."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from history_crypto import dpapi
from history_vfs import HistoryView
from read_target_history import text_value
DATA=Path(__file__).resolve().parents[1]/'.local/quote-m-session'

def main():
    session=json.loads((DATA/'session.json').read_text(encoding='utf-8'))
    room=session['allowed_room'];account='wxid_example000002'
    table='Msg_'+hashlib.md5(room.encode()).hexdigest()
    private=json.loads(dpapi((DATA/'history-keys.dpapi').read_bytes(),True))
    results={'account':account,'room':room,'authenticated_files':[], 'samples':[]}
    for item in private['files']:
        path=Path(item['path'])
        if Path(session['account_roots'][0]) not in path.parents:raise ValueError('Unexpected account')
        results['authenticated_files'].append(path.name)
        with HistoryView(path,bytes.fromhex(item['key']),bytes.fromhex(item['salt'])) as view:
            if path.name=='contact.db':
                rows=view.query('SELECT username,nick_name,is_in_chat_room FROM contact WHERE username IN (?,?)',(room,account))
                results['contacts']=[{'id':r[0],'name':r[1],'in_group':r[2]} for r in rows]
            else:
                if not view.query('SELECT name FROM sqlite_master WHERE name=?',(table,)):continue
                rows=view.query('SELECT local_id,server_id,local_type,create_time,message_content,compress_content FROM "'+table+'" ORDER BY local_id DESC LIMIT 200')
                for local,server,kind,created,body,compressed in rows:
                    text=text_value(body) or text_value(compressed)
                    if not any(marker in text for marker in ('引用原文1008','引用回复1008','引用确认1008')):continue
                    info={'local_id':local,'server_id':str(server),'type':kind,'created':created}
                    xml=text[text.find('<'):] if '<' in text else ''
                    if xml:
                        root=ET.fromstring(xml);app=root if root.tag=='appmsg' else root.find('.//appmsg')
                        if app is not None:
                            info.update(app_type=app.findtext('type'),title=app.findtext('title'))
                            ref=app.find('refermsg')
                            if ref is not None:
                                info['reference']={name:ref.findtext(name) for name in ('type','svrid','fromusr','chatusr','displayname','content','createtime')}
                    else:info['text']=text.split(':\n',1)[-1]
                    results['samples'].append(info)
    (DATA/'quote-sample-evidence.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
