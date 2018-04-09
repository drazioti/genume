from shlex import split as cmdsplit
import subprocess as sbpr
import os

from genume.globals import VERSION
from genume.registry.value import ValueEntry

def parse(cmdl, c):
    while len(cmdl) != 0:
        cmd = cmdl.pop(0)
        if cmd == "KVAL":
            # Key-value case.
            k = cmdl.pop(0)
            v = ValueEntry(c, cmdl.pop(0))
            c[k] = v
        else:
            print("Warn: invalid command {0}".format(cmd))

def run(f):
    if os.access(str(f), os.X_OK):
        o = sbpr.check_output(str(f))
        # Make everything be on a single line.
        s = o.decode("utf-8").strip().replace("\n", " ")
        return s
    else:
        print("Warn: {0} is not executable.".format(str(f)))

def run_and_parse(cat, file):
    s = run(file)
    if s:
        parse(cmdsplit(s), cat)

# Initialize environment variables.
os.putenv("GENUME_VERSION", VERSION)