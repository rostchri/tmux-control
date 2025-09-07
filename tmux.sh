#!/usr/bin/env bash
# tmux-multi-ssh.sh — Multi-Host-Gruppen in eigenen Windows, Sync-Toggle mit farbiger Statusbar
# Bash 3.2-kompatibel (macOS)

set -euo pipefail

### ───────── CONFIG ─────────
SESSION="fleet"
USER="root"
MAIN_PANE_WIDTH=120

# Gruppen definieren: "window-name: host1 host2 host3 …" je Zeile
GROUPS_DEF="$(cat <<'EOF'
MASTER: localhost host2.example.com host3.example.com host4.example.com
EOF
)"
#grp-2: host5.example.com host6.example.com host7.example.com
#grp-3: host8.example.com host9.example.com host10.example.com

### ───────── Utils ─────────
sanitize_win_name() { printf "%s" "${1//./-}"; }

get_term_size() {
  COLS=$(tput cols 2>/dev/null || echo 200)
  LINES=$(tput lines 2>/dev/null || echo 60)
  : "${COLS:=200}"; : "${LINES:=60}"
}

start_session() {
  local first_win="$1"
  tmux start-server
  tmux new-session -d -s "$SESSION" -n "$first_win" -x "$COLS" -y "$LINES"
  tmux set-option -g history-limit 10000 # default 2000
  tmux setw -t "$SESSION:$first_win" pane-border-status top
  tmux setw -t "$SESSION:$first_win" pane-border-format "#{pane_index} #{pane_title}"
}

create_window() {
  local win="$1"
  tmux new-window -t "$SESSION" -n "$win"
  tmux setw -t "$SESSION:$win" pane-border-status top
  tmux setw -t "$SESSION:$win" pane-border-format "#{pane_index} #{pane_title}"
}

join_hosts_into_window() {
  local target="$1"; shift
  local h tmpw
  for h in "$@"; do
    tmpw="$(sanitize_win_name "$h")"
    tmux new-window -t "$SESSION" -n "$tmpw"
    tmux join-pane  -s "$SESSION:$tmpw" -t "$SESSION:$target"
    tmux select-layout -t "$SESSION:$target" main-vertical
    tmux setw          -t "$SESSION:$target" main-pane-width "$MAIN_PANE_WIDTH"
  done
}

title_and_ssh() {
  local target="$1"; shift
  local i=0 h
  for h in "$@"; do
    tmux select-pane -t "$SESSION:$target.$i" -T "$h"
    #tmux send-keys   -t "$SESSION:$target.$i" "echo ===== $h =====" C-m
    tmux send-keys   -t "$SESSION:$target.$i" "ssh ${USER}@$h" C-m
    i=$((i+1))
  done
}

finalize_layout() {
  local win="$1" n
  n=$(tmux list-panes -t "$SESSION:$win" -F '#{pane_index}' | wc -l | tr -d ' ')
  if [ "$n" -le 7 ]; then
    tmux select-layout -t "$SESSION:$win" even-horizontal
  else
    tmux select-layout -t "$SESSION:$win" tiled
  fi
}

# Effektiven (sichtbaren) Status-Style für die Session ermitteln und speichern/anwenden
save_and_apply_original_status_style() {
  local bg fg style
  bg="$(tmux display -p -t "$SESSION:" "#{status_bg}" 2>/dev/null || true)"
  fg="$(tmux display -p -t "$SESSION:" "#{status_fg}" 2>/dev/null || true)"
  [ -n "$bg" ] || bg="green"
  [ -n "$fg" ] || fg="black"
  style="bg=${bg},fg=${fg}"
  tmux set -t "$SESSION" @orig-status-style "$style"
  tmux set -t "$SESSION" status-style "$style"
}

# Statusbar basierend auf aktuellem Window-Sync setzen (init & bei Wechsel)
apply_status_for_current_window() {
  local sess base state
  sess="$(tmux display -p "#{session_name}")"
  state="$(tmux display -p "#{?synchronize-panes,1,0}")"
  if [ "$state" = 1 ]; then
    tmux set -t "$sess" status-style "bg=red,fg=white"
  else
    base="$(tmux show -t "$sess" -v @orig-status-style 2>/dev/null || echo "bg=green,fg=black")"
    tmux set -t "$sess" status-style "$base"
  fi
}

install_sync_toggle_and_hooks() {
  # Session-lokal: Status/Maus/Meldedauer
  tmux set -t "$SESSION" status on
  #tmux set -t "$SESSION" display-time 4000
  tmux set -t "$SESSION" mouse on

  # Original-Style sichern & sofort setzen
  save_and_apply_original_status_style

  # Toggle-Binding
  tmux unbind-key b 2>/dev/null || true
  tmux bind-key b run-shell '
    sess=$(tmux display -p "#{session_name}")
    state=$(tmux display -p "#{?synchronize-panes,1,0}")
    if [ "$state" = 1 ]; then
      tmux set -w synchronize-panes off
      base=$(tmux show -t "$sess" -v @orig-status-style 2>/dev/null || echo "bg=green,fg=black")
      tmux set -t "$sess" status-style "$base"
      tmux display-message ">>> #[fg=blue]synchronize-panes OFF#[default] <<<"
    else
      tmux set -w synchronize-panes on
      tmux set -t "$sess" status-style "bg=red,fg=white"
      tmux display-message ">>> #[fg=red]synchronize-panes ON#[default] <<<"
    fi
  '

  # Hook: beim Window-Wechsel Statusbar passend zum *neuen* Window färben
  tmux set-hook -t "$SESSION" after-select-window 'run-shell "
sess=\$(tmux display -p \"#{session_name}\");
state=\$(tmux display -p \"#{?synchronize-panes,1,0}\");
if [ \"\$state\" = 1 ]; then
  tmux set -t \"\$sess\" status-style \"bg=red,fg=white\";
else
  base=\$(tmux show -t \"\$sess\" -v @orig-status-style 2>/dev/null || echo \"bg=green,fg=black\");
  tmux set -t \"\$sess\" status-style \"\$base\";
fi
"'

  # NEU: wenn tmux automatisch ins nächste Window springt (altes geschlossen)
  tmux set-hook -t "$SESSION" session-window-changed 'run-shell "
sess=\$(tmux display -p \"#{session_name}\");
state=\$(tmux display -p \"#{?synchronize-panes,1,0}\");
if [ \"\$state\" = 1 ]; then
  tmux set -t \"\$sess\" status-style \"bg=red,fg=white\";
else
  base=\$(tmux show -t \"\$sess\" -v @orig-status-style 2>/dev/null || echo \"bg=green,fg=black\");
  tmux set -t \"\$sess\" status-style \"\$base\";
fi
"'

  # NEU (Fallback): wenn ein Pane stirbt, ebenfalls Status prüfen
  tmux set-hook -t "$SESSION" pane-died 'run-shell "
sess=\$(tmux display -p \"#{session_name}\");
state=\$(tmux display -p \"#{?synchronize-panes,1,0}\");
if [ \"\$state\" = 1 ]; then
  tmux set -t \"\$sess\" status-style \"bg=red,fg=white\";
else
  base=\$(tmux show -t \"\$sess\" -v @orig-status-style 2>/dev/null || echo \"bg=green,fg=black\");
  tmux set -t \"\$sess\" status-style \"\$base\";
fi
"'
}

### ───────── MAIN ─────────
get_term_size

# Erste Zeile -> erstes Window
first_line="$(printf "%s\n" "$GROUPS_DEF" | sed -n '1p')"
[ -n "$first_line" ] || { echo "Keine Gruppen definiert."; exit 1; }
IFS=':' read -r first_name rest_hosts <<<"$first_line"
first_name="$(echo "$first_name" | xargs)"
rest_hosts="$(echo "$rest_hosts" | xargs)"
first_win="$(sanitize_win_name "$first_name")"

# Session + erstes Window
start_session "$first_win"

# Erste Gruppe befüllen
# shellcheck disable=SC2206
first_hosts=( $rest_hosts )
join_hosts_into_window "$first_win" "${first_hosts[@]}"
title_and_ssh         "$first_win" "${first_hosts[@]}"
finalize_layout       "$first_win"
tmux rename-window -t "$SESSION:$first_win" "$first_win"

# Weitere Gruppen -> weitere Windows
printf "%s\n" "$GROUPS_DEF" | sed '1d' | while IFS= read -r line; do
  [ -n "$line" ] || continue
  IFS=':' read -r name hosts_str <<<"$line"
  name="$(echo "$name" | xargs)"
  hosts_str="$(echo "$hosts_str" | xargs)"
  [ -n "$name" ] && [ -n "$hosts_str" ] || continue
  win="$(sanitize_win_name "$name")"
  create_window "$win"
  # shellcheck disable=SC2206
  hosts=( $hosts_str )
  join_hosts_into_window "$win" "${hosts[@]}"
  title_and_ssh         "$win" "${hosts[@]}"
  finalize_layout       "$win"
  tmux rename-window -t "$SESSION:$win" "$win"
done

# Toggle & Hooks installieren (inkl. Initial-Farb-Set) und anwenden
install_sync_toggle_and_hooks
apply_status_for_current_window

# Start im ersten Window + kurzer Überblick
tmux list-panes -t "$SESSION:$first_win" -F '#{pane_index} #{pane_title} #{pane_width}x#{pane_height}'
tmux select-window -t "$SESSION:$first_win"
tmux attach -t "$SESSION"
tmux display-panes -t "$SESSION:$first_win"

