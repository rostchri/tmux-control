#!/usr/bin/python

from tmc import tmc_init_adm
from tmc import tmc_backend as tcb
from tmc import tmc_tmux_conf_check as tcc

if __name__ == '__main__':
    tcc.check()
    tmc_init_adm.init_adm()
