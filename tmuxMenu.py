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
        reading = True
        while reading:
            print("enter your config-content!\nsyntax: machine,info;machine,info [...]")
            cmd = input(prompt)
            if cmd == "q":
                reading = False
            else:
                try:
                    machines = self.parseConfig(cmd.split(";"))
                    for id, info in machines:
                        id, info = id, info
                        self.machines[id] = info
                except TypeError as e:
                    print("something went wrong!\ninput: {0}".format(cmd))
        print("alright, your machines:")
        print(self.machines)
            
    def create(self):
        cmd, reading, self.rawLines = str, 1, []
        info = "creating config:"
        initPrompt = "Is that name correct? (y/n)\n" + prompt
        secondPrompt = "Enter a new name for the config please"
        self.name = self.nameValidator(info, initPrompt, secondPrompt, self.name)
        self.build()

    def edit(self):
        pass

    def parseConfig(self, rawLines):
        for line in rawLines:
            #print(line)
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
                sys.exit()
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
        cmd = None
        if len(self.menuDict) == 1:
            handle(self.menuDict[0][1])
            return(0)
        while cmd not in range(len(self.menuDict)):
            print(self.text)
            cmd = input(prompt)
            if cmd == "q":
                return(sys.exit())
            try:
                int(cmd)
                if int(cmd) - 1 in range(len(self.menuDict)):
                    handle(self.menuDict[int(cmd)-1][1])
                    return(self.menuDict[int(cmd)-1])
                else:
                    print("your answer {0} was not in range! (min 1, max {1})".format(cmd, len(self.menuDict)))
            except:
                print("your cmd was not accepted:\n{0}\nplease enter a valid command (a number between 1 and {1})".format(cmd, len(self.menuDict)))

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
        #["edit config", sessionConfig.edit]
        ["launch tmux-session with config", launchSession],
    ]
    return(startMenu)


def handle(func):
    func()


def launchSession():
    print("session launched")


def main():
    configMenu = Menu("testConfig", getConfigs())
    chosenConfig = "TOBEDETERMINED"
    sessionConfig = Config(chosenConfig)

    startMenu = getStart()
    mainMenu = Menu("start menu", startMenu)
    run = 1
    while run != 0:
        run = mainMenu.launch()
        return(run)


app()