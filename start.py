import runpy
import os

print("Xephon starting from bot.py")
here = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(here, "bot.py"), run_name="__main__")
