import curses

appName = 'tmuxControl'
appVersion = 'v0.1'

release = '{0} {1}'.format(appName, appVersion)
gitLink = 'https://github.com/2357mam/tmuxControl'
footer = 'source: {0}'.format(gitLink)

# assigning colors
red = curses.COLOR_RED
green = curses.COLOR_GREEN
blue = curses.COLOR_BLUE
yellow = curses.COLOR_YELLOW
black = curses.COLOR_BLACK        
magenta = curses.COLOR_MAGENTA
cyan = curses.COLOR_CYAN
white = curses.COLOR_WHITE

configDir = "configs"