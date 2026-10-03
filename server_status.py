# Copyright (c) 2026 GANOMABI / amiinarii.
"""Fetch only display fields from the same backend as the FiveM server list."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.request import Request, urlopen
from server_catalog import connect_uri

def page_url(code):
    connect_uri(code)
    return 'https://servers.fivem.net/servers/detail/' + code

def parse_status(payload):
    data = payload['Data']
    clients = data.get('clients')
    maximum = data.get('svMaxclients', data.get('sv_maxclients'))
    if type(clients) is not int or clients < 0 or type(maximum) is not int or maximum < clients:
        raise ValueError('Invalid player counts')
    description = data.get('vars', {}).get('sv_projectDesc', '')
    if not isinstance(description, str):
        raise ValueError('Invalid server description')
    description = re.sub(r'\^[0-9]', '', description)
    description = ''.join(c for c in description if c.isprintable() or c == '\n')[:500]
    return {'clients': clients, 'maximum': maximum, 'description': description,
            'checked': datetime.now().strftime('%H:%M:%S'), 'available': True}

def fetch_status(code):
    connect_uri(code)
    request = Request('https://frontend.cfx-services.net/api/servers/single/' + code,
                      headers={'User-Agent': 'GanoV-Cache-Switch', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=10) as response:
        raw = response.read(4*1024*1024+1)
    if len(raw) > 4*1024*1024:
        raise ValueError('Server response too large')
    return parse_status(json.loads(raw))

def fetch_statuses(codes):
    def fetch(code):
        try:
            return code, fetch_status(code)
        except Exception:
            return code, {'available': False}
    with ThreadPoolExecutor(max_workers=4) as executor:
        return dict(executor.map(fetch, codes))
