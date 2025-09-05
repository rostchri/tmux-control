# sitecustomize.py
import faulthandler
import signal
import sys
import time
import os

def dump_with_metadata(signum, frame):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    pid = os.getpid()
    prog = sys.argv[0] or "<unknown>"
    print(
        f"\n=== SIGUSR1 received at {ts} (pid={pid}, program={prog}) ===",
        file=sys.stderr,
        flush=True,
    )
    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)

# Signalhandler registrieren
signal.signal(signal.SIGUSR1, dump_with_metadata)
