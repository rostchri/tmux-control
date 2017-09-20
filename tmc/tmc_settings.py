import curses

APP_NAME = 'tmuxControl'
APP_VERSION = 'v0.1'

APP_INFO = '{0} {1}'.format(APP_NAME, APP_VERSION)
GIT_LINK = 'https://github.com/2357mam/tmux-control'
FOOTER = 'source: {0}'.format(GIT_LINK)

# assigning colors
RED = curses.COLOR_RED
GREEN = curses.COLOR_GREEN
BLUE = curses.COLOR_BLUE
YELLOW = curses.COLOR_YELLOW
BLACK = curses.COLOR_BLACK
MAGENTA = curses.COLOR_MAGENTA
CYAN = curses.COLOR_CYAN
WHITE = curses.COLOR_WHITE

CONFIG_DIR = 'tmc/configs'
FILE_DIR = 'tmc/files'
