import os

REQUIREMENTS = [
        'set-option -g allow-rename off',
        ]

TCF = os.getenv("HOME") + '/.tmux.conf'


def check():
    with open(TCF, 'r') as f:
        tmux_conf = f.read()
    for x in REQUIREMENTS:
        if not x in tmux_conf:
            tmux_conf += '\n%s\n' %(x)
    with open(TCF, 'w') as f:
        f.write(tmux_conf)
