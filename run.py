import os

here = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(here, "start.py")
exec(compile(open(path, encoding="utf-8").read(), path, "exec"))
