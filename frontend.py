#!/usr/bin/python

import curses


# iterates through the menu-contents dict:
#   determining height/ width of the desired box
#   creating a dict that holds line-numbers and corresponding values
#   returns those three vars (height, width, {lines + content})
def getBoxProperties():
    propertyDict = {}
    boxHeight = 0
    boxWidth = 0
    line = 3
    
    category = 'header'
    propertyDict[category] = []
    for row in contentDict[category]:
        var = row
        propertyDict[category].append([line, var])
        line, boxHeight = map(incrementVars,[line, boxHeight])
        if len(var) > boxWidth:
            boxWidth = len(var)
    propertyDict[category].append([line, '---'])
    line, boxHeight = map(incrementVars,[line, boxHeight])

    category = 'content'
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
        if len(var) > boxWidth:
            boxWidth = len(var)
    propertyDict[category].append([line, '---'])
    line, boxHeight = map(incrementVars,[line, boxHeight])

    category = 'footer'
    propertyDict[category] = []
    for row in contentDict[category]:
        var = row
        propertyDict[category].append([line, var])
        line, boxHeight = map(incrementVars,[line, boxHeight])
        if len(var) > boxWidth:
            boxWidth = len(var)
        
    boxWidth += 4
    return propertyDict, boxHeight, boxWidth


# builds the actual menu:
#   1. gets the properties by calling getBoxProperties
#   2. adds the strings to their respective places and refreshes the window
def makeBox():
    propertyDict, boxHeight, boxWidth = getBoxProperties()
    win = curses.newwin(boxHeight + 2, boxWidth, 5, 35)
    win.bkgd(curses.color_pair(2))

    for line in propertyDict['header']:
        win.addstr(line[0] -2, 2, line[1])

    for line in propertyDict['content']:
        for entity in line:
            if not type(entity) == list:
                win.addstr(line[0] -2, 2, line[1])
            else:
                win.addstr(entity[0] -2, 2, entity[1])

    for line in propertyDict['footer']:
        win.addstr(line[0] -2, 2, line[1]) 

    win.box()
    win.refresh()


# default initialization, receives two pairs of colours (defined at the top of this document)
def initCurses(c1, c2, c3, c4):
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    curses.start_color()
    curses.init_pair(1, c1, c2)
    curses.init_pair(2, c3, c4)
    stdscr.bkgd(curses.color_pair(1))
    stdscr.refresh()
    return stdscr


# terminates the box
def killBox(stdscr):
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()


def launch(contentDict, c1, c2, c3, c4):
    stdscr = initCurses(c1, c2, c3, c4)
    makeBox()
    # waits for keypress (so the program doesnt just terminate while being WIP)
    c = stdscr.getch()
    killBox(stdscr)


def incrementVars(x):
    return x+1


if __name__ == '__main__':

    # dict holding the menu-layout-categories (header content footer)
    contentDict = {
        'header' : ['tmux Control 0.1'],
        'content' : [
            'foo',
            'bar',
            'baz'
        ],
        'footer' : ['tcFooter']
    }

    # assigning some colors to handy vars
    green = curses.COLOR_GREEN
    blue = curses.COLOR_BLUE
    yellow = curses.COLOR_YELLOW
    black = curses.COLOR_BLACK

    # assigning handy vars to neutral parameters
    c1 = green
    c2 = blue
    c3 = yellow
    c4 = black

    launch(contentDict, c1, c2, c3, c4)