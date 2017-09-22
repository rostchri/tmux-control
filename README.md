# tmuxControl

Dynamic session-control:

most tmux-managers just initialize a static layout, where this will manage sessions on the fly.

The first intended use case is ssh-connecting to machine-lists found in a config-file, and management of

a) the active list of desired machines for the current session and

b) the session itself.

Usage: create a json-file containing a dict with infos about your machine, equivalent to tmc/configs/taskf_ssh.json,
pass your file as param1 to init_ops (or call app.py with your file as arg1 directly)
