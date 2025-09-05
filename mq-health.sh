#!/usr/bin/env bash
set -euo pipefail

##### Konfiguration #####
PATTERN="${1:-myscript.py}"               # Python-Skriptname für pgrep
RUNMQSC="${RUNMQSC:-runmqsc}"             # oder absolut: /opt/mqm/bin/runmqsc
QMGR="${QMGR:-QM1}"                       # Queue Manager Name
QUEUE="${QUEUE:-MY.APP.QUEUE}"            # zu prüfende Queue
MQ_TIMEOUT="${MQ_TIMEOUT:-3}"             # Sekunden Timeout für runmqsc
CPU_GRACE="${CPU_GRACE:-0}"               # zusätzliche Jiffies-Schwellwerte, z.B. 0
LOG="${LOG_TARGET:-/proc/1/fd/2}"         # ins Container-Log schreiben (stderr von PID 1)
###########################################

log() { printf '%s\n' "$*" >>"$LOG" 2>/dev/null || true; }

# 1) Python-PID ermitteln (ältester Match)
PID="$(pgrep -fo "python.*${PATTERN}" || true)"
if [ -z "$PID" ]; then
  echo "no python process found for pattern=${PATTERN}"
  log  "HC: no python process for pattern=${PATTERN}"
  exit 1
fi

# 2) CPU-Zeit (utime+stime) robust aus /proc/<pid>/stat lesen
STAT_LINE="$(cat "/proc/${PID}/stat")" || {
  echo "cannot read /proc/${PID}/stat"; log "HC: cannot read /proc/${PID}/stat"; exit 1; }
REST="${STAT_LINE#*) }"; set -- $REST
UTIME="${12}"; STIME="${13}"
TOTAL=$((UTIME + STIME))

STATEFILE="/tmp/py_cpu_prev_${PID}"
PREV="$( [ -f "$STATEFILE" ] && cat "$STATEFILE" || echo "" )"
echo "$TOTAL" > "$STATEFILE"

# 3) IBM MQ Status (CURDEPTH / OPPROCS / IPPROCS) ermitteln
#    Wir kapseln runmqsc mit Timeout, damit der Healthcheck selbst nicht hängen bleibt.
mq_out="$(timeout "${MQ_TIMEOUT}"s sh -c \
  "printf '%s\n' \"DIS QSTATUS(${QUEUE}) TYPE(QUEUE) CURDEPTH OPPROCS IPPROCS\" | ${RUNMQSC} ${QMGR} 2>/dev/null" \
  || true)"

# Parsing: wir holen uns die letzte Zeile mit den Attributen
# Beispieleintrag: "   CURDEPTH(5)  OPPROCS(1)  IPPROCS(0)"
CURDEPTH="$(printf '%s\n' "$mq_out" | grep -Eo 'CURDEPTH\([0-9]+\)' | tail -n1 | tr -dc '0-9')"
OPPROCS="$(printf  '%s\n' "$mq_out" | grep -Eo 'OPPROCS\([0-9]+\)' | tail -n1 | tr -dc '0-9')"
IPPROCS="$(printf  '%s\n' "$mq_out" | grep -Eo 'IPPROCS\([0-9]+\)' | tail -n1 | tr -dc '0-9')"

# Fallbacks, falls runmqsc nicht lieferte:
: "${CURDEPTH:=0}"; : "${OPPROCS:=0}"; : "${IPPROCS:=0}"

# 4) Erstes Sample -> healthy (wir brauchen eine Vergleichsbasis)
if [ -z "$PREV" ]; then
  echo "first sample (ok) curdepth=${CURDEPTH} opprocs=${OPPROCS} ipprocs=${IPPROCS}"
  log  "HC: first sample (ok) pid=${PID} curdepth=${CURDEPTH} opprocs=${OPPROCS} ipprocs=${IPPROCS}"
  exit 0
fi

DELTA=$(( TOTAL - PREV ))

# 5) Entscheidungslogik:
#    - Wenn CPU nicht vorankommt (DELTA <= CPU_GRACE)
#    - UND auf der Queue liegen Nachrichten (CURDEPTH > 0)
#    => unhealthy + Stacktrace via SIGUSR1 anfordern
if [ "$DELTA" -le "$CPU_GRACE" ] && [ "${CURDEPTH}" -gt 0 ]; then
  echo "stalled: cpu delta=${DELTA} curdepth=${CURDEPTH} (pid=${PID})"
  log  "HC: stalled (cpu delta=${DELTA}) with pending msgs (curdepth=${CURDEPTH}) -> USR1"
  kill -s USR1 -- "$PID" || true
  exit 1
fi

# Optional: Wenn keine Consumer auf der Queue sind (OPPROCS=0) und gleichzeitig CURDEPTH wächst,
# könntest du ebenfalls failen. Standardmäßig nur Info-Log:
if [ "${OPPROCS}" -eq 0 ] && [ "${CURDEPTH}" -gt 0 ]; then
  log "HC: warning: curdepth=${CURDEPTH} but opprocs=0 (no consumers?)"
fi

echo "ok: cpu delta=${DELTA} curdepth=${CURDEPTH} opprocs=${OPPROCS} ipprocs=${IPPROCS}"
log  "HC: ok (cpu delta=${DELTA}) curdepth=${CURDEPTH} opprocs=${OPPROCS} ipprocs=${IPPROCS}"
exit 0
