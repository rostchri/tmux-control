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
            self.data = self.create()

    def edit(self):
        pass

    def create(self):
        cmd, reading, self.rawLines = str, 1, []
        self.rawLines = []
        print("creating config: %s" %(self.name))
        print("enter the names of your machines and the respective infos, separated by comma.")
        print("you can add multiple combinations, separated by semicolon.")
        while reading:
            cmd = input(prompt)
            if cmd == "q":
                reading = False
            else:
                try:
                    self.segments = []
                    self.segments = (x for x in cmd.split(";"))
                    for segment in self.segments:
                        self.machineNames[self.segments.index(segment)], self.machineInfos[self.segments.index(segment)] = segment.split(",")
                except:
                    print("something went wrong!\ninput: {0}".format(cmd))
        
    def loadData(self):
        self.machineNames, self.machineInfos = [], []
        for line in self.rawLines:
            self.machineNames[self.rawLines.index(line)], self.machineInfos[self.rawLines.index(line)] = line.split(",")

    def saveConfig(self):
        self.savingData = self.data.replace("a", "b")
        with open(self.file, "w") as f:
            f.write(self.savingData)


class Menu:
    def __init__(self, name, options):
        self.menuDict = {}
        self.name = name
        self.options = options
        self.text = self.buildMenu()

    def buildMenu(self):
        #for option in self.options:
        #    self.menuDict[self.options.index(option)] = option
        #    self.menuDict[self.options.index(option)][0] = "{0}".format(self.menuDict[self.options.index(option)][0])
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
            cmd = input(prompt)
            if int(cmd) - 1 in range(len(self.menuDict)):
                handle(self.menuDict[int(cmd) - 1][1])
            else:
                print("your cmd was not accepted:\n{0}\n{1}".format(cmd, type(cmd)))
        return(cmd)

    def result(self):
        return(self.name)


def app():
    global prompt
    if __name__ == "__main__":
        prompt = buildPrompt()
        while 1:
            main()


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
    cfgs = []
    for f in os.listdir(configDir):
        if not "DS_Store" in f:
            cfgs.append([f],[os.path.join(configDir, f)])
    return(cfgs)


def getStart():
    startMenu = [
        ["edit config", sessionConfig.edit]
        ["launch tmux-session with config", launchSession],
        ["quit", quit],
    ]
    return(startMenu)


def handle(func):
    func()


def launchSession():
    print("session launched")


def main():
    choseConfig = Menu("chose config", getConfigs())
    chosenConfig = choseConfig.result()
    sessionConfig = Config(chosenConfig)

    mainMenu = Menu("start menu", getStart)
    run = mainMenu.launch()
    while run != 0:
        mainMenu.launch()


app()