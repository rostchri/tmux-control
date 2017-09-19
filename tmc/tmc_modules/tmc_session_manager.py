import libtmux


window_id = 1


#receives list of machine-dicts, creates one window per machine
def create_windows(targets):
    global window_id
    server = libtmux.Server()
    server.new_session(session_name='tmc_ops')
    session = server.find_where({ "session_name": "tmc_ops" })
    for el in targets:
        target = el['machine']
        session.new_window(attach=False)
        session.windows[window_id].rename_window(target + '_w')
        tempdict = {
                'window_id': window_id,
                'window_name': target + '_w'
                }
        el.update(tempdict)
        window_id += 1
    return(targets) 
