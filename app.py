#!/usr/bin/python

# checks wether the app was called with an arg,
# arg can be:
#  1. a config-file to launch an ssh-session with
#  2. 'DIRECT_LAUNCH', launching the app without init_adm
# if no arg exists, init_adm is called,
# which then calls this script with 'DIRECT_LAUNCH' set as arg 1
# this seems kind of clunky, but makes sense:
# you just want to call one launching-app, and launch
# init_adm OR an ssh-session with a custom file/,
# after init_adm was called, you can launch the actual app -
# with a gui and in the correct tmux-environment.

import os
import sys

from tmc import tmc_backend as tcb
from tmc import tmc_init_adm
from tmc import tmc_tmux_conf_check as tcc

if __name__ == '__main__':
    # ensures all requirements in tmux.conf are met
    tcc.check()
    try:
        if len(sys.argv) == 1:
            # launches 1. the session containing the tool,
            # and 2. this script with arg1 'DIRECT_LAUNCH'
            tmc_init_adm.launch()
        else:
            if sys.argv[1] == 'DIRECT_LAUNCH':
                tcb.app()
            else:
                # initializes ops-session with arg-file
                tcb.init_ops(sys.argv[1])
                os.system('tmux attach-session -t tmc_ops')
    except (Exception,),e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print >> sys.stderr, "### Unexpected exception: '%s' [%s] in file '%s' at line: %d" % (str(e), exc_type, fname, exc_tb.tb_lineno)

