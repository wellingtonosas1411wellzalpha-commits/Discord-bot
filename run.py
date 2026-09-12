# run.py — decoder & launcher for Kira bot
# Do not modify this file.

import os
import sys

_KEY = os.environ.get("KIRA_KEY", "")
if _KEY != "KirAiZENin":
    print("Unauthorized.")
    sys.exit(1)

def _decode(s: str) -> str:
    TOKENS = [
        ('<>|~', 'A'),
        ('|~~~', 'E'),
        ('|<>',  'B'),
        ('<>|',  'D'),
        ('|~~',  'F'),
        ('(',    'C'),
    ]
    JUNK   = set('#%₦¥')
    DIGITS = set('0123456789')

    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in JUNK:
            i += 1
            continue
        if ch in DIGITS:
            result.append(ch)
            i += 1
            continue
        matched = False
        for token, letter in TOKENS:
            if s[i:i+len(token)] == token:
                result.append(letter)
                i += len(token)
                matched = True
                break
        if not matched:
            i += 1

    return bytes.fromhex(''.join(result)).decode('utf-8')


_here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_here, 'encoded.kira'), encoding='utf-8') as _f:
    _src = _decode(_f.read())

exec(compile(_src, 'bot.py', 'exec'))
