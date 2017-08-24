#!/usr/bin/python
# -*- coding: utf-8 -*-

import curses


boxContainer = {
    'header' : ['tmux Control 0.1'],
    'content' : [
        'foo',
        'bar',
        'baz'
    ],
    'footer' : ['tcFooter']
}


def incrementVars(x):
    return x+1


def getBoxProperties():
    boxContent = {}
    boxHeight = 0
    boxWidth = 0
    line = 3
    
    category = 'header'
    boxContent[category] = []
    for row in boxContainer[category]:
        var = row
        boxContent[category].append([line, var])
        line, boxHeight = map(incrementVars,[line, boxHeight])
        if len(var) > boxWidth:
            boxWidth = len(var)
    boxContent[category].append([line, '---'])
    line, boxHeight = map(incrementVars,[line, boxHeight])

    category = 'content'
    boxContent[category] = []
    for row in boxContainer[category]:
        if not type(row[1]) == list:
            var = row
            boxContent[category].append([line, var])
            line, boxHeight = map(incrementVars,[line, boxHeight])
        else:
            for var in row:
                boxContent[category].append([line, var])
                line, boxHeight = map(incrementVars,[line, boxHeight])
        if len(var) > boxWidth:
            boxWidth = len(var)
    boxContent[category].append([line, '---'])
    line, boxHeight = map(incrementVars,[line, boxHeight])

    category = 'footer'
    boxContent[category] = []
    for row in boxContainer[category]:
        var = row
        boxContent[category].append([line, var])
        line, boxHeight = map(incrementVars,[line, boxHeight])
        if len(var) > boxWidth:
            boxWidth = len(var)
        
    boxWidth += 4
    return boxContent, boxHeight, boxWidth


def makeBox():
    boxContent, boxHeight, boxWidth = getBoxProperties()
    win = curses.newwin(boxHeight + 2, boxWidth, 5, 35)
    win.bkgd(curses.color_pair(2))

    for line in boxContent['header']:
        win.addstr(line[0] -2, 2, line[1])

    for line in boxContent['content']:
        for entity in line:
            if not type(entity) == list:
                win.addstr(line[0] -2, 2, line[1])
            else:
                win.addstr(entity[0] -2, 2, entity[1])

    for line in boxContent['footer']:
        win.addstr(line[0] -2, 2, line[1]) 

    win.box()
    win.refresh()
    print(boxContent)


def initCurses():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(1)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    stdscr.bkgd(curses.color_pair(1))
    stdscr.refresh()
    return stdscr


def killBox():
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()


stdscr = initCurses()

makeBox()

c = stdscr.getch()

killBox()