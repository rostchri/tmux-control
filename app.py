#!/usr/bin/python

import os
import sys

from tmc import tmc_backend as tcb
from tmc import tmc_init_adm
from tmc import tmc_tmux_conf_check as tcc


def default_launch():
    if __name__ == '__main__':
        # ensures all requirements in tmux.conf are met
        tcc.check()
        try:
            if sys.argv[1] == 'direct_launch':
                direct_launch()
            else:
                # initializes ops-session with arg-file
                tcb.init_ops(sys.argv[1])
                os.system('tmux attach-session -t tmc_ops')
        except:
            # launches 1. the session containing the tool, and 2. the tool
            tmc_init_adm.launch()

def direct_launch():
    tcb.app()


default_launch()
