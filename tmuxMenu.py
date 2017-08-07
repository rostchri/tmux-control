#! /usr/local/bin/python3

import libtmux
import os
import sys

configDir = "configs"
server = libtmux.Server()


class Config:

    def __init__(self, name):
        self.name = name
        self.file = os.path.join(configDir, self.name + ".txt")
        if self.file in os.listdir(configDir):
            with open(self.file, "r") as f:
                self.rawLines = f.readlines()
                self.data = self.loadData()
        else:
            self.data = self.makeConfig()
    
    def create(self):
        pass
    
    def makeConfig(self):
        pass
        
    def loadData(self):
        self.machineNames, self.machineInfos = [], []
        for line in self.rawLines:
            self.machineNames, self.machineInfos .append(line.split(","))

    def saveConfig(self):
        self.savingData = self.data.replace("a", "b")
        with open(self.file, "w") as f:
            f.write(self.savingData)


class Menu:

    def __init__(self, name, options, prompt):
        self.menuDict = {}
        self.name = name
        self.options = options
        self.prompt = prompt
        self.text = self.buildMenu()

    def buildMenu(self):
        for option in self.options:
            self.menuDict[self.options.index(option)] = option
            self.menuDict[self.options.index(option)][0] = "{0}".format(self.menuDict[self.options.index(option)][0])
            i = 0
            self.text = ""
            for option in self.menuDict:
                self.text += "{0}: {1}\n".format(i+1, self.menuDict[option][0])
                i+=1
        return(self.text)

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
        main(prompt)


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


def getConfigs():
    pass


def handle(func):
    func()


def main(prompt):

    startMenu = [
        ["first action", functionA],
        ["second action", functionB],
        ["quit", quit],
    ]
    thisMenu = Menu("start menu", startMenu, prompt)
    thisMenu.launch()


app()