# sitecustomize.py
# Fügt Jitter/Backoff in PyMQI Queue.get() ein, ohne App-Code zu ändern.
import os, sys, time, random
import pymqi
from pymqi import CMQC, MQMIError

# --- Konfiguration über ENV ---
# Vorab-Jitter vor jedem GET (in Millisekunden, Range inkl. Zufall)
_JITTER_RANGE = os.environ.get("GET_JITTER_RANGE_MS", "0,300")
try:
    _JITTER_MIN_MS, _JITTER_MAX_MS = [max(0, int(x)) for x in _JITTER_RANGE.split(",", 1)]
except Exception:
    _JITTER_MIN_MS, _JITTER_MAX_MS = 0, 0

# Backoff nur bei "no message" (2033), in Millisekunden (0 = aus)
_BACKOFF_2033_MS = int(os.environ.get("GET_BACKOFF_2033_MS", "0"))

# Optional: nur beim Start einmalig desynchronisieren (ms)
_STARTUP_JITTER_MS = int(os.environ.get("STARTUP_JITTER_MS", "0"))

_DEBUG = os.environ.get("GET_JITTER_DEBUG", "").lower() in ("1","true","yes")

def _sleep_ms(ms: int):
    if ms > 0:
        time.sleep(ms / 1000.0)

# Einmaliger Start-Jitter (desynchronisiert Container-Starts)
if _STARTUP_JITTER_MS > 0:
    _sleep_ms(random.randint(0, _STARTUP_JITTER_MS))
    if _DEBUG:
        print(f"[get-jitter] startup jitter applied (<= {_STARTUP_JITTER_MS} ms)", file=sys.stderr)

# Original sichern & patchen
_ORIG_GET = pymqi.Queue.get

def _jittered_get(self, *args, **kwargs):
    # Vorab-Jitter vor jedem GET (klein halten, z.B. 0–300 ms)
    if _JITTER_MAX_MS > 0:
        _sleep_ms(random.randint(_JITTER_MIN_MS, _JITTER_MAX_MS))

    try:
        return _ORIG_GET(self, *args, **kwargs)
    except MQMIError as e:
        # Optionale Backoff-Pause nur bei "no message available" (2033)
        if e.comp == CMQC.MQCC_FAILED and e.reason == CMQC.MQRC_NO_MSG_AVAILABLE and _BACKOFF_2033_MS > 0:
            if _DEBUG:
                print(f"[get-jitter] 2033 backoff {_BACKOFF_2033_MS} ms", file=sys.stderr)
            _sleep_ms(_BACKOFF_2033_MS)
        # Fehler unverändert weiterreichen
        raise

# Monkeypatch aktivieren
pymqi.Queue.get = _jittered_get

if _DEBUG:
    print(
        f"[get-jitter] enabled: jitter={_JITTER_MIN_MS}-{_JITTER_MAX_MS}ms, "
        f"backoff2033={_BACKOFF_2033_MS}ms, startup_jitter<={_STARTUP_JITTER_MS}ms",
        file=sys.stderr
    )
