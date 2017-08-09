import curses
from urllib2 import urlopen
from HTMLParser import HTMLParser
from json import loads


stdscr = curses.initscr()


def get_new_Joke():
    joke_json = loads(urlopen('http://api.icndb.com/jokes/random').read())
    return(HTMLParser().unescape(joke_json['value']['joke']).encode('utf-8'))


curses.noecho()
curses.cbreak()
curses.curs_set(0)

if curses.has_colors():
    curses.start_color()

curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)

stdscr.addstr("hello", curses.A_REVERSE)
stdscr.chgat(-1, curses.A_REVERSE)


stdscr.addstr(curses.LINES-1, 0, "Press 'R' to request a new quote, 'Q' to quit")

stdscr.chgat(curses.LINES-1,7, 1, curses.A_BOLD | curses.color_pair(2))
stdscr.chgat(curses.LINES-1,35, 1, curses.A_BOLD | curses.color_pair(1))

quote_text_window = curses.newwin(curses.LINES-2,curses.COLS, 1,0)

quote_text_window.addstr("Press 'R' to get your first quote!")