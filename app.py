#!/usr/bin/python

from tmc import tmc_init_adm
from tmc import tmc_tmux_conf_check as tcc

if __name__ == '__main__':
    #the module that ensures all requirements in tmux.conf are met
    tcc.check()
    #the module that launches 1. the session containing the tool, and 2. the tool
    tmc_init_adm.launch()
