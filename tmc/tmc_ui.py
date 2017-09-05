import curses

import tmc_settings as tcs


def build_box(content_dict):
    property_dict, box_height, box_width = get_box_properties(content_dict)
    win = curses.newwin(box_height + 2, box_width, 5, 35)
    win.bkgd(curses.color_pair(2))
    win.refresh()
    for section in property_dict:
        if not section == 'content':
            for line in property_dict[section]:
                win.addstr(line[0] -2, 2, line[1])
        else:
            for line in property_dict[section]:
                for entity in line:
                    if not type(entity) == list:
                        win.addstr(line[0] -2, 2, line[1])
                    else:
                        win.addstr(entity[0] -2, 2, entity[1])
    win.box()
    win.refresh()


def get_box_properties(content_dict):
    property_dict = {}
    box_height = 0
    box_width = 0
    line = 3
    categories = ['header', 'content', 'footer']
    for category in categories:
        property_dict[category] = []
        for row in content_dict[category]:
            if not type(row[1]) == list:
                var = row
                property_dict[category].append([line, row])
                line, box_height = map(increment_vars,[line, box_height])
            else:
                for var in row:
                    property_dict[category].append([line, var])
                    line, box_height = map(increment_vars,[line, box_height])
            if len(var) + 2 > box_width:
                box_width = len(var) + 2
        property_dict[category].append([line, ''])
        line, box_height = map(increment_vars,[line, box_height])      
    box_width += 4
    return property_dict, box_height, box_width


def increment_vars(x):
    return x+1


def init_curses(inactiveColor, windowBg, boxText, boxBg):
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    curses.start_color()
    curses.init_pair(1, inactiveColor, windowBg)
    curses.init_pair(2, boxText, boxBg)
    stdscr.bkgd(curses.color_pair(1))
    stdscr.refresh()
    return stdscr


def kill_box(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


def launch(menu, inactiveColor, windowBg, boxText, boxBg):
    content = [x[0] for x in menu]
    content_dict = {
        'header' : [tcs.APP_INFO],
        'content' : content,
        'footer' : [tcs.FOOTER]
    }
    stdscr = init_curses(inactiveColor, windowBg, boxText, boxBg)
    build_box(content_dict)
    # Waits for keypress (so the program doesnt just terminate while being WIP)
    cmd = chr(stdscr.getch())
    kill_box(stdscr)
    return cmd