# this module launches a tmux-session 'tmc_adm' and the tmc-app in  window 0 of that session.

import os

import libtmux

LAUNCH_TOOL = os.getcwd() + '/app.py DIRECT_LAUNCH 2> .tmux-control-direct-launch.log' 

def launch():
    server = libtmux.Server()
    res = os.system('tmux new -d -s tmc_adm -n program')
    session = server.find_where({ "session_name": "tmc_adm" })
    window = session.new_window()
    session.windows[0].rename_window('TMC app-session')
    pane = window.select_pane('%0')
    pane = pane.select_pane()
    pane.send_keys(LAUNCH_TOOL)
    os.system('tmux attach-session -t tmc_adm')
