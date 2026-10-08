"""Configure the authorized provider locally; never echo the secret."""
import getpass
import json
from pathlib import Path
import sys

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))

def main():
    from api_credentials import save_key
    from lab import Settings
    template = json.loads(Path(__file__).with_name('settings.template.json').read_text(encoding='utf-8'))
    key = getpass.getpass('Paratera API key (hidden): ')
    save_key(APP / '.local/paratera-api-key.dpapi', template['api_base'], key)
    key = None
    Settings(APP / '.local/settings.json').update(template)
    print('Provider configured locally. WeChat account/session enrollment is still required.')

if __name__ == '__main__':
    main()
