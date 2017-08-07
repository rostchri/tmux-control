#! /usr/local/bin/python3

import libtmux
import os
import sys

server = libtmux.Server()

class Menu:

    def __init__(self, name, options, prompt):
        
        self.menuDict = {}
        self.name = name
        self.options = options
        for option in self.options:
            self.menuDict[options.index(option)] = option
            self.menuDict[options.index(option)][0] = "{0}".format(self.menuDict[options.index(option)][0])
        self.prompt = prompt
        i = 0
        self.text = ""
        for option in self.menuDict:
            self.text += "{0}: {1}\n".format(i+1, self.menuDict[option][0])
            i+=1

    def launch(self):
        print(self.text)
        cmd = None
        while cmd not in range(len(self.menuDict)):
            cmd = input(self.prompt)
            if int(cmd) - 1 in range(len(self.menuDict)):
                handle(self.menuDict[int(cmd) - 1][1])
            else:
                print("your cmd was not accepted:\n{0}\n{1}".format(cmd, type(cmd)))


def app():
    if __name__ == "__main__":
        prompt = buildPrompt()
        mainMenu(prompt)


def buildPrompt():
    os.system("whoami > {0} && hostname >> {0}".format("promptInfo.txt"))
    with open("promptInfo.txt", "r") as f:
        promptInfo = f.readlines()
        currentUser = promptInfo[0][:-1]
        currentMachine = promptInfo[1][:-1]
    return("{0}@{1}:".format(currentUser, currentMachine))


def functionA():
    print("You called function 1")


def functionB():
    print("You called function 2")


def mainMenu(prompt):
    options = [
        ["first action", functionA],
        ["second action", functionB],
        ["quit", quit],
    ]
    thisMenu = Menu("main menu", options, prompt)
    thisMenu.launch()


def handle(func):
    func()


app()