import os
import libtmux


window_id = 1


#receives list of machine-dicts, creates one window per machine
def create_windows(targets):
    global window_id
    server = libtmux.Server()
    os.system('tmux new -d -s tmc_ops')
    session = server.find_where({ "session_name": "tmc_ops" })
    #for el in targets:
    #    target = el['machine']
    #    window_name = target + '_w'
    #    session.new_window()
    #    session.windows[window_id].rename_window(window_name)
    #    el['window_name'] = window_name
    #    el['window_id'] = window_id
    #    window_id += 1
    return(targets)
