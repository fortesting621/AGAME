import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
game = os.path.join(here, "buttkikers_united.py")

python_dir = os.path.dirname(sys.executable)
pythonw = os.path.join(python_dir, "pythonw.exe")
if not os.path.exists(pythonw):
    pythonw = sys.executable

CREATE_NO_WINDOW = 0x08000000
subprocess.Popen([pythonw, game], cwd=here, creationflags=CREATE_NO_WINDOW)