# Copyright (c) 2026 GANOMABI / amiinarii.
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

CATALOG_URL = 'https://raw.githubusercontent.com/kaminarifoxu/Fivem-Cache-Switcher/main/servers.json'

def validate_catalog(data):
    if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('servers'), list) or len(data['servers']) > 200:
        raise ValueError('Invalid server catalog')
    ids = set()
    for server in data['servers']:
        if not isinstance(server, dict):
            raise ValueError('Invalid server entry')
        if not isinstance(server.get('id'), str) or not re.fullmatch(r'[a-z0-9_-]{1,60}', server['id']) or server['id'] in ids:
            raise ValueError('Invalid or duplicate server id')
        ids.add(server['id'])
        if not isinstance(server.get('name'), str) or not 1 <= len(server['name']) <= 100:
            raise ValueError('Invalid server name')
        if not isinstance(server.get('join_code'), str) or not re.fullmatch(r'[a-z0-9]{6,10}', server['join_code']):
            raise ValueError('Invalid Cfx join code')
        if not isinstance(server.get('description', {}), dict) or any(not isinstance(v, str) or len(v) > 500 for v in server.get('description', {}).values()):
            raise ValueError('Invalid description')
    return data

def read_catalog(path):
    return validate_catalog(json.loads(Path(path).read_text(encoding='utf-8-sig')))

def load_catalog(cache, bundled):
    for path in (cache, bundled):
        try:
            return read_catalog(path)
        except (OSError, ValueError):
            pass
    return {'schema_version':1, 'servers':[]}

def sync_catalog(cache):
    request = Request(CATALOG_URL, headers={'User-Agent':'GanoV-Cache-Switch', 'Cache-Control':'no-cache'})
    with urlopen(request, timeout=12) as response:
        raw = response.read(1024*1024+1)
    if len(raw) > 1024*1024:
        raise ValueError('Server catalog too large')
    catalog = validate_catalog(json.loads(raw))
    path = Path(cache)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)
    return catalog

def connect_uri(code):
    if not isinstance(code, str) or not re.fullmatch(r'[a-z0-9]{6,10}', code):
        raise ValueError('Invalid Cfx join code')
    return 'fivem://connect/cfx.re/join/' + code
