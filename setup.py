from setuptools import setup

setup(name='tmux-control',
version='0.2',
description='tmux session manager',
author='Maximilian Middeke',
author_email='mam@baltic-online.de',
url='https://github.com/2357mam/tmuxControl',
py_modules=['app', 'tmc_backend', 'tmc_settings', 'tmc_ui'],
install_requires=[
    'curses',
    'libtmux'])
