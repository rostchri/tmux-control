import os

import libtmux

LAUNCH_TOOL = os.getcwd() + '/tmc.py'

def launch():
    server = libtmux.Server()
    os.system('tmux new -d -s tmc_adm')
    session = server.find_where({ "session_name": "tmc_adm" })
    window = session.new_window()
    session.windows[0].rename_window('TMC app-session')
    pane = window.select_pane('%0')
    pane = pane.select_pane()
    pane.send_keys(LAUNCH_TOOL)
    os.system('tmux attach-session -t tmc_adm')
