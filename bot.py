import importlib
from pathlib import Path
import core

FOLDERS = [
    "fun", "info", "economy", "jobs", "pets", "marriage", "achievements",
    "market", "shop", "gambling", "utility", "levels", "admin", "owner",
    "Xephongpt", "tester",
]

for folder in FOLDERS:
    for path in sorted(Path(folder).glob("*.py")):
        if path.name == "__init__.py":
            continue
        importlib.import_module(f"{folder}.{path.stem}")

if __name__ == "__main__":
    core.start()
