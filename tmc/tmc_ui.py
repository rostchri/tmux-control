import curses

import tmc_settings as tcs


def buildBox(contentDict):
    propertyDict, boxHeight, boxWidth = getBoxProperties(contentDict)
    win = curses.newwin(boxHeight + 2, boxWidth, 5, 35)
    win.bkgd(curses.color_pair(2))
    win.refresh()
    for section in propertyDict:
        if not section == 'content':
            for line in propertyDict[section]:
                win.addstr(line[0] -2, 2, line[1])
        else:
            for line in propertyDict[section]:
                for entity in line:
                    if not type(entity) == list:
                        win.addstr(line[0] -2, 2, line[1])
                    else:
                        win.addstr(entity[0] -2, 2, entity[1])
    win.box()
    win.refresh()


def getBoxProperties(contentDict):
    propertyDict = {}
    boxHeight = 0
    boxWidth = 0
    line = 3
    categories = ['header', 'content', 'footer']
    for category in categories:
        propertyDict[category] = []
        for row in contentDict[category]:
            if not type(row[1]) == list:
                var = row
                propertyDict[category].append([line, var])
                line, boxHeight = map(incrementVars,[line, boxHeight])
            else:
                for var in row:
                    propertyDict[category].append([line, var])
                    line, boxHeight = map(incrementVars,[line, boxHeight])
            if len(var) + 2 > boxWidth:
                boxWidth = len(var) + 2
        propertyDict[category].append([line, ''])
        line, boxHeight = map(incrementVars,[line, boxHeight])      
    boxWidth += 4
    return propertyDict, boxHeight, boxWidth


def incrementVars(x):
    return x+1


def initCurses(inactiveColor, windowBg, boxText, boxBg):
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


def killBox(stdscr):
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


def launch(menu, inactiveColor, windowBg, boxText, boxBg):
    content = [x[0] for x in menu]
    contentDict = {
        'header' : [tcs.APP_INFO],
        'content' : content,
        'footer' : [tcs.FOOTER]
    }
    stdscr = initCurses(inactiveColor, windowBg, boxText, boxBg)
    buildBox(contentDict)
    # Waits for keypress (so the program doesnt just terminate while being WIP)
    cmd = chr(stdscr.getch())
    killBox(stdscr)
    return cmd