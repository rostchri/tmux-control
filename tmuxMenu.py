#! /usr/local/bin/python3

import libtmux
import os
import sys

configDir = "configs"
server = libtmux.Server()


class Config:

    def __init__(self, name):
        self.machines = {}
        self.name = name
        self.file = os.path.join(configDir, self.name + ".txt")
        if self.file in os.listdir(configDir):
            with open(self.file, "r") as f:
                ids, infos = self.parseConfig(f.readlines())
            for i, id in enumerate(ids):
                self.machines[id] = infos[i]
        else:
            self.data = self.create()

    def build(self):
        print("\nenter your config-content!\nsyntax: machine,info;machine,info [...]\nenter q to leave config-reading-mode.")
        reading = True
        while reading:
            cmd = input(prompt)
            if cmd == "q":
                reading = False
            else:
                try:
                    machines = self.parseConfig(cmd.split(";"))
                    for id, info in machines:
                        self.machines[id] = info
                except TypeError as e:
                    print("TypeError!\ninput: {0}".format(cmd))
            
    def create(self):
        cmd, reading, self.rawInfo = str, 1, []
        info = "\ncreating config:"
        initPrompt = "Is that name correct? (y/n)\n{0}".format(prompt)
        secondPrompt = "Enter a new name for the config please"
        self.name = self.nameValidator(info, initPrompt, secondPrompt, self.name)
        self.build()

    def edit(self):
        pass

    def parseConfig(self, rawInfo):
        for line in rawInfo:
            machine = line.split(",", 2)
            yield(machine)
            
    def nameValidator(self, info, initPrompt, secondPrompt, target):
        validated = False
        while not validated:
            print(info + ": " + target)
            cmd = input(initPrompt)
            if cmd == "y":
                result = target
                validated = True
            elif cmd == "n":
                target = input(secondPrompt)
            elif cmd == "q":
                exitApp()
            else:
                print("not a valid command: %s"%(cmd))
        return(result)

    def saveConfig(self):
        self.savingData = self.data.replace("a", "b")
        with open(self.file, "w") as f:
            f.write(self.savingData)


class Menu:
    def __init__(self, name, options):
        self.menuDict = {}
        self.name = name
        self.options = options
        self.text = name + "\n" + self.buildMenu()

    def buildMenu(self):
        for i, option in enumerate(self.options):
            self.menuDict[i] = option
            self.menuDict[i][0] = "{0}".format(self.menuDict[i][0])
        text = ""
        for i, option in enumerate(self.menuDict):
                text += "{0}: {1}\n".format(i+1, self.menuDict[option][0])
        return(text)

    def launch(self):
        cmd = None
        while cmd not in range(len(self.menuDict)):
            print("\n" + self.text[:-1])
            cmd = input(prompt)
            if cmd.isdigit():
                if int(cmd) - 1 in range(len(self.menuDict)):
                    handle(self.menuDict[int(cmd)-1][1])
                    #return(self.menuDict[int(cmd)-1])
                else:
                    print("your answer {0} was not in range! (min 1, max {1})".format(cmd, len(self.menuDict)))

    def result(self):
        return(self.name)


def app():
    global prompt
    if __name__ == "__main__":
        prompt = buildPrompt()
        print("Welcome to tmuxControl!")
        while 1:
            main()


def buildPrompt():
    os.system("whoami > {0} && hostname >> {0}".format("promptInfo.txt"))
    with open("promptInfo.txt", "r") as f:
        promptInfo = f.readlines()
        currentUser = promptInfo[0][:-1]
        currentMachine = promptInfo[1][:-1]
    return("\n{0}@{1}:".format(currentUser, currentMachine))


def functionA():
    print("\nYou called function 1")


def functionB():
    print("\nYou called function 2")


def getConfigs():
    cfgs = []
    for f in os.listdir(configDir):
        if not "DS_Store" in f:
            cfgs.append([f],[os.path.join(configDir, f)])

    configMenu = Menu("testConfig", cfgs)
    chosenConfig = "testConfig"
    sessionConfig = Config(chosenConfig)


def getStart():
    startMenu = [
        ["launch tmux-session with config", launchSession],
        ["manage config", getConfigs],
        ["stop the app", exitApp],

    ]
    return(startMenu)


def handle(func):
    func()


def launchSession():
    print("\nsession launched")


def main():
    startMenu = getStart()
    mainMenu = Menu("Main Menu", startMenu)
    run = 1

    while run != 0:
        run = mainMenu.launch()
        return(run)


def exitApp():
    print("goodbye")
    sys.exit(0)


app()