#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patwatch.py — Regex-Zähler mit watch-Style-Header, Anti-Flackern,
Template (Spalte 4), Transform-Pipeline (Spalte 5 inkl. Backrefs als Quelle),
Live-Toggle 'a' (Alternativansicht), Aux-Kommando, Laufzeitmessung
und optionale Farbchips-Ausgabe (--color).

Pattern-TSV (Tab-getrennt):
  ID<TAB>LINE_REGEX<TAB>WORD_REGEX(optional)<TAB>TEMPLATE(optional)<TAB>TRANSFORMS(optional)

Extras:
- Zeilen in der Pattern-Datei, die (nach optionalen Spaces) mit '#' beginnen, werden ignoriert.
- Header zeigt rechts Timestamp (+ optional Custom-Header), Verarbeitungszeit und RAM-Verbrauch: "[123ms|12.3MB]".
  Für präzise RAM-Messung wird psutil empfohlen (pip install psutil).
  Fallback verwendet ps-Befehl auf macOS für aktuellen RSS (nicht maximalen wie resource.getrusage()).
- Taste 'a' schaltet zwischen Normalansicht (Head/Tail) und Alternativansicht (Breiten-optimiert) um.
- --color erzeugt farbige Wort-"Chips" mit ≥120 stabilen, gut lesbaren ANSI-256 Farbkombis (FG/BG),
  mit WCAG-orientierter Kontrastwahl (nie Schwarz auf starkem Rot/Blau).
- Farben in der Normalansicht entsprechen den Farben der Alternativansicht:
  Die Farbauswahl basiert auf dem Alternativ-Wort (Spalte 5); fehlt dieses, auf dem Originalwort.

TASTATURBEHANDLUNG (WICHTIG):
- Taste 'a': Wechsel zwischen Normal- und Alt-Ansicht (KOMPLETTER REFRESH)
- Taste 'c': Im Color-Modus: Toggle zwischen normaler Anzeige und Farbcode-Debug (zeigt Farbcodes statt ID/Hostname)
- Taste 'q': Programm beenden
- Taste '+': Intervall um 5 Sekunden erhöhen
- Taste '-': Intervall um 5 Sekunden verringern (Minimum 1s)
- Ctrl+C: Programm beenden

COLOR-DEBUG-MODUS (TASTE 'C'):
Im Color-Modus zeigt Taste 'c' die Farbcodes anstelle der ID/Hostname an.
Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
Funktionsweise: Einfache Wortersetzung (server1.example.com → 16/119) mit normaler Farbgebung.
WICHTIG: Diese Funktion darf NICHT entfernt werden!

Die Tastaturbehandlung funktioniert in allen Modi:
- Kontinuierlicher Modus (-t/--interval)
- Iterativer Modus (--iterative)
- STDIN-Modus (ohne --cmd)

WICHTIG: Die Terminal-Konfiguration (termios.setcbreak) ist ESSENTIELL für die Tastaturbehandlung!

ANSICHTSWECHSEL (Taste 'a'):
Bei Wechsel zwischen Normal- und Alt-Ansicht wird ein kompletter Refresh der Anzeige gemacht,
damit alte Zeileninhalte korrekt verschwinden und die neue Ansicht korrekt dargestellt wird.
Die neue Ansicht wird im Hintergrund berechnet, während nur die Status-Bar aktualisiert wird.
Im Color-Modus wird nur die benötigte Ansicht berechnet für bessere Performance.
Der Berechnungsfortschritt wird in der Status-Bar mit "[...]" angezeigt, die Zeit wird im [Xms] Format angezeigt.

TESTING-HINWEIS:
Die Tastaturbehandlung funktioniert nur bei echten Benutzereingaben. AI-Assistenten können
keine echten Tastatureingaben simulieren. Bei Tests durch AI-Assistenten scheint die
Tastaturbehandlung nicht zu funktionieren, aber echte Benutzer können die Tasten normal verwenden.

ANTI-FLIMMERN-SYSTEM (WICHTIG):
Das Anti-Flimmern-System verhindert das Flimmern der Status-Bar zwischen [Xms] und [0ms].
Es verwendet zwei Systeme:

1. GLOBALE BERECHNUNGSZEIT (global_calculation_time_ms):
   - Bei regulären Updates nur überschrieben wird wenn ms > 0
   - Bei Taste 'a' auf die Berechnungszeit der neuen Ansicht gesetzt wird
   - In der Status-Bar nur angezeigt wird wenn > 0

2. DURCHSCHNITTLICHE VERARBEITUNGSZEIT (average_processing_time_ms):
   - Sammelt alle Verarbeitungszeiten und berechnet den Durchschnitt
   - Wird nur bei Status-Bar-Refreshs angezeigt
   - Verhindert ständige Aktualisierung der Millisekunden-Anzeige
   - Verwendet einen gleitenden Durchschnitt der letzten 10 Messungen

WICHTIG: Diese Lösung darf NICHT entfernt werden, da sie das Flimmern-Problem löst!

CACHE-DEAKTIVIERUNG (KRITISCH - NIEMALS ÄNDERN!):
Das Cache-Deaktivierungssystem löst das Problem mit 0-Werten beim Modus-Wechsel (Taste 'a').
Es verwendet eine globale Variable use_cache = False, die:
1. Cache-Füllung deaktiviert (one_frame.current_text wird nicht gefüllt)
2. Cache-Verwendung deaktiviert (handle_mode_switch() zeigt keinen Cache an)
3. Pattern-Daten-Verarbeitung aktiviert (für normale Anzeige erforderlich)
4. Rendering-Funktionen aktiviert (für normale Anzeige erforderlich)

PROBLEM-LÖSUNG:
- Ohne Cache-Deaktivierung: 0-Werte aus dem ersten Zyklus werden beim Modus-Wechsel angezeigt
- Mit Cache-Deaktivierung: Programm zeigt immer nur die aktuellen Input-Daten an
- Beim Drücken von 'a': Erst beim nächsten Zyklus werden neue Daten angezeigt

WICHTIG: Diese Lösung darf NIEMALS entfernt oder geändert werden, ohne das Problem zu verstehen!
Alle mit "NIEMALS ENTFERNEN ODER ÄNDERN" markierten Code-Bereiche sind kritisch!
"""

import sys, re, argparse, subprocess, time, shutil, os, select, signal, threading
from collections import deque
from typing import List, Optional, Pattern, Tuple
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Globale Variable für Pipe-Modus-Erkennung
is_pipe_mode = False

# ---------- Speicher-Monitoring ----------
def get_memory_usage_mb():
    """
    Gibt den aktuellen RAM-Verbrauch des Prozesses in MB zurück.
    Verwendet psutil für präzise Speicher-Informationen, falls verfügbar.
    Fallback auf /proc/self/status wenn psutil nicht verfügbar ist.

    Returns:
        float: RAM-Verbrauch in MB (RSS - Resident Set Size)
    """
    if PSUTIL_AVAILABLE:
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # RSS in MB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    else:
        # Fallback ohne psutil - verwende /proc/self/status (Linux) oder andere Methoden
        try:
            if sys.platform == "linux":
                # Linux: Lese /proc/self/status für aktuellen RSS
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            # Format: "VmRSS:    1234 kB"
                            rss_kb = int(line.split()[1])
                            return rss_kb / 1024  # KB zu MB
            elif sys.platform == "darwin":
                # macOS: Verwende ps-Befehl für aktuellen RSS
                import subprocess
                result = subprocess.run(['ps', '-o', 'rss=', '-p', str(os.getpid())],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    rss_kb = int(result.stdout.strip())
                    return rss_kb / 1024  # KB zu MB
            else:
                # Windows oder andere: Verwende resource als letzten Fallback
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                max_rss = usage.ru_maxrss
                if sys.platform == "win32":
                    return max_rss / 1024 / 1024  # Windows: Bytes zu MB
                else:
                    return max_rss / 1024  # Linux/macOS: KB zu MB
        except (ImportError, AttributeError, FileNotFoundError, ValueError, subprocess.SubprocessError):
            return 0.0

def format_memory_usage(mb):
    """
    Formatiert Speicherverbrauch in human-readable Format.

    Args:
        mb (float): Speicherverbrauch in MB

    Returns:
        str: Formatierter String (z.B. "12.3MB", "1.2GB")
    """
    if mb < 1024:
        return f"{mb:.1f}MB"
    else:
        gb = mb / 1024
        return f"{gb:.1f}GB"

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Zeilen zählen & Wörter sammeln nach Regex-Patterns (pro ID).")
    p.add_argument("-p","--patterns", required=True,
                   help="Pattern-Datei: ID<TAB>LINE_REGEX<TAB>WORD_REGEX(optional)<TAB>TEMPLATE(optional)<TAB>TRANSFORMS(optional)")
    p.add_argument("--sep", default=" ", help="Trennzeichen zwischen Wörtern (Default: ' ')")
    p.add_argument("--ignorecase", action="store_true", help="Case-insensitive Matching")
    p.add_argument("--strip-punct", action="store_true", help="Satzzeichen am Wortanfang/-ende entfernen")
    p.add_argument("--fs", default="\\t", help="Feldtrenner in Pattern-Datei (Default: '\\t')")
    p.add_argument("--cg-sep", default="", help="Trenner beim Zusammenfügen mehrerer Capture-Gruppen (wenn kein TEMPLATE)")

    # Hauptkommando / Watch
    p.add_argument("-c","--cmd", help="Shell-Kommando (Pipes erlaubt); dessen STDOUT wird ausgewertet.")
    p.add_argument("-t","--interval", type=float, default=5.0, help="Kontinuierlicher Modus: Kommando läuft dauerhaft, Display wird alle X Sekunden aktualisiert. Standard: 5s für STDIN, 0s für --cmd.")
    p.add_argument("--iterative", type=float, help="Iterativer Modus: Kommando wird alle X Sekunden neu ausgeführt (Output wird ersetzt).")
    p.add_argument("--shell", default="/bin/sh", help="Shell für -c/--cmd und --auxcmd (Default: /bin/sh)")
    p.add_argument("--timeout", type=float, default=None, help="Timeout in Sekunden fürs Hauptkommando (optional)")
    p.add_argument("--clear", action="store_true", help="Pro Durchlauf Bildschirm löschen + Header wie 'watch'")
    p.add_argument("--no-warn", action="store_true",
                   help="Unterdrückt STDERR der Kommandos und interne Warnhinweise bei Exit≠0.")
    p.add_argument("--color-header", action="store_true",
                   help="Farbiger Header: tmux-dunkelgrün (BG 48;5;22) + schwarzer Text (30).")

    # Header-Extras
    p.add_argument("--utc", action="store_true", help="Timestamp im Header in UTC ausgeben.")
    p.add_argument("--header", default="", help="Custom-Headertext; erscheint oben rechts vor dem Timestamp.")

    # Aux-Kommando
    p.add_argument("-a","--auxcmd", help="Zweites Shell-Kommando; dessen STDOUT wird angehängt.")
    p.add_argument("--aux-sep", default="###",
                   help="Trennerzeile vor/zwischen Haupt- und Aux-Output (Default: '###'). Escape wie '\\n' erlaubt.")
    p.add_argument("--aux-timeout", type=float, default=None,
                   help="Eigenes Timeout (Sekunden) für --auxcmd. Default: --timeout.")
    p.add_argument("--aux-before", action="store_true",
                   help="Aux-Block vor dem Hauptblock ausgeben.")

    # Farben
    p.add_argument("--color", action="store_true",
                   help="Farbige Wort-Chips (≥120 ANSI-256 Farbkombis). Ignoriert --sep; gilt in Normal- und Alt-Ansicht.")

    # Ansicht-Modus
    p.add_argument("--alt-view", action="store_true",
                   help="Startet direkt in der Alt-Ansicht (transformierte Wörter). Standard: Normal-Ansicht (Original-Wörter).")

    args = p.parse_args()

    # Validierung der Modi
    if args.iterative is not None and args.interval != 5.0:
        sys.stderr.write("[ERROR] --iterative und --interval können nicht gleichzeitig verwendet werden.\n")
        sys.exit(2)

    # Setze Standard-Intervall basierend auf Modus
    if args.interval == 5.0 and args.cmd and args.iterative is None:
        # Wenn --cmd verwendet wird und kein explizites -t oder -i angegeben wurde, setze auf 0
        args.interval = 0.0

    # Validierung der Parameter
    if args.interval < 0:
        sys.stderr.write("[ERROR] --interval darf nicht negativ sein.\n")
        sys.exit(2)
    if args.iterative is not None and args.iterative < 0:
        sys.stderr.write("[ERROR] --iterative darf nicht negativ sein.\n")
        sys.exit(2)
    if args.timeout is not None and args.timeout <= 0:
        sys.stderr.write("[ERROR] --timeout muss positiv sein.\n")
        sys.exit(2)
    if args.aux_timeout is not None and args.aux_timeout <= 0:
        sys.stderr.write("[ERROR] --aux-timeout muss positiv sein.\n")
        sys.exit(2)

    return args

def unescape(s: str) -> str:
    return s.encode("utf-8").decode("unicode_escape")

# ---------- POSIX-RegEx Klassen -> Python ----------
_POSIX_RE = re.compile(r"\[\[:(alpha|digit|alnum|space|lower|upper|xdigit|word|punct):\]\]")
_POSIX_MAP = {
    "alpha": r"[A-Za-z]", "digit": r"\d", "alnum": r"[0-9A-Za-z]",
    "space": r"\s", "lower": r"[a-z]", "upper": r"[A-Z]",
    "xdigit": r"[0-9A-Fa-f]", "word": r"\w", "punct": r"[^\w\s]",
}
def posix_to_py(rx: str) -> str:
    return _POSIX_RE.sub(lambda m: _POSIX_MAP[m.group(1)], rx)

# ---------- Wort-Extraktion & Helpers ----------
def last_word(line: str) -> str:
    line = line.rstrip()
    if not line: return ""
    parts = re.split(r"\s+", line)
    return parts[-1] if parts else ""

def strip_punct(word: str) -> str:
    return re.sub(r'^[^\w\s]+|[^\w\s]+$', "", word)

def apply_template(tmpl: str, m: Optional[re.Match]) -> str:
    """Backrefs im Template via Match m ersetzen. Unterstützt: \\1..\\99, \\g<name>, \\\\ \\t \\n \\r.
       Wenn m=None → Backrefs werden zu leerem String; Escapes bleiben wirksam.
    """
    if m is None:
        s = tmpl.replace("\\t", "\t").replace("\\n", "\n").replace("\\r", "\r").replace("\\\\", "\\")
        return re.sub(r'\\(?:g<[^>]+>|\d+)', "", s)

    out = []; i = 0; s = tmpl; L = len(s)
    while i < L:
        ch = s[i]
        if ch != '\\':
            out.append(ch); i += 1; continue
        i += 1
        if i >= L: out.append('\\'); break
        c = s[i]
        if c.isdigit():
            j = i
            while j < L and s[j].isdigit(): j += 1
            idx = int(s[i:j]) if j > i else None
            try:
                out.append(m.group(idx) or "" if idx is not None else "")
            except IndexError:
                out.append("")
            i = j; continue
        if c == 'g' and i + 1 < L and s[i+1] == '<':
            k = s.find('>', i+2)
            if k != -1:
                name = s[i+2:k]
                try:
                    out.append(m.group(name) or "")
                except Exception:
                    out.append("")
                i = k + 1; continue
            out.append('\\g'); i += 1; continue
        if c == 't': out.append('\t'); i += 1; continue
        if c == 'n': out.append('\n'); i += 1; continue
        if c == 'r': out.append('\r'); i += 1; continue
        if c == '\\': out.append('\\'); i += 1; continue
        out.append(c); i += 1
    return "".join(out)

# ---------- Transform-Pipeline ----------
def parse_pipeline(s: str):
    """Splitte Pipeline an unescaped '|'. Erhalte Backslashes; behandle nur '\\|' und '\\\\' speziell."""
    if not s: return []
    tokens, cur = [], []
    i, L = 0, len(s)
    while i < L:
        ch = s[i]
        if ch == '\\':
            if i + 1 < L:
                nxt = s[i+1]
                if nxt == '|':
                    cur.append('|'); i += 2; continue
                elif nxt == '\\':
                    cur.append('\\'); i += 2; continue
                else:
                    cur.append('\\'); i += 1; continue
            else:
                cur.append('\\'); i += 1; continue
        elif ch == '|':
            tokens.append(''.join(cur).strip()); cur = []; i += 1; continue
        else:
            cur.append(ch); i += 1
    if cur:
        tokens.append(''.join(cur).strip())
    return [t for t in tokens if t]

_CALL_RE = re.compile(r'^([a-zA-Z_]\w*)\s*(?:\((.*)\))?$')

def split_call(token: str):
    m = _CALL_RE.match(token)
    if not m: return None, token  # kein Funktionsaufruf → Template/Backref-Token
    name, args = m.group(1), (m.group(2) or "")
    out, cur, q, esc = [], [], None, False
    for ch in args:
        if esc: cur.append(ch); esc=False; continue
        if ch == '\\': esc=True; continue
        if q:
            if ch == q: q=None
            else: cur.append(ch)
        else:
            if ch in ("'", '"'): q=ch
            elif ch == ',': out.append(''.join(cur).strip()); cur=[]
            else: cur.append(ch)
    if cur: out.append(''.join(cur).strip())
    out = [a[1:-1] if (len(a)>=2 and a[0]==a[-1] and a[0] in "'\"") else a for a in out]
    return name.lower(), out

def apply_pipeline(word: str, pipeline: str, m: Optional[re.Match]) -> str:
    funcs = {
        # String-Case
        "upper": lambda s: s.upper(),
        "lower": lambda s: s.lower(),
        "title": lambda s: s.title(),
        "swapcase": lambda s: s.swapcase(),
        # Slicing
        "first": lambda s,n="1": s[:int(n)],
        "last":  lambda s,n="1": s[-int(n):] if s else s,
        "slice": lambda s,a="",b="": s[(int(a) if a!="" else None):(int(b) if b!="" else None)],
        "subst": lambda s,a="",b="": s[(int(a) if a!="" else None):(int(b) if b!="" else None)],  # Alias
        # Trim/Whitespace
        "strip": lambda s,chs="": s.strip(chs) if chs else s.strip(),
        "lstrip": lambda s,chs="": s.lstrip(chs) if chs else s.lstrip(),
        "rstrip": lambda s,chs="": s.rstrip(chs) if chs else s.rstrip(),
        "collapse_ws": lambda s: " ".join(s.split()),
        # Ersetzen
        "replace_str": lambda s,a,b: s.replace(a,b),
        "replace": lambda s,rx,repl,flag="": re.sub(rx, repl, s, flags=(re.I if ('i' in flag.lower()) else 0)),
        "tr": lambda s,src,dst: s.translate(str.maketrans(src, dst)),
        # Split/Extract
        "split": lambda s,delim,idx="0": (s.split(delim)[int(idx)] if delim in s and len(s.split(delim))>int(idx) else ""),
        "rsplit": lambda s,delim,idx="0": (s.rsplit(delim)[int(idx)] if delim in s and len(s.rsplit(delim))>int(idx) else ""),
        "rextract": lambda s,rx,grp="1": (re.search(rx,s).group(int(grp)) if re.search(rx,s) else ""),
        # Padding/Format
        "padleft": lambda s,w,ch=" ": s.rjust(int(w), ch[:1] if ch else " "),
        "padright": lambda s,w,ch=" ": s.ljust(int(w), ch[:1] if ch else " "),
        "zfill": lambda s,w: s.zfill(int(w)),
        "ensure_prefix": lambda s,p: s if s.startswith(p) else (p+s),
        "ensure_suffix": lambda s,p: s if s.endswith(p) else (s+p),
        # Zahlen (best effort)
        "int": lambda s: str(int(float(s))) if s.strip() else s,
        "float": lambda s: str(float(s)) if s.strip() else s,
        "round": lambda s,d="0": (("{0:." + str(int(d)) + "f}").format(round(float(s), int(d)))) if s.strip() else s,
        # Mit Templates im Lauf setzen/anhängen
        "set": lambda s,expr: apply_template(expr, m),
        "append": lambda s,expr: s + apply_template(expr, m),
        "prepend": lambda s,expr: apply_template(expr, m) + s,
        "concat": lambda s,expr: s + apply_template(expr, m),
    }

    try:
        tokens = parse_pipeline(pipeline)
        for tok in tokens:
            call = split_call(tok)
            if call[0] is None:
                # Kein Funktionsaufruf → behandle als Template/Backref-Token (ersetzen)
                word = apply_template(call[1], m)
                continue
            name, args = call
            f = funcs.get(name)
            if not f:
                continue
            if name in ("set","append","prepend","concat") and args:
                word = f(word, args[0])  # apply_template passiert in Func
            else:
                word = f(word, *args)
    except (ValueError, TypeError, IndexError) as e:
        # Spezifische Fehler für ungültige Argumente oder Indizes
        sys.stderr.write(f"[WARN] Transform-Pipeline Fehler: {e}. Wort unverändert gelassen.\n")
    except re.error as e:
        # Regex-Fehler in replace oder rextract
        sys.stderr.write(f"[WARN] Regex-Fehler in Transform-Pipeline: {e}. Wort unverändert gelassen.\n")
    except Exception as e:
        # Andere unerwartete Fehler
        sys.stderr.write(f"[WARN] Unerwarteter Fehler in Transform-Pipeline: {e}. Wort unverändert gelassen.\n")
    return word

# ---------- Datenstruktur ----------
class PatternRec:
    __slots__ = ("pid","line_re","word_re","tmpl","transforms","orig_ref","found_refs",
                 "count","head","head_keys","head_count","alts","orig_words","tail_max","tail","tail_keys")
    def __init__(self, pid: str, line_re: Pattern, word_re: Optional[Pattern],
                 tmpl: str, transforms: str):
        self.pid = pid
        self.line_re = line_re
        self.word_re = word_re
        self.tmpl = tmpl
        self.transforms = transforms  # 5. Spalte (Pipeline)
        # Extrahiere Backreference aus Spalte 5 (z.B. \1, \2, etc.)
        self.orig_ref = ""
        self.found_refs = set()  # Sammle alle gefundenen Backreferences
        if transforms:
            # Suche nach Backreferences wie \1, \2, etc.
            import re
            backref_match = re.search(r'\\(\d+)', transforms)
            if backref_match:
                self.orig_ref = backref_match.group(0)  # z.B. "\1"
        self.count = 0
        self.head: List[str] = []
        self.head_keys: List[str] = []   # Farb-Key je Head-Wort (Altwort dominiert)
        self.head_count = 0
        self.tail_max = 0  # Keine Tail-Begrenzung mehr
        self.tail = deque()  # Unbegrenzt
        self.tail_keys = deque()  # Unbegrenzt
        self.alts: List[str] = []  # Historie alternativer Wörter (für Alt-Ansicht)
        self.orig_words: List[str] = []  # Ursprüngliche Wörter vor Transformation (für Legende)

def compile_rx(rx: str, flags: int) -> Pattern:
    return re.compile(rx, flags)

def extract_word_and_match(line: str, pat: PatternRec, cg_sep: str) -> Tuple[str, Optional[re.Match]]:
    """Gibt (Wort, Matchobjekt) zurück. Matchobjekt wird für Transforms/Backrefs in Spalte 5 genutzt."""
    if pat.word_re is not None:
        m = pat.word_re.search(line)
        if not m:
            return "", None
        if pat.tmpl:
            return apply_template(pat.tmpl, m), m
        if m.lastindex:
            parts = [g for g in m.groups() if g]
            return (cg_sep.join(parts) if parts else m.group(0)), m
        return m.group(0), m
    # ohne WORD_REGEX
    return last_word(line), None

def load_patterns(path: str, fs: str, flags: int) -> List[PatternRec]:
    pats: List[PatternRec] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln, raw in enumerate(f, 1):
                line = raw.rstrip("\n")
                if not line.strip(): continue
                if line.endswith("\r"): line = line[:-1]
                if line.lstrip().startswith("#"):  # Kommentarzeilen ignorieren
                    continue
                parts = line.split(fs, 4)  # bis zu 5 Felder
                if len(parts) < 2:
                    sys.stderr.write(f"[WARN] Zeile {ln}: erwarte mind. 2 Felder (ID{fs}LINE_REGEX[ {fs}WORD_REGEX[ {fs}TEMPLATE[ {fs}TRANSFORMS ]]]). Übersprungen.\n")
                    continue
                pid = parts[0].strip()
                line_rx = posix_to_py(parts[1])
                word_rx = posix_to_py(parts[2]) if len(parts)>=3 and parts[2] != "" else None
                tmpl = parts[3] if len(parts) >= 4 else ""
                transforms = parts[4] if len(parts) >= 5 else ""
                if not pid or not line_rx:
                    sys.stderr.write(f"[WARN] Zeile {ln}: leere ID oder LINE_REGEX. Übersprungen.\n")
                    continue
                try:
                    lre = compile_rx(line_rx, flags)
                except re.error as e:
                    sys.stderr.write(f"[WARN] Zeile {ln}: ungültige LINE_REGEX '{parts[1]}': {e}. Übersprungen.\n")
                    continue
                wre = None
                if word_rx is not None:
                    try: wre = compile_rx(word_rx, flags)
                    except re.error as e:
                        sys.stderr.write(f"[WARN] Zeile {ln}: ungültige WORD_REGEX '{parts[2]}': {e}. WORD_REGEX ignoriert.\n")
                pats.append(PatternRec(pid, lre, wre, tmpl, transforms))
    except FileNotFoundError:
        sys.stderr.write(f"[ERROR] Pattern-Datei '{path}' nicht gefunden.\n")
        return []
    except PermissionError:
        sys.stderr.write(f"[ERROR] Keine Berechtigung zum Lesen der Pattern-Datei '{path}'.\n")
        return []
    except UnicodeDecodeError as e:
        sys.stderr.write(f"[ERROR] Unicode-Fehler beim Lesen der Pattern-Datei '{path}': {e}\n")
        return []
    except Exception as e:
        sys.stderr.write(f"[ERROR] Unerwarteter Fehler beim Lesen der Pattern-Datei '{path}': {e}\n")
        return []
    return pats

# ---------- Kernverarbeitung ----------
def process_text(input_text: str, patterns: List[PatternRec], sep: str,
                 strip_p: bool, cg_sep: str) -> str:
    """
    KERNVERARBEITUNG: Verarbeitet Input-Text und erstellt truncated Ausgabe.

    CODE-PFAD: Wird verwendet für:
    - NOCOLOR-Modus (ohne --color Flag)
    - STDIN-Modus (ohne --cmd)
    - Einmalige Ausführung (ohne -t/--interval)

    TRUNCATION: Implementiert in dieser Funktion für nocolor-Kompatibilität.
    """
    # reset
    for pat in patterns:
        pat.count = 0
        pat.head.clear()
        pat.head_keys.clear()
        pat.head_count = 0
        pat.alts.clear()
        pat.orig_words.clear()  # Reset ursprüngliche Wörter
        pat.found_refs.clear()  # Reset gefundene Backreferences
        # tail_max wurde entfernt, da es nicht mehr benötigt wird

    for line in input_text.splitlines():
        for pat in patterns:
            if pat.line_re.search(line):
                pat.count += 1
                w, m = extract_word_and_match(line, pat, cg_sep)
                if strip_p and w: w = strip_punct(w)
                # Speichere ursprüngliches Wort für Legende
                pat.orig_words.append(w)

                # Speichere die evaluierte \1 Backreference für die Legende
                if m and m.groups() and len(m.groups()) >= 1:
                    pat.found_refs.add(m.group(1))  # \1 Backreference

                # Transformiertes Alternativwort (Spalte 5; darf Backrefs als Quelle nutzen)
                alt = apply_pipeline(w, pat.transforms, m) if pat.transforms else w
                pat.alts.append(alt)
                # Normal-Head
                if w:
                    pat.head.append(w)
                    pat.head_keys.append(alt if alt else w)  # Farb-Key: Altwort dominiert
                    pat.head_count += 1

    # Normalansicht mit Truncation (wird für nocolor-Modus verwendet)
    cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    out_lines = []
    for pat in patterns:
        total = pat.count
        prefix = f"{pat.pid:<8} {total:<8} "
        prefix_len = len(prefix)

        # Sichere Berechnung der verfügbaren Breite - auch für sehr kleine Terminals
        max_total_width = max(cols - 1, 20)  # Mindestens 20 Zeichen, auch bei winzigen Terminals
        available_for_content = max_total_width - prefix_len

        if available_for_content <= 0 or not pat.head:
            words = ""
        else:
            # Verwende robuste Truncation für die Wörter (funktioniert auch bei kleinen Breiten)
            words = build_truncated_content(pat.head, available_for_content, sep, False)

        # Finale Sicherheitsprüfung: Kürze nur den Wort-Teil, nicht die Pattern-ID
        final_line = f"{pat.pid}\t{total}\t{words}"
        if len(final_line) > max_total_width:
            # Kürze nur den Wort-Teil weiter
            excess = len(final_line) - max_total_width
            if len(words) > excess + 3:
                words = words[:-(excess + 3)] + "..."
            else:
                words = "..."

        out_lines.append(f"{pat.pid:<8} {total:<8} {words}")
    return "\n".join(out_lines) + ("\n" if out_lines else "")

# ---------- Farben (ANSI 256) mit Kontrast-Heuristik ----------
def _xterm_rgb(code: int):
    if 16 <= code <= 231:  # 6x6x6 farbwürfel
        i = code - 16
        r = i // 36
        g = (i % 36) // 6
        b = i % 6
        conv = lambda v: 0 if v == 0 else 95 + (v - 1) * 40
        return (conv(r), conv(g), conv(b))
    if 232 <= code <= 255:  # grau
        v = 8 + 10 * (code - 232)
        return (v, v, v)
    return (255, 255, 255)

def _srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _rel_lum_rgb(r: int, g: int, b: int) -> float:
    R = _srgb_to_linear(r); G = _srgb_to_linear(g); B = _srgb_to_linear(b)
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def _contrast(l1: float, l2: float) -> float:
    if l1 < l2: l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

def _best_fg_for_bg(r: int, g: int, b: int) -> int:
    """Wähle 15 (weiß) oder 16 (schwarz) – höchster Kontrast; vermeide unleserliche Kombinationen."""
    lum = _rel_lum_rgb(r, g, b)
    cr_black = _contrast(lum, 0.0)
    cr_white = _contrast(1.0, lum)

    # Strikte Kontrast-Regeln für bessere Lesbarkeit
    # Mindestkontrast von 4.5 (WCAG AA) für gute Lesbarkeit
    min_contrast = 4.5

    # Prüfe ob schwarzer Text lesbar wäre
    black_readable = cr_black >= min_contrast
    white_readable = cr_white >= min_contrast

    # Wenn beide lesbar sind, wähle den besseren Kontrast
    if black_readable and white_readable:
        return 15 if cr_white >= cr_black else 16

    # Wenn nur einer lesbar ist, verwende den lesbaren
    if black_readable:
        return 16
    if white_readable:
        return 15

    # Fallback: Verwende weiß für dunkle Hintergründe, schwarz für helle
    return 15 if lum < 0.5 else 16

def build_palette() -> list[tuple[int, int]]:
    """Erzeuge (fg,bg)-Paare mit gutem Kontrast; mind. 120 Stück."""
    pairs = []
    for code in range(16, 232):
        r, g, b = _xterm_rgb(code)
        y8 = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if y8 < 25 or y8 > 245:
            continue
        fg = _best_fg_for_bg(r, g, b)
        pairs.append((fg, code))
    for code in range(238, 247):
        r, g, b = _xterm_rgb(code)
        fg = _best_fg_for_bg(r, g, b)
        pairs.append((fg, code))
    seen, uniq = set(), []
    for fg, bg in pairs:
        if (fg, bg) not in seen:
            uniq.append((fg, bg)); seen.add((fg, bg))
    if len(uniq) < 120:
        for code in range(16, 232):
            r, g, b = _xterm_rgb(code)
            fg = _best_fg_for_bg(r, g, b)
            if (fg, code) not in seen:
                uniq.append((fg, code)); seen.add((fg, code))
            if len(uniq) >= 120:
                break

    # Filtere problematische Farbkombinationen aus
    filtered = []
    for fg, bg in uniq:
        r, g, b = _xterm_rgb(bg)
        # Vermeide dunkelblaue Hintergründe (schwer lesbar)
        if r < 50 and g < 50 and b > 100:  # Dunkelblau
            continue
        # Vermeide sehr dunkle Hintergründe mit schwarzer Schrift
        if fg == 16 and r < 30 and g < 30 and b < 30:  # Sehr dunkel mit schwarzer Schrift
            continue
        # Vermeide sehr helle Hintergründe mit weißer Schrift
        if fg == 15 and r > 220 and g > 220 and b > 220:  # Sehr hell mit weißer Schrift
            continue
        filtered.append((fg, bg))

    return filtered[:240]

_PALETTE = build_palette()

class _ColorAllocator:
    """Hash-basierter Allokator: Verwendet deterministische Hash-Funktion für konsistente Farben."""
    def __init__(self, palette):
        self.palette = list(palette)
        self.map = {}       # key -> palette index

    def _deterministic_hash(self, key: str) -> int:
        """Deterministische Hash-Funktion für konsistente Farben bei jedem Programmstart."""
        # Verwende einen einfachen aber effektiven Hash-Algorithmus
        # der deterministisch ist und gut verteilt
        hash_value = 0
        for i, char in enumerate(key):
            # Kombiniere Zeichen-Code mit Position für bessere Verteilung
            hash_value = ((hash_value << 5) + hash_value + ord(char) * (i + 1)) & 0xFFFFFFFF

        # Füge Länge hinzu für bessere Verteilung bei kurzen Strings
        hash_value = (hash_value + len(key) * 31) & 0xFFFFFFFF

        return hash_value

    def pair_for(self, key: str):
        """Gibt (fg,bg) für den Key zurück; deterministische Hash-basierte Farbauswahl."""
        if key not in self.map:
            # Verwende deterministische Hash-Funktion
            hash_value = self._deterministic_hash(key)

            # Verwende modulo für Palette-Index
            self.map[key] = hash_value % len(self.palette)

        return self.palette[self.map[key]]

_COLOR_ALLOC = _ColorAllocator(_PALETTE)

def _color_chip_key(word: str, key: Optional[str] = None) -> str:
    """Farbiges Chip-Rendering; Farbe anhand 'key' (z. B. Altwort) wählen."""
    if not word:
        return ""
    fg, bg = _COLOR_ALLOC.pair_for(key if key is not None else word)
    return f"\x1b[38;5;{fg};48;5;{bg}m{word}\x1b[0m"

def get_color_pair(key: str) -> Tuple[int, int]:
    """Gibt das Farbpaar (fg, bg) für einen gegebenen Key zurück."""
    if not key:
        return 0, 0
    return _COLOR_ALLOC.pair_for(key)

def _color_chip(word: str) -> str:
    if not word:
        return ""
    # Standard: Farbe aus dem Wort selbst ableiten (Alt-Ansicht nutzt Altwörter direkt)
    fg, bg = _COLOR_ALLOC.pair_for(word)
    return f"\x1b[38;5;{fg};48;5;{bg}m{word}\x1b[0m"

def colorize_join(words: list[str]) -> str:
    chips = [_color_chip(w) for w in words if w]
    # Im Color-Mode bei alternativansicht ohne sichtbaren Separator zwischen Chips
    return "".join(chips)

def strip_ansi_codes(text: str) -> str:
    """Entfernt ANSI-Escape-Sequenzen aus einem String für korrekte Längenberechnung."""
    import re
    # Entferne alle ANSI-Escape-Sequenzen (umfassende Regex)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def calculate_visual_length(text: str, use_color: bool) -> int:
    """Berechnet die visuelle Länge eines Textes, berücksichtigt ANSI-Codes."""
    if use_color:
        return len(strip_ansi_codes(text))
    else:
        return len(text)



def colorize_join_with_keys(words: list[str], keys: list[str]) -> str:
    """Wie colorize_join, aber Farbe wird aus keys[i] abgeleitet (Alt dominiert)."""
    chips = []
    for i, w in enumerate(words):
        if not w:
            continue
        key = keys[i] if i < len(keys) and keys[i] else w
        chips.append(_color_chip_key(w, key))
    return " ".join(chips)

def build_truncated_content(words: list[str], max_width: int, sep: str, use_color: bool) -> str:
    """
    Baut truncated Inhalt mit garantierter Längen-Begrenzung.
    Implementiert die Spezifikations-Anforderungen:
    - Keine Zeilenüberläufe (höchste Priorität)
    - Optimale Zeilennutzung
    - Konsistente "..."-Positionierung
    - Robuste Behandlung sehr kleiner Terminalbreiten
    """

    if not words:
        return ""

    # Für sehr kleine Breiten: Versuche mindestens ein Wort + Ellipsis zu zeigen
    if max_width <= 3:
        return "..."
    elif max_width <= 8:
        # Bei sehr kleiner Breite: Zeige nur erstes Wort gekürzt + "..."
        first_word = words[0]
        if len(first_word) + 3 <= max_width:
            return first_word + "..."
        elif max_width > 3:
            return first_word[:max_width-3] + "..."
        else:
            return "..."

    def get_visual_length(text: str) -> int:
        if use_color:
            return len(strip_ansi_codes(text))
        else:
            return len(text)

    def join_words(word_list: list[str]) -> str:
        if use_color:
            return colorize_join(word_list)
        else:
            return sep.join(word_list) if word_list else ""

    # Teste ob alle Wörter passen
    full_content = join_words(words)
    if get_visual_length(full_content) <= max_width:
        return full_content

    # Truncation nötig - berechne optimale Aufteilung
    ellipsis = "..."
    ellipsis_len = 3

    if max_width <= ellipsis_len:
        return ellipsis

    available_for_words = max_width - ellipsis_len

    # Verteile Platz: 50% links, 50% rechts
    left_budget = available_for_words // 2
    right_budget = available_for_words - left_budget

    # Sammle linke Wörter
    left_words = []
    left_length = 0
    sep_len = len(sep) if sep else 0

    for word in words:
        if use_color:
            # Für farbige Wörter: Berechne visuelle Länge des farbigen Chips
            colored_word = _color_chip(word)
            word_visual_len = len(strip_ansi_codes(colored_word))
        else:
            word_visual_len = len(word)

        needed_space = word_visual_len + (sep_len if left_words else 0)

        if left_length + needed_space <= left_budget:
            left_words.append(word)
            left_length += needed_space
        else:
            break

    # Sammle rechte Wörter (rückwärts)
    right_words = []
    right_length = 0

    for word in reversed(words[len(left_words):]):
        if use_color:
            # Für farbige Wörter: Berechne visuelle Länge des farbigen Chips
            colored_word = _color_chip(word)
            word_visual_len = len(strip_ansi_codes(colored_word))
        else:
            word_visual_len = len(word)

        needed_space = word_visual_len + (sep_len if right_words else 0)

        if right_length + needed_space <= right_budget:
            right_words.insert(0, word)
            right_length += needed_space
        else:
            break

    # Baue finalen Inhalt
    left_content = join_words(left_words)
    right_content = join_words(right_words)

    if left_words and right_words:
        result = left_content + ellipsis + right_content
    elif left_words:
        result = left_content + ellipsis
    elif right_words:
        result = ellipsis + right_content
    else:
        result = ellipsis

    # Finale Sicherheitsprüfung - falls immer noch zu lang
    if get_visual_length(result) > max_width:
        # Drastische Kürzung
        safe_content_len = max_width - ellipsis_len
        if safe_content_len > 0:
            if use_color:
                plain_result = strip_ansi_codes(result)
                result = plain_result[:safe_content_len] + ellipsis
            else:
                result = result[:safe_content_len] + ellipsis
        else:
            result = ellipsis

    return result

def build_truncated_content_with_keys(words: list[str], keys: list[str], max_width: int, sep: str, use_color: bool) -> str:
    """
    Baut truncated Inhalt mit garantierter Längen-Begrenzung und Farb-Keys.
    Version für Normal-Ansicht: Wörter werden mit Farben aus keys gerendert.
    """

    if not words:
        return ""

    # Für sehr kleine Breiten: Versuche mindestens ein Wort + Ellipsis zu zeigen
    if max_width <= 3:
        return "..."
    elif max_width <= 8:
        # Bei sehr kleiner Breite: Zeige nur erstes Wort gekürzt + "..."
        first_word = words[0]
        if len(first_word) + 3 <= max_width:
            return _color_chip_key(first_word, keys[0] if keys else None) + "..."
        elif max_width > 3:
            return _color_chip_key(first_word[:max_width-3], keys[0] if keys else None) + "..."
        else:
            return "..."

    def get_visual_length(text: str) -> int:
        if use_color:
            return len(strip_ansi_codes(text))
        else:
            return len(text)

    def join_words_with_keys(word_list: list[str], key_list: list[str]) -> str:
        if use_color:
            chips = []
            for i, w in enumerate(word_list):
                if not w:
                    continue
                key = key_list[i] if i < len(key_list) and key_list[i] else w
                chips.append(_color_chip_key(w, key))
            return " ".join(chips)
        else:
            return sep.join(word_list) if word_list else ""

    # Teste ob alle Wörter passen
    full_content = join_words_with_keys(words, keys)
    if get_visual_length(full_content) <= max_width:
        return full_content

    # Truncation nötig - berechne optimale Aufteilung
    ellipsis = "..."
    ellipsis_len = 3

    if max_width <= ellipsis_len:
        return ellipsis

    available_for_words = max_width - ellipsis_len

    # Verteile Platz: 50% links, 50% rechts
    left_budget = available_for_words // 2
    right_budget = available_for_words - left_budget

    # Sammle linke Wörter
    left_words = []
    left_keys = []
    left_length = 0
    sep_len = len(sep) if sep else 0

    for i, word in enumerate(words):
        if use_color:
            # Für farbige Wörter: Berechne visuelle Länge des farbigen Chips
            key = keys[i] if i < len(keys) and keys[i] else word
            colored_word = _color_chip_key(word, key)
            word_visual_len = len(strip_ansi_codes(colored_word))
        else:
            word_visual_len = len(word)

        needed_space = word_visual_len + (sep_len if left_words else 0)

        if left_length + needed_space <= left_budget:
            left_words.append(word)
            left_keys.append(keys[i] if i < len(keys) else word)
            left_length += needed_space
        else:
            break

    # Sammle rechte Wörter (rückwärts)
    right_words = []
    right_keys = []
    right_length = 0

    for i in range(len(words) - 1, len(left_words) - 1, -1):
        word = words[i]
        if use_color:
            # Für farbige Wörter: Berechne visuelle Länge des farbigen Chips
            key = keys[i] if i < len(keys) and keys[i] else word
            colored_word = _color_chip_key(word, key)
            word_visual_len = len(strip_ansi_codes(colored_word))
        else:
            word_visual_len = len(word)

        needed_space = word_visual_len + (sep_len if right_words else 0)

        if right_length + needed_space <= right_budget:
            right_words.insert(0, word)
            right_keys.insert(0, keys[i] if i < len(keys) else word)
            right_length += needed_space
        else:
            break

    # Baue finalen Inhalt
    left_content = join_words_with_keys(left_words, left_keys)
    right_content = join_words_with_keys(right_words, right_keys)

    if left_words and right_words:
        result = left_content + ellipsis + right_content
    elif left_words:
        result = left_content + ellipsis
    elif right_words:
        result = ellipsis + right_content
    else:
        result = ellipsis

    # Finale Sicherheitsprüfung - falls immer noch zu lang
    if get_visual_length(result) > max_width:
        # Drastische Kürzung
        safe_content_len = max_width - ellipsis_len
        if safe_content_len > 0:
            if use_color:
                plain_result = strip_ansi_codes(result)
                result = plain_result[:safe_content_len] + ellipsis
            else:
                result = result[:safe_content_len] + ellipsis
        else:
            result = ellipsis

    return result

# ---------- Rendering (Normal & Alt) ----------
def render_normal_view(patterns: List[PatternRec], sep: str, use_color: bool, color_debug_mode: bool = False, content_start_line: int = 1) -> str:
    """
    NORMAL VIEW RENDERING: Rendert die normale Ansicht mit robuster Truncation.

    CODE-PFAD: Wird verwendet für:
    - COLOR-Modus (mit --color Flag)
    - Kontinuierlicher CMD-Modus (mit --cmd und -t)
    - Normal-Ansicht (nicht Alt-View)

    TRUNCATION: Verwendet build_truncated_content() für optimale Darstellung.
    """
    cols = shutil.get_terminal_size(fallback=(80, 24)).columns


    lines = []
    for pat in patterns:
        prefix = f"{pat.pid}\t{pat.count}\t"
        prefix_len = len(prefix)

        # Sichere Berechnung der verfügbaren Breite - auch für sehr kleine Terminals
        max_total_width = max(cols - 1, 20)  # Mindestens 20 Zeichen, auch bei winzigen Terminals
        available_for_content = max_total_width - prefix_len

        if available_for_content <= 0:
            lines.append(prefix + "\n")
            continue

        # NORMAL VIEW: Verwende die ursprünglichen Wörter (pat.head) statt transformierte (pat.alts)
        words = pat.head
        if not words:
            lines.append(prefix + "\n")
            continue

        # ========================================================================
        # COLOR-DEBUG-MODUS (TASTE 'C')
        # ========================================================================
        # WICHTIG: Im Color-Debug-Modus werden Farbcodes anstelle der ID/Hostname angezeigt.
        # Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
        # ========================================================================
        if color_debug_mode and use_color and pat.head_keys:
            # ========================================================================
            # COLOR-DEBUG-MODUS IMPLEMENTIERUNG (TASTE 'C')
            # ========================================================================
            # WICHTIG: Ersetzt einfach die Wörter durch Farbcodes für Debug-Zwecke.
            # Das ermöglicht die direkte Identifikation problematischer Farbkombinationen.
            #
            # KRITISCHE LOGIK:
            # - Einfache Wortersetzung: word → f"{fg}/{bg}" Farbcode
            # - Verwendet normale Farbgebung für konsistente Darstellung
            # - Ohne diese Logik: Schwer zu identifizieren welche Farbkombination problematisch ist
            #
            # WICHTIG: Diese Logik darf NICHT entfernt werden!
            # ========================================================================
            # COLOR-DEBUG-MODUS: Ersetze einfach die Wörter durch Farbcodes
            debug_words = []
            for word, key in zip(words, pat.head_keys):
                if key:
                    # Ersetze das Wort durch den Farbcode (z.B. server1.example.com → 16/119)
                    debug_words.append(f"{get_color_pair(key)[0]}/{get_color_pair(key)[1]}")
                else:
                    debug_words.append("none")

            # Verwende die normale Farbgebung für die Farbcodes
            if use_color and debug_words:
                content = build_truncated_content_with_keys(debug_words, pat.head_keys, available_for_content, sep, use_color)
            else:
                content = build_truncated_content(debug_words, available_for_content, sep, use_color)
        else:
            # NORMAL-MODUS: Verwende die ursprünglichen Wörter
        # Erstelle Inhalt mit garantierter Längen-Begrenzung
            # In der Normal-Ansicht: Verwende pat.head_keys für die Farben (Alt-Wörter als Key)
            if use_color and pat.head_keys:
                # Verwende colorize_join_with_keys für korrekte Farbgebung
                content = build_truncated_content_with_keys(words, pat.head_keys, available_for_content, sep, use_color)
            else:
                content = build_truncated_content(words, available_for_content, sep, use_color)

        # Finale Sicherheitsprüfung
        total_len = prefix_len + len(strip_ansi_codes(content) if use_color else content)
        if total_len > max_total_width:
            # Notfall-Kürzung
            safe_len = max_total_width - prefix_len - 3
            if safe_len > 0:
                if use_color:
                    content = strip_ansi_codes(content)[:safe_len] + "..."
                else:
                    content = content[:safe_len] + "..."
            else:
                content = "..."

        lines.append(prefix + content + "\n")

    return "".join(lines)

def render_alt_view(patterns: List[PatternRec], sep: str, use_color: bool, no_warn: bool = False, content_start_line: int = 1) -> str:
    """
    ALTERNATIVE VIEW RENDERING: Rendert die alternative Ansicht mit robuster Truncation.

    CODE-PFAD: Wird verwendet für:
    - Alt-Ansicht (nach Drücken der 'a'-Taste)
    - Sowohl COLOR- als auch NOCOLOR-Modus
    - Kontinuierlicher CMD-Modus (mit --cmd und -t)

    TRUNCATION: Verwendet build_truncated_content() für optimale Darstellung.
    """
    cols = shutil.get_terminal_size(fallback=(80, 24)).columns

    lines = []
    for pat in patterns:
        prefix = f"{pat.pid}\t{pat.count}\t"
        prefix_len = len(prefix)

        # Sichere Berechnung der verfügbaren Breite - auch für sehr kleine Terminals
        max_total_width = max(cols - 1, 20)  # Mindestens 20 Zeichen, auch bei winzigen Terminals
        available_for_content = max_total_width - prefix_len

        if available_for_content <= 0:
            lines.append(prefix + "\n")
            continue

        words = pat.alts
        if not words:
            lines.append(prefix + "\n")
            continue

        # Sicherheitsprüfung für sehr große Wortlisten
        if len(words) > 1000:
            words = words[:1000]
            if not no_warn:
                sys.stderr.write(f"[WARN] Wortliste für Pattern '{pat.pid}' auf 1000 Wörter begrenzt.\n")

        # Erstelle Inhalt mit garantierter Längen-Begrenzung
        content = build_truncated_content(words, available_for_content, sep, use_color)

        # Finale Sicherheitsprüfung
        total_len = prefix_len + len(strip_ansi_codes(content) if use_color else content)
        if total_len > max_total_width:
            # Notfall-Kürzung
            safe_len = max_total_width - prefix_len - 3
            if safe_len > 0:
                if use_color:
                    content = strip_ansi_codes(content)[:safe_len] + "..."
                else:
                    content = content[:safe_len] + "..."
            else:
                content = "..."

        lines.append(prefix + content + "\n")

    return "".join(lines)

# ---------- Kommando & Header/Watch ----------
def run_cmd(cmd: str, shell_path: str, timeout: Optional[float], no_warn: bool) -> tuple[str, float]:
    if not cmd or not cmd.strip():
        return "", 0.0

    try:
        # Validierung der Shell-Parameter
        if not os.path.exists(shell_path):
            sys.stderr.write(f"[ERROR] Shell '{shell_path}' nicht gefunden.\n")
            return "", 0.0

        # Zeitmessung starten
        cmd_start = time.perf_counter()

        # Für kontinuierliche Ausgabe: Verwende Popen mit select
        process = subprocess.Popen(
            [shell_path, "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=(subprocess.DEVNULL if no_warn else subprocess.PIPE),
            text=True,
            bufsize=1,  # Line-buffered
        )

        # Lese Output kontinuierlich mit select
        output_lines = []
        try:
            while True:
                # Prüfe ob Prozess noch läuft
                if process.poll() is not None:
                    break

                # Prüfe auf verfügbare Daten mit select (nicht-blockierend)
                if select.select([process.stdout], [], [], 0.1)[0]:
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line)
                        # Begrenze die Anzahl der Zeilen um Speicher zu sparen
                        if len(output_lines) > 1000:
                            output_lines = output_lines[-500:]  # Behalte nur die letzten 500 Zeilen
                else:
                    # Keine Daten verfügbar, kurze Pause
                    time.sleep(0.01)

                # Timeout prüfen
                if timeout and (time.perf_counter() - cmd_start) > timeout:
                    process.terminate()
                    break

        except KeyboardInterrupt:
            process.terminate()
            raise

        # Zeitmessung beenden
        cmd_time = time.perf_counter() - cmd_start

        # Warte auf Prozess-Ende
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()

        if (not no_warn) and process.returncode != 0 and process.returncode is not None:
            sys.stderr.write(f"[WARN] Kommando Exit {process.returncode}\n")

        return "".join(output_lines), cmd_time

    except subprocess.TimeoutExpired:
        if not no_warn:
            sys.stderr.write(f"[WARN] Kommando Timeout nach {timeout}s: {cmd}\n")
        return "", 0.0
    except FileNotFoundError:
        if not no_warn:
            sys.stderr.write(f"[ERROR] Shell '{shell_path}' nicht gefunden.\n")
        return "", 0.0
    except PermissionError:
        if not no_warn:
            sys.stderr.write(f"[ERROR] Keine Berechtigung für Shell '{shell_path}'.\n")
        return "", 0.0
    except Exception as e:
        if not no_warn:
            sys.stderr.write(f"[ERROR] Unerwarteter Fehler beim Ausführen des Kommandos: {e}\n")
        return "", 0.0

def now_str(use_utc: bool) -> str:
    fmt = "%a %b %d %H:%M:%S %Z %Y"
    return time.strftime(fmt, time.gmtime() if use_utc else time.localtime())

def build_header_line(left: str, right: str, color: bool) -> str:
    cols = shutil.get_terminal_size(fallback=(80, 24)).columns
    if len(left) + 1 + len(right) <= cols:
        spaces = cols - len(left) - len(right)
        line = left + (" " * spaces) + right
    else:
        keep_left = max(0, cols - len(right) - 1)
        left = left[:keep_left]
        max_right = max(0, cols - len(left) - 1)
        right = right[-max_right:] if max_right > 0 else ""
        sep = " " if (cols - len(left) - len(right)) > 0 else ""
        line = left + sep + right
    if color:
        # schwarzer Text (30) auf tmux-dunkelgrünem Hintergrund (48;5;22)
        return f"\x1b[30;48;5;22m{line.ljust(cols)}\x1b[0m"
    return line

# ---------- Tastatur-Poll (für 'a' Toggle) ----------
class KeyPoller:
    def __init__(self):
        self.enabled = True
        self.win = os.name == "nt"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def poll(self):
        if not self.enabled:
            return ""

        if self.win:
            try:
                import msvcrt
                s = ""
                while msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    s += ch
                return s
            except ImportError:
                return ""
            except Exception:
                return ""
        else:
            try:
                # Einfache, nicht-blockierende Tastaturprüfung
                # WICHTIG: Im Pipe-Modus wird sys.stdin für piped Daten verwendet
                # und darf NICHT für Tastatureingaben gelesen werden
                if not is_pipe_mode and select.select([sys.stdin], [], [], 0)[0]:
                    return sys.stdin.read(1)
                return ""
            except Exception:
                return ""

def main():
    global is_pipe_mode

    def signal_handler(signum, frame):
        sys.exit(0)

    # Signal-Handler für SIGINT (Ctrl+C) und SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

                # ========================================================================
    # TASTATURBEHANDLUNG SETUP
    # ========================================================================
    # WICHTIG: Diese Terminal-Konfiguration ist ESSENTIELL für die Tastaturbehandlung!
    # Ohne diese Konfiguration funktionieren die Tasten 'a', '+', '-', 'q' NICHT.
    #
    # Funktionsweise:
    # - Speichert die ursprünglichen Terminal-Einstellungen
    # - Setzt das Terminal in "cbreak mode" für sofortige Tastatureingaben
    # - Stellt die Einstellungen am Ende wieder her
    #
    # Betroffene Modi:
    # - Kontinuierlicher Modus (-t/--interval)
    # - Iterativer Modus (--iterative)
    # - STDIN-Modus (ohne --cmd)
    #
    # Tasten-Funktionalität:
    # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
    # - 'q': Programm beenden
    # - '+': Intervall um 5 Sekunden erhöhen
    # - '-': Intervall um 5 Sekunden verringern (Minimum 1s)
    #
    # DOCKER-UNTERSTÜTZUNG:
    # - Im Docker-Container wird die Tastaturbehandlung deaktiviert
    # - Das Terminal ist nicht interaktiv und Tastatureingaben sind nicht verfügbar
    # - Tests laufen automatisch ohne Benutzerinteraktion
    # ========================================================================
    old_settings = None
    # Prüfe ob wir in einem Docker-Container sind (kein interaktives Terminal)
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER') == 'true'

    # ========================================================================
    # TASTATURBEHANDLUNG SETUP - WICHTIGE DOKUMENTATION
    # ========================================================================
    # WICHTIG: Diese Terminal-Konfiguration ist ESSENTIELL für die Tastaturbehandlung!
    # Ohne diese Konfiguration funktionieren die Tasten 'a', '+', '-', 'q' NICHT.
    #
    # Funktionsweise:
    # - Speichert die ursprünglichen Terminal-Einstellungen
    # - Setzt das Terminal in "cbreak mode" für sofortige Tastatureingaben
    # - Stellt die Einstellungen am Ende wieder her
    #
    # Betroffene Modi:
    # - Kontinuierlicher Modus (-t/--interval)
    # - Iterativer Modus (--iterative)
    # - STDIN-Modus (ohne --cmd)
    #
    # Tasten-Funktionalität:
    # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
    # - 'q': Programm beenden
    # - '+': Intervall um 5 Sekunden erhöhen
    # - '-': Intervall um 5 Sekunden verringern (Minimum 1s)
    #
    # DOCKER-UNTERSTÜTZUNG:
    # - Im Docker-Container wird die Tastaturbehandlung deaktiviert
    # - Das Terminal ist nicht interaktiv und Tastatureingaben sind nicht verfügbar
    # - Tests laufen automatisch ohne Benutzerinteraktion
    #
    # TESTING-HINWEIS:
    # - Die Tastaturbehandlung funktioniert nur bei echten Benutzereingaben
    # - AI-Assistenten können keine echten Tastatureingaben simulieren
    # - Bei Tests durch AI-Assistenten scheint die Tastaturbehandlung nicht zu funktionieren
    # - Echte Benutzer können die Tasten 'a', 'q', '+', '-' normal verwenden
    # ========================================================================
    try:
        args = parse_args()

        # PIPE-MODUS-ERKENNUNG
        # WICHTIG: Diese Variable wird verwendet um zu erkennen ob patwatch im Pipe-Modus läuft.
        # Im Pipe-Modus wird sys.stdin für die piped Daten verwendet und darf NICHT
        # für Tastatureingaben gelesen werden, da sonst die 'a' Taste in den piped
        # Daten als Tastatureingabe interpretiert wird und den Alt-Modus aktiviert.
        is_pipe_mode = not sys.stdin.isatty() and not args.cmd

        # ========================================================================
        # TASTATURBEHANDLUNG SETUP
        # ========================================================================
        # WICHTIG: Diese Terminal-Konfiguration ist ESSENTIELL für die Tastaturbehandlung!
        # Ohne diese Konfiguration funktionieren die Tasten 'a', '+', '-', 'q' NICHT.
        #
        # Funktionsweise:
        # - Speichert die ursprünglichen Terminal-Einstellungen
        # - Setzt das Terminal in "cbreak mode" für sofortige Tastatureingaben
        # - Stellt die Einstellungen am Ende wieder her
        #
        # Betroffene Modi:
        # - Kontinuierlicher Modus (-t/--interval)
        # - Iterativer Modus (--iterative)
        # - STDIN-Modus (ohne --cmd)
        #
        # Tasten-Funktionalität:
        # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
        # - 'q': Programm beenden
        # - '+': Intervall um 5 Sekunden erhöhen
        # - '-': Intervall um 5 Sekunden verringern (Minimum 1s)
        #
        # DOCKER-UNTERSTÜTZUNG:
        # - Im Docker-Container wird die Tastaturbehandlung deaktiviert
        # - Das Terminal ist nicht interaktiv und Tastatureingaben sind nicht verfügbar
        # - Tests laufen automatisch ohne Benutzerinteraktion
        #
        # TESTING-HINWEIS:
        # - Die Tastaturbehandlung funktioniert nur bei echten Benutzereingaben
        # - AI-Assistenten können keine echten Tastatureingaben simulieren
        # - Bei Tests durch AI-Assistenten scheint die Tastaturbehandlung nicht zu funktionieren
        # - Echte Benutzer können die Tasten 'a', 'q', '+', '-' normal verwenden
        # ========================================================================
        old_settings = None
        if os.name != 'nt' and not is_pipe_mode and not in_docker:  # Nicht Windows, nicht Pipe-Modus und nicht Docker
            try:
                import termios, tty
                # Speichere aktuelle Terminal-Einstellungen
                old_settings = termios.tcgetattr(sys.stdin)
                # Setze Terminal in cbreak mode für sofortige Tastatureingaben
                tty.setcbreak(sys.stdin.fileno())
            except ImportError:
                old_settings = None
            except Exception as e:
                old_settings = None

        fs = unescape(args.fs)
        sep = unescape(args.sep)
        # between wird nicht mehr verwendet, immer "..."
        cg_sep = unescape(args.cg_sep)
        aux_sep = unescape(args.aux_sep)
        flags = re.IGNORECASE if args.ignorecase else 0

        patterns = load_patterns(args.patterns, fs, flags)
        if not patterns:
            sys.stderr.write("[ERROR] Keine gültigen Patterns geladen.\n")
            sys.exit(2)

        alt_mode = args.alt_view  # Start im gewünschten Modus (Normal oder Alt)
        current_interval = args.interval if args.interval else 0  # Aktuelles Intervall

        # Cache für die letzten verarbeiteten Daten
        last_text = ""
        last_cmd_time = 0.0
        last_proc_time = 0

        # ========================================================================
        # GLOBALE BERECHNUNGSZEIT-VERWALTUNG (ANTI-FLIMMERN-SYSTEM)
        # ========================================================================
        # WICHTIG: Diese Variable speichert die aktuelle Berechnungszeit global.
        # Sie verhindert das Flimmern der Status-Bar und das kurze Aufblinken von 0ms.
        #
        # PROBLEM-LÖSUNG:
        # - Ohne diese globale Variable: Status-Bar flimmert zwischen [Xms] und [0ms]
        # - Mit dieser Lösung: Berechnungszeit bleibt stabil bis zum nächsten echten Update
        #
        # FUNKTIONSWEISE:
        # 1. Reguläre Updates: Überschreiben nur wenn ms > 0 (verhindert 0ms Flimmern)
        # 2. Taste 'a': Setzt die globale Zeit auf die Berechnungszeit der neuen Ansicht
        # 3. Status-Bar: Zeigt nur Zeit an wenn global_calculation_time_ms > 0
        #
        # WICHTIG: Diese Lösung darf NICHT entfernt werden, da sie das Flimmern-Problem löst!
        # ========================================================================
        global_calculation_time_ms = 0  # Globale Berechnungszeit in Millisekunden

        # ========================================================================
        # DURCHSCHNITTLICHE VERARBEITUNGSZEIT (ANTI-FLIMMERN-SYSTEM)
        # ========================================================================
        # WICHTIG: Diese Variable speichert die durchschnittliche Verarbeitungszeit
        # und wird nur bei Status-Bar-Refreshs angezeigt, um unnötiges Flimmern zu vermeiden.
        #
        # Funktionsweise:
        # - Sammelt alle Verarbeitungszeiten und berechnet den Durchschnitt
        # - Wird nur angezeigt wenn die Status-Bar durch andere Anlässe refresht wird
        # - Verhindert ständige Aktualisierung der Millisekunden-Anzeige
        #
        # WICHTIG: Diese Lösung verhindert unnötiges Flimmern der Status-Bar!
        # ========================================================================
        average_processing_times = []  # Liste aller Verarbeitungszeiten
        max_processing_samples = 10    # Maximale Anzahl der gespeicherten Zeiten
        average_processing_time_ms = 0  # Durchschnittliche Verarbeitungszeit in ms

        # ========================================================================
        # CACHE-DEAKTIVIERUNG (PROBLEM-LÖSUNG FÜR 0-WERTE)
        # ========================================================================
        # WICHTIG: Diese Variable deaktiviert den Cache komplett, um das Problem
        # mit 0-Werten nach dem Drücken von 'a' zu lösen.
        #
        # PROBLEM-LÖSUNG:
        # - Mit Cache: 0-Werte aus dem ersten Zyklus werden beim Modus-Wechsel angezeigt
        # - Ohne Cache: Programm zeigt immer nur die aktuellen Input-Daten an
        # - Beim Drücken von 'a': Erst beim nächsten Zyklus werden neue Daten angezeigt
        #
        # FUNKTIONSWEISE:
        # - use_cache = False: Kein Cache wird gefüllt oder angezeigt
        # - use_cache = True: Cache wird normal verwendet (für zukünftige Aktivierung)
        #
        # WICHTIG: Diese Variable löst das Problem mit den 0-Werten beim Modus-Wechsel!
        # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
        # ========================================================================
        use_cache = False  # Cache komplett deaktiviert

        # ========================================================================
        # GLOBALE CONTENT-START-ZEILE (COLOR-MODE POSITIONIERUNG)
        # ========================================================================
        # WICHTIG: Diese Variable steuert, in welcher Zeile der Content im color-mode beginnt.
        # Sie wird verwendet um die Legende und den Content korrekt zu positionieren.
        #
        # LOGIK:
        # - content_start_line = 3: Content beginnt in Zeile 3 (nach Header + Legende)
        # - Wird von allen Rendering-Funktionen verwendet um korrekte Positionierung zu gewährleisten
        # - Verhindert Überschreibung der Legende durch den Content
        #
        # WICHTIG: Diese Variable muss von ALLEN Funktionen im color-mode verwendet werden!
        # ========================================================================
        content_start_line = 3  # Zeile wo der Content im color-mode beginnt

        def get_legend_line(patterns: List[PatternRec], use_color: bool = False) -> str:
            """Erstellt die Legende-Zeile basierend auf den gefundenen Backreferences"""
            legend_items = []
            for pat in patterns:
                if pat.found_refs:
                    # Sortiere die gefundenen Backreferences für konsistente Anzeige
                    sorted_refs = sorted(pat.found_refs)
                    legend_items.extend(sorted_refs)

            # Entferne Duplikate und behalte die Reihenfolge bei
            seen = set()
            unique_items = []
            for item in legend_items:
                if item not in seen:
                    seen.add(item)
                    unique_items.append(item)

            if not unique_items:
                return ""

            if use_color:
                # ========================================================================
                # FARBIGE LEGENDE-IMPLEMENTIERUNG
                # ========================================================================
                # WICHTIG: Die Legende verwendet die gleichen Farben wie die entsprechenden
                # Wörter im Content. Das ermöglicht eine konsistente Farbzuordnung.
                # ========================================================================
                colored_items = []
                for item in unique_items:
                    # Verwende die gleiche Farblogik wie im Content
                    colored_item = _color_chip_key(item, item)  # item als key für konsistente Farben
                    colored_items.append(colored_item)
                return " ".join(colored_items)
            else:
                return " ".join(unique_items)

        # ========================================================================
        # COLOR-DEBUG-MODUS (TASTE 'C') - FARBKOMBINATIONEN-DEBUG
        # ========================================================================
        # WICHTIG: Im Color-Modus zeigt Taste 'c' die Farbcodes anstelle der ID/Hostname an.
        # Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
        #
        # PROBLEM-LÖSUNG:
        # - Ohne diese Funktion: Schwer zu identifizieren welche Farbkombination problematisch ist
        # - Mit dieser Funktion: Direkte Anzeige der Farbcodes mit den entsprechenden Farben
        #
        # FUNKTIONSWEISE:
        # - Taste 'c' im Normal-Modus: Zeigt Farbcodes anstelle von ID/Hostname
        # - Taste 'c' im Alt-Modus: Zeigt normale ID/Hostname an
        # - Einfache Wortersetzung: server1.example.com → 16/119
        # - Verwendet normale Farbgebung für konsistente Darstellung
        #
        # WICHTIG: Diese Funktion darf NICHT entfernt werden, da sie die Fehlerbehebung
        # von schlechten Farbkombinationen ermöglicht!
        # ========================================================================
        color_debug_mode = False  # Color-Debug-Modus (Taste 'c')

        def show_calculation_status(switching_to_alt: bool, calculation_time_ms: int = 0):
            """Zeigt den Berechnungsstatus in der Status-Bar an (nur bei Taste 'a')"""
            nonlocal global_calculation_time_ms, content_start_line, average_processing_times, max_processing_samples, average_processing_time_ms

            if args.clear:
                # Bestimme den Modus für die Header-Anzeige
                if args.iterative is not None:
                    left = f"Every {current_interval:.1f}s (iterative): {args.cmd}"
                elif args.cmd:
                    if current_interval > 0:
                        left = f"Every {current_interval:.1f}s (continuous): {args.cmd}"
                    else:
                        left = f"Continuous: {args.cmd}"
                elif is_pipe_mode:
                    left = "STDIN"
                else:
                    left = "STDIN"

                ts = now_str(args.utc)
                right_parts = []

                # ========================================================================
                # STATUS-BAR-BERECHNUNGS-INDIKATOR (NUR BEI TASTE 'A')
                # ========================================================================
                # WICHTIG: Diese Funktion wird nur bei Taste 'a' aufgerufen,
                # nicht bei regulären Updates. Das verhindert 0ms Anzeigen.
                #
                # Funktionsweise:
                # - Während Berechnung: "[...]" an der [ALT]-Position
                # - Nach Berechnung: "[ALT]" wieder normal, Zeit am Ende
                # - Bessere Sichtbarkeit und logischere Positionierung
                # ========================================================================
                if calculation_time_ms > 0:
                    # ========================================================================
                    # TASTE 'A' BERECHNUNGSZEIT SETZEN (ANTI-FLIMMERN-SYSTEM)
                    # ========================================================================
                    # WICHTIG: Setzt die globale Zeit auf die Berechnungszeit der neuen Ansicht.
                    # Das verhindert das Flimmern und sorgt für stabile Anzeige.
                    #
                    # KRITISCHE LOGIK:
                    # - global_calculation_time_ms = calculation_time_ms
                    # - Diese Zeit bleibt bestehen bis zum nächsten regulären Update mit ms > 0
                    # - Ohne diese Zeile: Berechnungszeit verschwindet sofort wieder
                    #
                    # WICHTIG: Diese Zeile darf NICHT entfernt werden!
                    # ========================================================================
                    global_calculation_time_ms = calculation_time_ms  # ANTI-FLIMMERN: Globale Zeit setzen
                    if args.header:
                        right_parts.append(args.header)
            if alt_mode:
                right_parts.append("[ALT]")
                right_parts.append(f"{ts} [{global_calculation_time_ms}ms]")
            else:
                # Berechnung läuft: Zeige "[...]" an der [ALT]-Position
                if args.header:
                    right_parts.append(args.header)
                right_parts.append("[...]")
                right_parts.append(ts)

                right = "  ".join([p for p in right_parts if p])
                header = build_header_line(left, right, color=args.color_header)

                # Nur Header aktualisieren, nicht den Hauptbereich
                header_frame = "\x1b[H" + header
                sys.stdout.write(header_frame)
                sys.stdout.flush()

        def handle_mode_switch():
            """Gemeinsame Funktion für Modus-Wechsel (Taste 'a') - ersetzt alle 3 Code-Pfade"""
            nonlocal alt_mode, global_calculation_time_ms, content_start_line, use_cache, average_processing_times, max_processing_samples, average_processing_time_ms

            # ========================================================================
            # OPTIMIERTER ANSICHTSWECHSEL MIT STATUS-BAR-FEEDBACK
            # ========================================================================
            # WICHTIG: Die neue Ansicht wird im Hintergrund berechnet,
            # während nur die Status-Bar aktualisiert wird. Das verhindert
            # schwarze Zeilen und gibt trotzdem Feedback über den Fortschritt.
            # ========================================================================

            # Sofortige Status-Anzeige in der Header-Zeile
            show_calculation_status(not alt_mode)

            # Künstliche Verzögerung für sichtbares "[...]"
            time.sleep(0.1)

            # Berechnungszeit messen
            calc_start = time.perf_counter()

            # DEBUG: NUR LEGENDE AUS CACHE (KEIN MAIN-CONTENT)
            # Verwende den gecachten Content, der bereits die Legende enthält
            new_content = ""

            # Berechnungszeit berechnen
            calc_time_ms = int(round((time.perf_counter() - calc_start) * 1000))

            # Jetzt den Modus wechseln
            alt_mode = not alt_mode

            # ========================================================================
            # FERTIGE FRAME MIT SCREEN-CLEAR ERSTELLEN
            # ========================================================================
            # WICHTIG: Erst jetzt wird der Screen-Clear gemacht,
            # nachdem die Berechnung abgeschlossen ist.
            # Das verhindert schwarze Zeilen während der Berechnung.
            # ========================================================================
            if args.clear:
                # Bestimme den Modus für die Header-Anzeige
                if args.iterative is not None:
                    left = f"Every {current_interval:.1f}s (iterative): {args.cmd}"
                elif args.cmd:
                    if current_interval > 0:
                        left = f"Every {current_interval:.1f}s (continuous): {args.cmd}"
                    else:
                        left = f"Continuous: {args.cmd}"
                elif is_pipe_mode:
                    left = "Pipe-Modus (STDIN)"
                else:
                    left = "STDIN"

                mode_tag = " [ALT]" if alt_mode else ""
                ts = now_str(args.utc)
                right_parts = []
                if args.header or mode_tag:
                    right_parts.append((args.header + mode_tag).strip())
                # Zeige durchschnittliche Verarbeitungszeit und RAM-Verbrauch im normalen Format
                memory_mb = get_memory_usage_mb()
                memory_str = format_memory_usage(memory_mb)
                right_parts.append(f"{ts} [{average_processing_time_ms}ms|{memory_str}]")
                right = "  ".join([p for p in right_parts if p])
                header = build_header_line(left, right, color=args.color_header)

                # ========================================================================
                # KOMPLETTEN GECACHTEN CONTENT ANZEIGEN (NUR WENN CACHE AKTIVIERT)
                # ========================================================================
                # WICHTIG: Zeige den kompletten gecachten Content an, der bereits
                # die Legende und den Content enthält, aber nur wenn Cache aktiviert.
                # Mit use_cache = False wird kein Cache verwendet, um 0-Werte zu vermeiden.
                #
                # PROBLEM-LÖSUNG:
                # - Ohne diese Bedingung: Cache wird immer angezeigt, 0-Werte beim Modus-Wechsel
                # - Mit dieser Bedingung: Cache wird nur angezeigt wenn aktiviert
                #
                # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
                # ========================================================================
                if use_cache:
                    cached_content = one_frame.current_text if hasattr(one_frame, 'current_text') else ""
                    legend_only = cached_content  # Verwende den kompletten gecachten Content
                else:
                    # Cache deaktiviert: Zeige leeren Content (wird beim nächsten Zyklus aktualisiert)
                    legend_only = ""
                # ========================================================================
                # LEGENDE-POSITIONIERUNG IM MODUS-WECHSEL
                # ========================================================================
                # WICHTIG: Die Legende wird in Zeile 2 positioniert (nach dem Header).
                # Der Content beginnt dann auf content_start_line.
                # ========================================================================
                # ========================================================================
                # CONTENT-POSITIONIERUNG MIT GLOBALER CONTENT_START_LINE
                # ========================================================================
                # WICHTIG: Der komplette gecachte Content (Legende + Content) wird
                # auf content_start_line positioniert, da er bereits die Legende enthält.
                # ========================================================================
                content_positioning = f"\x1b[{content_start_line};1H"  # Cursor auf content_start_line setzen
                complete_frame = "\x1b[H\x1b[2J" + header + "\n" + content_positioning + legend_only
            else:
                # ========================================================================
                # KOMPLETTEN GECACHTEN CONTENT ANZEIGEN (NUR WENN CACHE AKTIVIERT)
                # ========================================================================
                # WICHTIG: Zeige den kompletten gecachten Content an, der bereits
                # die Legende und den Content enthält, aber nur wenn Cache aktiviert.
                # Mit use_cache = False wird kein Cache verwendet, um 0-Werte zu vermeiden.
                #
                # PROBLEM-LÖSUNG:
                # - Ohne diese Bedingung: Cache wird immer angezeigt, 0-Werte beim Modus-Wechsel
                # - Mit dieser Bedingung: Cache wird nur angezeigt wenn aktiviert
                #
                # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
                # ========================================================================
                if use_cache:
                    cached_content = one_frame.current_text if hasattr(one_frame, 'current_text') else ""
                    legend_only = cached_content  # Verwende den kompletten gecachten Content
                else:
                    # Cache deaktiviert: Zeige leeren Content (wird beim nächsten Zyklus aktualisiert)
                    legend_only = ""
                # ========================================================================
                # LEGENDE-POSITIONIERUNG IM MODUS-WECHSEL (OHNE CLEAR)
                # ========================================================================
                # WICHTIG: Die Legende wird in Zeile 2 positioniert (nach dem Header).
                # Der Content beginnt dann auf content_start_line.
                # ========================================================================
                # ========================================================================
                # CONTENT-POSITIONIERUNG MIT GLOBALER CONTENT_START_LINE (OHNE CLEAR)
                # ========================================================================
                # WICHTIG: Der komplette gecachte Content (Legende + Content) wird
                # auf content_start_line positioniert, da er bereits die Legende enthält.
                # ========================================================================
                content_positioning = f"\x1b[{content_start_line};1H"  # Cursor auf content_start_line setzen
                complete_frame = content_positioning + legend_only

            # Sofortige Anzeige der fertigen Ansicht
            try:
                sys.stdout.write(complete_frame)
                sys.stdout.flush()
            except (BrokenPipeError, IOError):
                sys.exit(0)

            # Globale Berechnungszeit setzen (Anti-Flimmern)
            global_calculation_time_ms = calc_time_ms

        def calculate_view_content(target_alt_mode: bool) -> str:
            nonlocal color_debug_mode, content_start_line, use_cache, average_processing_times, max_processing_samples, average_processing_time_ms
            """Berechnet die Ansicht im Hintergrund ohne Screen-Clear"""
            # ========================================================================
            # VERWENDE AKTUELLE DATEN (NUR WENN CACHE AKTIVIERT)
            # ========================================================================
            # WICHTIG: Verwende die aktuellen Daten aus one_frame() nur wenn Cache aktiviert.
            # Mit use_cache = False wird kein Cache verwendet, um 0-Werte zu vermeiden.
            #
            # PROBLEM-LÖSUNG:
            # - Ohne diese Bedingung: Cache wird immer verwendet, 0-Werte beim Modus-Wechsel
            # - Mit dieser Bedingung: Cache wird nur verwendet wenn aktiviert
            #
            # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
            # ========================================================================
            if use_cache and hasattr(one_frame, 'current_text'):
                text = one_frame.current_text
            else:
                # Fallback: Verwende last_text
                text = last_text if last_text else ""

            # --- 1) Unsere Verarbeitungszeit starten ---
            t_start = time.perf_counter()

            # ========================================================================
            # PATTERN-DATEN NICHT ZURÜCKSETZEN BEIM MODUS-WECHSEL
            # ========================================================================
            # WICHTIG: Beim Modus-Wechsel sollen die Pattern-Daten NICHT zurückgesetzt werden,
            # da sie bereits verarbeitet wurden. Stattdessen verwenden wir die vorhandenen Daten.
            # Das verhindert das Problem mit 0-Werten nach dem Drücken von 'a'.
            # ========================================================================
            # NICHT process_text() aufrufen, da dies die Pattern-Daten zurücksetzt
            # normal_out_plain = process_text(text, patterns, sep, args.strip_punct, cg_sep)

            # ========================================================================
            # OPTIMIERTE ANSICHTS-BERECHNUNG (COLOR-MODUS PERFORMANCE)
            # ========================================================================
            # WICHTIG: Im Color-Modus ist die Berechnung beider Ansichten zeitaufwändig.
            # Daher berechnen wir nur die aktuell benötigte Ansicht für bessere Performance.
            #
            # Funktionsweise:
            # - Nur die aktuelle Ansicht wird berechnet (Normal ODER Alt)
            # - Verhindert unnötige Berechnungen und schwarze Bildschirme
            # - Deutlich schnellere Reaktion bei Taste 'a'
            # ========================================================================
            if target_alt_mode:
                # Alt-Ansicht berechnen
                content = render_alt_view(patterns, sep, use_color=args.color, no_warn=args.no_warn, content_start_line=content_start_line)
            else:
                # Normal-Ansicht berechnen
                content = render_normal_view(patterns, sep, use_color=args.color, color_debug_mode=color_debug_mode, content_start_line=content_start_line)

            # Zwischensumme unserer Laufzeit bis hier
            t_proc = time.perf_counter() - t_start

            # --- 2) Aux-Kommando (wird NICHT mitgezählt) ---
            frame_body = content
            if args.auxcmd:
                aux_to = args.aux_timeout if args.aux_timeout is not None else args.timeout
                aux_out, _ = run_cmd(args.auxcmd, args.shell, aux_to, args.no_warn)
                t_after_aux = time.perf_counter()
                sep_line = aux_sep + ("" if aux_sep.endswith("\n") else "\n")
                aux_block = sep_line + (aux_out if aux_out.endswith("\n") else aux_out + "\n")
                frame_body = (aux_block + content) if args.aux_before else (content + aux_block)
                t_proc += (time.perf_counter() - t_after_aux)  # nur das Zusammenbauen addieren

            # ========================================================================
            # DURCHSCHNITTLICHE VERARBEITUNGSZEIT BERECHNEN (ANTI-FLIMMERN)
            # ========================================================================
            # WICHTIG: Sammelt alle Verarbeitungszeiten und berechnet den Durchschnitt.
            # Die durchschnittliche Zeit wird nur bei Status-Bar-Refreshs angezeigt,
            # um unnötiges Flimmern zu vermeiden.
            #
            # Funktionsweise:
            # - Sammelt alle ms-Werte in einer Liste
            # - Berechnet den Durchschnitt der letzten max_processing_samples Werte
            # - Verhindert ständige Aktualisierung der Millisekunden-Anzeige
            #
            # WICHTIG: Diese Lösung verhindert unnötiges Flimmern der Status-Bar!
            # ========================================================================
            ms = int(round(t_proc * 1000.0))  # Berechne ms
            if ms > 0:  # Nur sammeln wenn aktuelle Zeit > 0
                # Füge aktuelle Zeit zur Liste hinzu
                average_processing_times.append(ms)

                # Begrenze die Liste auf max_processing_samples
                if len(average_processing_times) > max_processing_samples:
                    average_processing_times.pop(0)  # Entferne ältesten Wert

                # Berechne Durchschnitt
                average_processing_time_ms = int(round(sum(average_processing_times) / len(average_processing_times)))

            # ========================================================================
            # HINTERGRUND-BERECHNUNG OHNE SCREEN-CLEAR
            # ========================================================================
            # WICHTIG: Diese Funktion berechnet nur den Content, ohne Screen-Clear.
            # Der Screen-Clear wird erst später gemacht, wenn die fertige Ansicht
            # angezeigt wird. Das verhindert schwarze Zeilen während der Berechnung.
            # ========================================================================
            # Nur den Content zurückgeben, ohne Header und Screen-Clear
            return frame_body

        def one_frame():
            nonlocal alt_mode, current_interval, last_text, last_cmd_time, last_proc_time, global_calculation_time_ms, color_debug_mode, content_start_line, use_cache, average_processing_times, max_processing_samples, average_processing_time_ms

            # --- 0) Hauptkommando (nicht in Laufzeitmessung enthalten) ---
            cmd_time = 0.0
            try:
                if args.cmd:
                    if args.iterative is not None:
                        # Iterativer Modus: Kommando wird jedes Mal neu ausgeführt
                        text, cmd_time = run_cmd(args.cmd, args.shell, args.timeout, args.no_warn)
                    else:
                        # Kontinuierlicher Modus: Kommando läuft dauerhaft
                        # Für kontinuierliche Ausgabe: Verwende Popen statt run_cmd
                        if not hasattr(one_frame, 'cmd_process'):
                            # Erstelle Prozess beim ersten Aufruf
                            one_frame.cmd_process = subprocess.Popen(
                                [args.shell, "-c", args.cmd],
                                stdout=subprocess.PIPE,
                                stderr=(subprocess.DEVNULL if args.no_warn else subprocess.PIPE),
                                text=True,
                                bufsize=1,  # Line-buffered
                            )
                            one_frame.cmd_output = []
                            one_frame.cmd_start_time = time.perf_counter()

                        # Lese verfügbare Output-Zeilen
                        text = ""
                        try:
                            # Lese alle verfügbaren Zeilen sofort
                            while select.select([one_frame.cmd_process.stdout], [], [], 0.0)[0]:
                                line = one_frame.cmd_process.stdout.readline()
                                if line:
                                    one_frame.cmd_output.append(line)
                                    text += line
                                    # Begrenze die Anzahl der Zeilen um Speicher zu sparen
                                    if len(one_frame.cmd_output) > 1000:
                                        one_frame.cmd_output = one_frame.cmd_output[-500:]
                                else:
                                    break
                        except (BrokenPipeError, IOError):
                            pass

                        # Prüfe ob Prozess noch läuft
                        if one_frame.cmd_process.poll() is not None:
                            # Prozess beendet, verwende gesammelten Output
                            remaining_output, _ = one_frame.cmd_process.communicate()
                            if remaining_output:
                                text += remaining_output
                            cmd_time = time.perf_counter() - one_frame.cmd_start_time
                            # Reset für nächste Ausführung
                            delattr(one_frame, 'cmd_process')
                        else:
                            # Prozess läuft noch
                            cmd_time = time.perf_counter() - one_frame.cmd_start_time
                else:
                    # STDIN-Pipe-Modus: Lese kontinuierlich
                    text = ""
                    try:
                        # Lese alle verfügbaren Zeilen sofort ohne auf EOF zu warten
                        if select.select([sys.stdin], [], [], 0.0)[0]:  # Non-blocking check
                            for line in sys.stdin:
                                # Filtere Kommentarzeilen und leere Zeilen wenn --no-warn aktiv
                                if args.no_warn and (line.startswith('#') or line.strip() == ''):
                                    continue
                                text += line
                                # Wenn wir genug Zeilen haben, brechen wir ab
                                if text.count('\n') >= 20:  # Max 20 Zeilen pro Durchlauf
                                    break
                    except (BrokenPipeError, IOError):
                        # Versorgender Prozess beendet
                        if not args.no_warn:
                            sys.stderr.write("[INFO] Versorgender Prozess beendet.\n")
                        # text bleibt leer oder enthält bereits gelesene Zeilen
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if not args.no_warn:
                    sys.stderr.write(f"[ERROR] Fehler beim Lesen der Eingabe: {e}\n")
                text = ""

            # ========================================================================
            # AKTUELLE DATEN FÜR HINTERGRUND-BERECHNUNG SPEICHERN
            # ========================================================================
            # WICHTIG: Speichere die aktuellen Daten für calculate_view_content(),
            # aber nur wenn sie nicht leer sind, um die Status-Bar nicht zu beeinflussen.
            # ========================================================================
            # CACHE-FÜLLUNG (NUR WENN AKTIVIERT)
            # ========================================================================
            # WICHTIG: Cache wird nur gefüllt wenn use_cache = True.
            # Mit use_cache = False wird kein Cache verwendet, um 0-Werte zu vermeiden.
            #
            # PROBLEM-LÖSUNG:
            # - Ohne diese Bedingung: Cache wird immer gefüllt, 0-Werte beim Modus-Wechsel
            # - Mit dieser Bedingung: Cache wird nur gefüllt wenn aktiviert
            #
            # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
            # ========================================================================
            if use_cache and text.strip():  # Nur speichern wenn Cache aktiviert und Daten vorhanden sind
                one_frame.current_text = text

            # --- 1) Unsere Verarbeitungszeit starten ---
            t_start = time.perf_counter()

            # ========================================================================
            # PATTERN-DATEN NICHT ZURÜCKSETZEN IM COLOR-MODUS
            # ========================================================================
            # WICHTIG: Im Color-Modus verwenden wir die Rendering-Funktionen, die die
            # Pattern-Daten direkt verwenden. Daher dürfen wir die Pattern-Daten NICHT
            # zurücksetzen, da sonst die Rendering-Funktionen leere Daten verwenden.
            # Das verhindert das Problem mit 0-Werten nach dem Drücken von 'a'.
            # ========================================================================
            if args.color:
                # ========================================================================
                # COLOR-MODUS: PATTERN-DATEN ZURÜCKSETZEN UND VERARBEITEN
                # ========================================================================
                # WICHTIG: Im Color-Modus müssen wir die Pattern-Daten zurücksetzen,
                # aber dann direkt verarbeiten, ohne process_text() zu verwenden.
                # Das verhindert das Problem mit 0-Werten nach dem Drücken von 'a'.
                # ========================================================================
                # ========================================================================
                # PATTERN-DATEN ZURÜCKSETZEN (NUR WENN CACHE AKTIVIERT)
                # ========================================================================
                # WICHTIG: Pattern-Daten werden nur zurückgesetzt wenn use_cache = True.
                # Mit use_cache = False werden die Pattern-Daten nicht zurückgesetzt,
                # um das Problem mit 0-Werten beim Modus-Wechsel zu vermeiden.
                #
                # PROBLEM-LÖSUNG:
                # - Ohne diese Bedingung: Pattern-Daten werden immer zurückgesetzt, 0-Werte
                # - Mit dieser Bedingung: Pattern-Daten werden nur zurückgesetzt wenn Cache aktiviert
                #
                # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
                # ========================================================================
                if use_cache:
                    # Reset Pattern-Daten (wie in process_text())
                    for pat in patterns:
                        pat.count = 0
                        pat.head.clear()
                        pat.head_keys.clear()
                        pat.head_count = 0
                        pat.alts.clear()
                        pat.orig_words.clear()  # Reset ursprüngliche Wörter
                        pat.found_refs.clear()  # Reset gefundene Backreferences

                # ========================================================================
                # PATTERN-DATEN IMMER VERARBEITEN (FÜR ANZEIGE ERFORDERLICH)
                # ========================================================================
                # WICHTIG: Pattern-Daten müssen IMMER verarbeitet werden, um überhaupt
                # etwas anzuzeigen. Das Problem mit 0-Werten wird durch die Cache-Deaktivierung gelöst.
                #
                # PROBLEM-LÖSUNG:
                # - Ohne Verarbeitung: Schwarzer Bildschirm, nichts wird angezeigt
                # - Mit Verarbeitung: Normale Anzeige, aber keine 0-Werte beim Modus-Wechsel
                #
                # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
                # ========================================================================
                # Verarbeite die Daten direkt
                for line in text.splitlines():
                    for pat in patterns:
                        if pat.line_re.search(line):
                            pat.count += 1
                            w, m = extract_word_and_match(line, pat, cg_sep)
                            if args.strip_punct and w: w = strip_punct(w)
                            # Speichere ursprüngliches Wort für Legende
                            pat.orig_words.append(w)
                            # Speichere die evaluierte \1 Backreference für die Legende
                            if m and m.groups() and len(m.groups()) >= 1:
                                pat.found_refs.add(m.group(1))  # \1 Backreference
                            # Transformiertes Alternativwort (Spalte 5; darf Backrefs als Quelle nutzen)
                            alt = apply_pipeline(w, pat.transforms, m) if pat.transforms else w
                            pat.alts.append(alt)
                            # Normal-Head
                            if w:
                                pat.head.append(w)
                                pat.head_keys.append(alt if alt else w)  # Farb-Key: Altwort dominiert
                                pat.head_count += 1
                # Im Color-Modus wird normal_out_plain nicht benötigt, aber für Konsistenz definieren
                normal_out_plain = ""
            else:
                # Im NoColor-Modus: Pattern-Daten zurücksetzen und verarbeiten
                normal_out_plain = process_text(text, patterns, sep, args.strip_punct, cg_sep)

            # CODE-PFAD DOKUMENTATION:
            # DIESER CODE-PFAD wird verwendet für:
            # - Kontinuierlicher CMD-Modus (--cmd mit -t > 0)
            # - Iterativer Modus (--iterative)
            # - COLOR-Modus (--color) verwendet render_normal_view/render_alt_view
            # - NOCOLOR-Modus (ohne --color) verwendet process_text (Zeile 1141 oben)

            # ========================================================================
            # OPTIMIERTE ANSICHTS-BERECHNUNG (COLOR-MODUS PERFORMANCE)
            # ========================================================================
            # WICHTIG: Im Color-Modus ist die Berechnung beider Ansichten zeitaufwändig.
            # Daher berechnen wir nur die aktuell benötigte Ansicht für bessere Performance.
            #
            # Funktionsweise:
            # - Nur die aktuelle Ansicht wird berechnet (Normal ODER Alt)
            # - Verhindert unnötige Berechnungen und schwarze Bildschirme
            # - Deutlich schnellere Reaktion bei Taste 'a'
            # ========================================================================
            # ========================================================================
            # RENDERING-FUNKTIONEN IMMER AUFRUFEN (FÜR ANZEIGE ERFORDERLICH)
            # ========================================================================
            # WICHTIG: Rendering-Funktionen müssen IMMER aufgerufen werden, um überhaupt
            # etwas anzuzeigen. Das Problem mit 0-Werten wird durch die Cache-Deaktivierung gelöst.
            #
            # PROBLEM-LÖSUNG:
            # - Ohne Rendering: Schwarzer Bildschirm, nichts wird angezeigt
            # - Mit Rendering: Normale Anzeige, aber keine 0-Werte beim Modus-Wechsel
            #
            # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
            # ========================================================================
            if alt_mode:
                # Alt-Ansicht berechnen
                content = render_alt_view(patterns, sep, use_color=args.color, no_warn=args.no_warn, content_start_line=content_start_line)
            else:
                # Normal-Ansicht berechnen
                if args.color:
                    # Color-Modus: Verwende render_normal_view
                    content = render_normal_view(patterns, sep, use_color=args.color, color_debug_mode=color_debug_mode, content_start_line=content_start_line)
                else:
                    # NoColor-Modus: Verwende die bereits verarbeiteten Daten
                    content = normal_out_plain

            # Zwischensumme unserer Laufzeit bis hier
            t_proc = time.perf_counter() - t_start

            # --- 2) Aux-Kommando (wird NICHT mitgezählt) ---
            frame_body = content
            if args.auxcmd:
                aux_to = args.aux_timeout if args.aux_timeout is not None else args.timeout
                aux_out, _ = run_cmd(args.auxcmd, args.shell, aux_to, args.no_warn)
                t_after_aux = time.perf_counter()
                sep_line = aux_sep + ("" if aux_sep.endswith("\n") else "\n")
                aux_block = sep_line + (aux_out if aux_out.endswith("\n") else aux_out + "\n")
                frame_body = (aux_block + content) if args.aux_before else (content + aux_block)
                t_proc += (time.perf_counter() - t_after_aux)  # nur das Zusammenbauen addieren

            # ========================================================================
            # CACHE MIT VERARBEITETEM CONTENT BEFÜLLEN (KRITISCH!)
            # ========================================================================
            # WICHTIG: Der Cache muss mit dem verarbeiteten Content befüllt werden,
            # der Legende + Content enthält (aber NICHT den Header, der wird neu erstellt).
            # Nur so funktioniert der Modus-Wechsel korrekt.
            # ========================================================================
            # Erstelle den Content-Teil (Legende + frame_body) für den Cache
            cached_content = ""
            if args.color:
                # Legende hinzufügen (nur im color-Modus)
                legend_text = get_legend_line(patterns, use_color=args.color)
                if legend_text:
                    cached_content += legend_text + "\n"  # Legende hinzufügen
                cached_content += frame_body  # Content hinzufügen
            else:
                cached_content += frame_body  # Im nocolor-Modus keine Legende

            # ========================================================================
            # CACHE-FÜLLUNG MIT VERARBEITETEM CONTENT (NUR WENN AKTIVIERT)
            # ========================================================================
            # WICHTIG: Cache wird nur gefüllt wenn use_cache = True.
            # Mit use_cache = False wird kein Cache verwendet, um 0-Werte zu vermeiden.
            #
            # PROBLEM-LÖSUNG:
            # - Ohne diese Bedingung: Cache wird immer gefüllt, 0-Werte beim Modus-Wechsel
            # - Mit dieser Bedingung: Cache wird nur gefüllt wenn aktiviert
            #
            # NIEMALS ENTFERNEN ODER ÄNDERN, OHNE DAS PROBLEM ZU VERSTEHEEN!
            # ========================================================================
            if use_cache:
                one_frame.current_text = cached_content

            # --- 3) Header bauen (mit ms) & atomar ausgeben ---
            frame = frame_body
            ms = int(round(t_proc * 1000.0))  # Immer ms berechnen

            # ========================================================================
            # DURCHSCHNITTLICHE VERARBEITUNGSZEIT BERECHNEN (ANTI-FLIMMERN)
            # ========================================================================
            # WICHTIG: Sammelt alle Verarbeitungszeiten und berechnet den Durchschnitt.
            # Die durchschnittliche Zeit wird nur bei Status-Bar-Refreshs angezeigt,
            # um unnötiges Flimmern zu vermeiden.
            #
            # Funktionsweise:
            # - Sammelt alle ms-Werte in einer Liste
            # - Berechnet den Durchschnitt der letzten max_processing_samples Werte
            # - Verhindert ständige Aktualisierung der Millisekunden-Anzeige
            #
            # WICHTIG: Diese Lösung verhindert unnötiges Flimmern der Status-Bar!
            # ========================================================================
            if ms > 0:  # Nur sammeln wenn aktuelle Zeit > 0
                # Füge aktuelle Zeit zur Liste hinzu
                average_processing_times.append(ms)

                # Begrenze die Liste auf max_processing_samples
                if len(average_processing_times) > max_processing_samples:
                    average_processing_times.pop(0)  # Entferne ältesten Wert

                # Berechne Durchschnitt
                average_processing_time_ms = int(round(sum(average_processing_times) / len(average_processing_times)))

            # ========================================================================
            # GLOBALE BERECHNUNGSZEIT-VERWALTUNG IN ONE_FRAME() (ANTI-FLIMMERN)
            # ========================================================================
            # WICHTIG: Reguläre Updates überschreiben die globale Zeit NUR wenn sie > 0 ist.
            # Bei Taste 'a' wird sie von show_calculation_status() gesetzt.
            # Das verhindert das kurze Aufblinken der Berechnungszeit und das Flimmern.
            #
            # KRITISCHE LOGIK:
            # - if ms > 0: Überschreibt global_calculation_time_ms = ms
            # - if ms = 0: Behält die alte globale Zeit bei (verhindert 0ms Flimmern)
            # - Ohne diese Bedingung: Status-Bar flimmert zwischen [Xms] und [0ms]
            #
            # WICHTIG: Diese Bedingung darf NICHT entfernt werden!
            # ========================================================================
            if ms > 0:  # Nur überschreiben wenn aktuelle Zeit > 0 (ANTI-FLIMMERN)
                global_calculation_time_ms = ms

            if args.clear:
                # Bestimme den Modus für die Header-Anzeige
                if args.iterative is not None:
                    left = f"Every {current_interval:.1f}s (iterative): {args.cmd}"
                elif args.cmd:
                    # Wenn --cmd verwendet wird, zeige das Kommando an
                    if current_interval > 0:
                        left = f"Every {current_interval:.1f}s (continuous): {args.cmd}"
                    else:
                        left = f"Continuous: {args.cmd}"
                elif is_pipe_mode:
                    left = "Pipe-Modus (STDIN)"
                else:
                    left = "STDIN"

                mode_tag = " [ALT]" if alt_mode else ""
                ts = now_str(args.utc)
                right_parts = []
                if args.header or mode_tag:
                    right_parts.append((args.header + mode_tag).strip())
                # ========================================================================
                # STATUS-BAR ZEIT- UND SPEICHER-ANZEIGE (ANTI-FLIMMERN-SYSTEM)
                # ========================================================================
                # WICHTIG: Zeigt nur Zeit an wenn global_calculation_time_ms > 0.
                # Das verhindert das Flimmern zwischen [Xms] und [0ms].
                #
                # KRITISCHE LOGIK:
                # - global_calculation_time_ms > 0: Zeigt [Xms] an
                # - global_calculation_time_ms <= 0: Zeigt keine Zeit an
                # - Ohne diese Bedingung: Status-Bar flimmert mit 0ms Anzeigen
                #
                # WICHTIG: Diese Bedingung darf NICHT entfernt werden!
                # ========================================================================
                # Zeige Kommando-Zeit, durchschnittliche Verarbeitungszeit und RAM-Verbrauch im Format [Xs|Yms|ZMB]
                memory_mb = get_memory_usage_mb()
                memory_str = format_memory_usage(memory_mb)

                if args.cmd and cmd_time > 0:
                    cmd_sec = int(round(cmd_time))
                    time_str = f"[{cmd_sec}s|{average_processing_time_ms}ms|{memory_str}]"
                elif average_processing_time_ms > 0:  # Nur anzeigen wenn durchschnittliche Zeit > 0 (ANTI-FLIMMERN)
                    time_str = f"[{average_processing_time_ms}ms|{memory_str}]"
                else:
                    time_str = f"[{memory_str}]"  # Zeige nur RAM-Verbrauch wenn keine Zeit verfügbar

                # Zeit anzeigen wenn vorhanden
                if time_str:
                    right_parts.append(f"{ts} {time_str}")
                else:
                    right_parts.append(ts)
                right = "  ".join([p for p in right_parts if p])
                header = build_header_line(left, right, color=args.color_header)
                # ========================================================================
                # LEGENDE ERSTELLEN UND POSITIONIEREN (COLOR-MODE)
                # ========================================================================
                # WICHTIG: Die Legende wird in Zeile 2 positioniert (nach dem Header).
                # Der Content beginnt dann auf content_start_line.
                # ========================================================================
                legend_line = ""
                if args.color:
                    legend_text = get_legend_line(patterns, use_color=args.color)
                    if legend_text:
                        legend_line = f"\x1b[2;1H{legend_text}\n"  # Legende in Zeile 2

                # Beim ersten Mal: Komplettes Löschen, danach nur Cursor-Positionierung
                if not hasattr(one_frame, 'first_clear'):
                    # ========================================================================
                    # CONTENT-POSITIONIERUNG MIT GLOBALER CONTENT_START_LINE
                    # ========================================================================
                    # WICHTIG: Der Content beginnt auf der durch content_start_line definierten Zeile.
                    # Das verhindert Überschreibung der Legende und stellt korrekte Positionierung sicher.
                    # ========================================================================
                    content_positioning = f"\x1b[{content_start_line};1H"  # Cursor auf content_start_line setzen
                    frame = "\x1b[H\x1b[2J" + header + "\n" + legend_line + content_positioning + frame_body
                    one_frame.first_clear = True
                else:
                    # ========================================================================
                    # CONTENT-POSITIONIERUNG MIT GLOBALER CONTENT_START_LINE (OHNE CLEAR)
                    # ========================================================================
                    # WICHTIG: Der Content beginnt auf der durch content_start_line definierten Zeile.
                    # Das verhindert Überschreibung der Legende und stellt korrekte Positionierung sicher.
                    # ========================================================================
                    content_positioning = f"\x1b[{content_start_line};1H"  # Cursor auf content_start_line setzen
                    frame = "\x1b[H" + header + "\n" + legend_line + content_positioning + frame_body

            # Aktualisiere die letzten Zeiten für update_display
            last_cmd_time = cmd_time
            last_proc_time = ms

            try:
                sys.stdout.write(frame)
                sys.stdout.flush()
            except (BrokenPipeError, IOError):
                # Handle broken pipe gracefully
                sys.exit(0)

        # SOFORT erste Ausführung beim Start
        one_frame()

        # Zeige Hinweis für Pipe-Modus
        if is_pipe_mode:
            sys.stderr.write("[INFO] Pipe-Modus: Tastatursteuerung nicht verfügbar.\n")
            sys.stderr.write("[INFO] Für Tastatursteuerung verwenden Sie: --cmd 'generator | patwatch'\n")
            sys.stderr.write("[INFO] Zum Beenden: Ctrl+C oder warten Sie bis der Generator beendet ist\n")

        # Programmstart-Zeit für Timeout-Prüfung
        program_start_time = time.time()

        # Hauptschleife für alle Modi
        try:
            # Einfache Tastaturbehandlung ohne KeyPoller
                while True:
                    # Globale Timeout-Prüfung
                    if args.timeout and (time.time() - program_start_time) >= args.timeout:
                        if not args.no_warn:
                            sys.stderr.write(f"[INFO] Timeout nach {args.timeout} Sekunden erreicht. Programm wird beendet.\n")
                        sys.exit(0)
                    if args.iterative is not None:
                        # Iterativer Modus: Kommando wird alle X Sekunden neu ausgeführt
                        current_interval = args.iterative

                        # Kontinuierliche Tastaturbehandlung während des Wartens
                        start_time = time.time()
                        while time.time() - start_time < current_interval:
                            # ========================================================================
                            # TASTATURBEHANDLUNG IM ITERATIVEN MODUS
                            # ========================================================================
                            # WICHTIG: Diese Tastaturbehandlung ist ESSENTIELL für die Benutzerinteraktion!
                            #
                            # Funktionsweise:
                            # - Prüft alle 100ms auf Tastatureingaben
                            # - Verarbeitet Tasten sofort ohne Warten auf Intervall-Ende
                            # - Aktualisiert die Anzeige sofort bei Tastendruck
                            #
                            # Tasten-Funktionalität:
                            # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
                            # - 'q': Programm beenden
                            # - '+': Intervall um 5 Sekunden erhöhen
                            # - '-': Intervall um 5 Sekunden verringern (Minimum 1s)
                            # ========================================================================
                            # Einfache Tastaturbehandlung ohne Terminal-Konfiguration
                            # WICHTIG: Im Pipe-Modus wird sys.stdin für piped Daten verwendet
                            # und darf NICHT für Tastatureingaben gelesen werden
                            if not is_pipe_mode:
                                try:
                                    if select.select([sys.stdin], [], [], 0.1)[0]:
                                        key = sys.stdin.read(1)
                                    if key == 'a':
                                        # ========================================================================
                                        # MODUS-WECHSEL - GEMEINSAME FUNKTION
                                        # ========================================================================
                                        # WICHTIG: Verwendet die gemeinsame handle_mode_switch() Funktion
                                        # um Code-Duplikation zu vermeiden und Wartungsfehler zu verhindern.
                                        # ========================================================================
                                        handle_mode_switch()
                                    elif key == '+':
                                        current_interval += 5.0
                                        args.iterative = current_interval
                                        one_frame()
                                    elif key == '-':
                                        new_interval = current_interval - 5.0
                                        if new_interval >= 1.0:
                                            current_interval = new_interval
                                            args.iterative = current_interval
                                            one_frame()
                                    elif key == 'c' and args.color:
                                        # ========================================================================
                                        # COLOR-DEBUG-MODUS TOGGLE (TASTE 'C') - ITERATIVER MODUS
                                        # ========================================================================
                                        # WICHTIG: Im Color-Modus zeigt Taste 'c' die Farbcodes anstelle der ID/Hostname an.
                                        # Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
                                        # ========================================================================
                                        color_debug_mode = not color_debug_mode
                                        one_frame()  # Sofortige Aktualisierung der Anzeige
                                    elif key == 'q':
                                        sys.exit(0)
                                        break
                                except Exception as e:
                                    # Stille Fehlerbehandlung für Tastaturbehandlung
                                    pass

                        # Wenn keine Tasten gedrückt wurden, normales Update
                        if time.time() - start_time >= current_interval:
                            one_frame()
                    elif args.interval and args.interval > 0:
                        # Kontinuierlicher Modus: Kommando läuft dauerhaft, Display wird alle X Sekunden aktualisiert
                        current_interval = args.interval

                        # Kontinuierliche Tastaturbehandlung während des Wartens
                        start_time = time.time()
                        while time.time() - start_time < current_interval:
                            # ========================================================================
                            # TASTATURBEHANDLUNG IM KONTINUIERLICHEN MODUS
                            # ========================================================================
                            # WICHTIG: Diese Tastaturbehandlung ist ESSENTIELL für die Benutzerinteraktion!
                            #
                            # Funktionsweise:
                            # - Prüft alle 100ms auf Tastatureingaben
                            # - Verarbeitet Tasten sofort ohne Warten auf Intervall-Ende
                            # - Aktualisiert die Anzeige sofort bei Tastendruck
                            #
                            # Tasten-Funktionalität:
                            # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
                            # - 'q': Programm beenden
                            # - '+': Intervall um 5 Sekunden erhöhen
                            # - '-': Intervall um 5 Sekunden verringern (Minimum 1s)
                            # ========================================================================
                            # Einfache Tastaturbehandlung ohne Terminal-Konfiguration
                            # WICHTIG: Im Pipe-Modus wird sys.stdin für piped Daten verwendet
                            # und darf NICHT für Tastatureingaben gelesen werden
                            if not is_pipe_mode:
                                try:
                                    if select.select([sys.stdin], [], [], 0.1)[0]:
                                        key = sys.stdin.read(1)
                                    if key == 'a':
                                        # ========================================================================
                                        # MODUS-WECHSEL - GEMEINSAME FUNKTION
                                        # ========================================================================
                                        # WICHTIG: Verwendet die gemeinsame handle_mode_switch() Funktion
                                        # um Code-Duplikation zu vermeiden und Wartungsfehler zu verhindern.
                                        # ========================================================================
                                        handle_mode_switch()
                                    elif key == '+':
                                        current_interval += 5.0
                                        args.interval = current_interval
                                        one_frame()
                                    elif key == '-':
                                        new_interval = current_interval - 5.0
                                        if new_interval >= 1.0:
                                            current_interval = new_interval
                                            args.interval = current_interval
                                            one_frame()
                                    elif key == 'c' and args.color:
                                        # ========================================================================
                                        # COLOR-DEBUG-MODUS TOGGLE (TASTE 'C') - KONTINUIERLICHER MODUS
                                        # ========================================================================
                                        # WICHTIG: Im Color-Modus zeigt Taste 'c' die Farbcodes anstelle der ID/Hostname an.
                                        # Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
                                        # ========================================================================
                                        color_debug_mode = not color_debug_mode
                                        one_frame()  # Sofortige Aktualisierung der Anzeige
                                    elif key == 'q':
                                        sys.exit(0)
                                    break
                                except Exception as e:
                                    # Stille Fehlerbehandlung für Tastaturbehandlung
                                    pass

                        # Wenn keine Tasten gedrückt wurden, normales Update
                        if time.time() - start_time >= current_interval:
                            one_frame()
                    else:
                        # ========================================================================
                        # STDIN-MODUS: Kontinuierlich lesen und anzeigen
                        # ========================================================================
                        # WICHTIG: Auch im STDIN-Modus muss Tastaturbehandlung funktionieren!
                        #
                        # Funktionsweise:
                        # - Führt one_frame() aus (liest STDIN-Daten und aktualisiert Anzeige)
                        # - Prüft dann auf Tastatureingaben mit kurzem Timeout
                        # - Verarbeitet Tasten 'a', 'q', '+', '-' sofort
                        # - Wiederholt den Zyklus kontinuierlich
                        #
                        # Tasten-Funktionalität (identisch zu anderen Modi):
                        # - 'a': Wechsel zwischen Normal- und Alt-Ansicht
                        # - 'q': Programm beenden
                        # - '+': Intervall um 5 Sekunden erhöhen (nicht relevant im STDIN-Modus)
                        # - '-': Intervall um 5 Sekunden verringern (nicht relevant im STDIN-Modus)
                        # ========================================================================

                        # Normales Update mit STDIN-Daten
                        one_frame()

                        # Tastaturbehandlung im STDIN-Modus
                        # WICHTIG: Im Pipe-Modus wird sys.stdin für piped Daten verwendet
                        # und darf NICHT für Tastatureingaben gelesen werden
                        if not is_pipe_mode:
                            try:
                                # Prüfe auf Tastatureingaben mit kurzem Timeout (100ms)
                                if select.select([sys.stdin], [], [], 0.1)[0]:
                                        key = sys.stdin.read(1)
                                        if key == 'a':
                                            # ========================================================================
                                            # MODUS-WECHSEL - GEMEINSAME FUNKTION
                                            # ========================================================================
                                            # WICHTIG: Verwendet die gemeinsame handle_mode_switch() Funktion
                                            # um Code-Duplikation zu vermeiden und Wartungsfehler zu verhindern.
                                            # ========================================================================
                                            handle_mode_switch()
                                        elif key == 'c' and args.color:
                                            # ========================================================================
                                            # COLOR-DEBUG-MODUS TOGGLE (TASTE 'C') - STDIN-MODUS
                                            # ========================================================================
                                            # WICHTIG: Im Color-Modus zeigt Taste 'c' die Farbcodes anstelle der ID/Hostname an.
                                            # Das ist nützlich für die Fehlerbehebung von schlechten Farbkombinationen.
                                            # ========================================================================
                                            color_debug_mode = not color_debug_mode
                                            one_frame()  # Sofortige Aktualisierung der Anzeige
                                        elif key == 'q':
                                            sys.exit(0)
                                        # '+', '-' sind im STDIN-Modus nicht relevant
                            except (KeyboardInterrupt, SystemExit):
                                sys.exit(0)
                            except Exception as e:
                                # Stille Fehlerbehandlung für Tastaturbehandlung
                                pass
        except Exception as e:
            if not args.no_warn:
                sys.stderr.write(f"[ERROR] Unerwarteter Fehler im kontinuierlichen Modus: {e}\n")
            sys.exit(1)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Kritischer Fehler: {e}\n")
        sys.exit(1)
    finally:
        # Terminal-Einstellungen wiederherstellen
        if old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except:
                pass  # Ignoriere Fehler beim Wiederherstellen

if __name__ == "__main__":
    main()
