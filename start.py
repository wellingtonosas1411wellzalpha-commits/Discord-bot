import os
import sys
import hashlib

_HASH = "90b011ac65424dc1df64f9de8cd56edb944e39a2ad233325cee6b15bf25d36ce"
_key = os.environ.get("KIRA_KEY", "")
if hashlib.sha256(_key.encode()).hexdigest() != _HASH:
    print("Unauthorized.")
    sys.exit(1)

def _decode(s: str) -> str:
    tokens = [
        ("<>|~", "A"),
        ("|~~~", "E"),
        ("|<>", "B"),
        ("<>|", "D"),
        ("|~~", "F"),
        ("(", "C"),
    ]
    junk = set("#%₦¥")
    digits = set("0123456789")
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in junk:
            i += 1
            continue
        if ch in digits:
            out.append(ch)
            i += 1
            continue
        hit = False
        for token, letter in tokens:
            if s[i:i + len(token)] == token:
                out.append(letter)
                i += len(token)
                hit = True
                break
        if not hit:
            i += 1
    return bytes.fromhex("".join(out)).decode("utf-8")

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "encoded.kira"), encoding="utf-8") as f:
    src = _decode(f.read())
exec(compile(src, "bot.py", "exec"))
