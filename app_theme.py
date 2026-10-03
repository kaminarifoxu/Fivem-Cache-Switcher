# Copyright (c) 2026 GANOMABI / amiinarii.
import json
from pathlib import Path
THEME = 'light'
DARK = {
 '#f7f0e3':'#101113', '#fffaf1':'#191b1f', '#ddc8a3':'#343039',
 '#896019':'#e9bc70', '#786757':'#a9a0a5', '#30251e':'#f0edf0',
 '#efe0c7':'#151619', '#f1e3cc':'#27242a', '#e6d0aa':'#3c343c',
 '#ead3b2':'#42242d', '#ead0b0':'#71333a', '#e3c292':'#8f3642',
 '#efdfc5':'#21181c', '#f5ead6':'#151216', '#fae6d1':'#2f1d25',
 '#c2a474':'#73505b', '#b68b48':'#b68b48', '#8e6846':'#8e6846',
}
def color(value):
    return DARK.get(value, value) if THEME == 'dark' else value

def load(path):
    global THEME
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8')).get('theme')
        THEME=value if value in ('light','dark') else 'light'
    except (OSError,ValueError,AttributeError):
        THEME='light'

def save(value,path):
    global THEME
    if value not in ('light','dark'):
        raise ValueError('Invalid theme')
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix('.new')
    temp.write_text(json.dumps({'theme':value}),encoding='utf-8');temp.replace(target)
    THEME=value
