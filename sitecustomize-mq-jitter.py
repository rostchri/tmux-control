# sitecustomize.py
# Kombiniert:
#  - Jitter/Backoff für pymqi.Queue.get()
#  - Sicheres Neutralisieren von MsgId/CorrelId/MatchOptions (optional)
import os, sys, time, random
import pymqi
from pymqi import CMQC, MQMIError

# ---------------- Konfiguration (ENV) ----------------
# Vorab-Jitter vor JEDEM get() (ms, Range "min,max")
_JITTER_RANGE = os.environ.get("GET_JITTER_RANGE_MS", "0,300")
try:
    _JITTER_MIN_MS, _JITTER_MAX_MS = [max(0, int(x)) for x in _JITTER_RANGE.split(",", 1)]
except Exception:
    _JITTER_MIN_MS, _JITTER_MAX_MS = 0, 0

# Backoff bei 2033 (No message) in ms (0 = aus)
_BACKOFF_2033_MS = int(os.environ.get("GET_BACKOFF_2033_MS", "0"))

# Einmalig beim Start des Prozesses desynchronisieren (ms)
_STARTUP_JITTER_MS = int(os.environ.get("STARTUP_JITTER_MS", "0"))

# Match-Reset aktivieren? (1/true/yes = an)
_CLR = os.environ.get("GET_CLEAR_MATCH", "1").lower() in ("1", "true", "yes")

# Nur jitter, wenn NICHT mit WAIT gearbeitet wird? (für Long-Polling-Setups)
_ONLY_NO_WAIT = os.environ.get("GET_JITTER_ONLY_IF_NO_WAIT", "0").lower() in ("1", "true", "yes")

# Debug-Logs auf stderr?
_DEBUG = os.environ.get("GET_JITTER_DEBUG", "").lower() in ("1", "true", "yes")

def _sleep_ms(ms: int):
    if ms > 0:
        time.sleep(ms / 1000.0)

# Einmaliger Start-Jitter (Container entkoppeln)
if _STARTUP_JITTER_MS > 0:
    _sleep_ms(random.randint(0, _STARTUP_JITTER_MS))
    if _DEBUG:
        print(f"[get-jitter] startup jitter applied (<= {_STARTUP_JITTER_MS} ms)", file=sys.stderr)

# ---------------- Original sichern & Wrapper bauen ----------------
_ORIG_GET = pymqi.Queue.get  # nur einmal referenzieren

def _patched_get(self, maxlen=None, md=None, gmo=None):
    """
    Wrapper um pymqi.Queue.get():
      1) optional MsgId/CorrelId/MatchOptions neutralisieren (nur wenn kein Matching erkennbar)
      2) optional Vorab-Jitter (bei Bedarf nur wenn kein WAIT gesetzt ist)
      3) Original get() aufrufen
      4) optional Backoff bei MQRC_NO_MSG_AVAILABLE (2033)
    """
    # (1) Match neutralisieren, wenn gewünscht und kein explizites Matching erkennbar
    if _CLR and md is not None and gmo is not None:
        # Erkennen, ob explizites Matching beabsichtigt ist
        want_match = bool(
            (gmo.MatchOptions and gmo.MatchOptions != CMQC.MQMO_NONE) or
            (md.MsgId and md.MsgId != CMQC.MQMI_NONE) or
            (md.CorrelId and md.CorrelId != CMQC.MQCI_NONE)
        )
        if not want_match:
            md.MsgId = CMQC.MQMI_NONE
            md.CorrelId = CMQC.MQCI_NONE
            gmo.MatchOptions = CMQC.MQMO_NONE

    # (2) Vorab-Jitter – optional nur wenn kein WAIT aktiv ist
    do_jitter = _JITTER_MAX_MS > 0
    if _ONLY_NO_WAIT and gmo is not None:
        do_jitter = do_jitter and not (gmo.Options & CMQC.MQGMO_WAIT)
    if do_jitter:
        _sleep_ms(random.randint(_JITTER_MIN_MS, _JITTER_MAX_MS))

    # (3) Original-GET
    try:
        return _ORIG_GET(self, maxlen, md, gmo)
    except MQMIError as e:
        # (4) Backoff bei 2033 (No Message Available), falls konfiguriert
        if (
            e.comp == CMQC.MQCC_FAILED
            and e.reason == CMQC.MQRC_NO_MSG_AVAILABLE
            and _BACKOFF_2033_MS > 0
        ):
            if _DEBUG:
                print(f"[get-jitter] 2033 backoff {_BACKOFF_2033_MS} ms", file=sys.stderr)
            _sleep_ms(_BACKOFF_2033_MS)
        # Fehler unverändert weiterreichen (nicht verschlucken!)
        raise

# Monkeypatch aktivieren (einmalig)
pymqi.Queue.get = _patched_get

if _DEBUG:
    print(
        "[get-jitter] enabled: "
        f"jitter={_JITTER_MIN_MS}-{_JITTER_MAX_MS}ms, "
        f"only_if_no_wait={int(_ONLY_NO_WAIT)}, "
        f"backoff2033={_BACKOFF_2033_MS}ms, "
        f"startup_jitter<={_STARTUP_JITTER_MS}ms, "
        f"clear_match={int(_CLR)}",
        file=sys.stderr
    )
