#! /usr/bin/python

import os
import sys

from tmc import tmc_backend as tcb

def launch_session():
    if __name__ == '__main__':
        tcb.init_ops(sys.argv[1])
        os.system('tmux attach-session -t tmc_ops')

launch_session()
