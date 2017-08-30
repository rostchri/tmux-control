import json
import os
import sys

import libtmux

import tmc_ui as tcui
import tmc_settings as tcs


class Config:
    def __init__(self, name):
        self.machines = {}
        self.name = name

    # Builds a new config via user-input, returns dict in desired format
    def build(self):
        machines, reading = {}, True
        cfgPrompt = '\nenter your config-content!\nsyntax: machine,info;machine,info [...]\nenter q to leave config-reading-mode.'
        while reading:
            cmd = input(prompt)
            if cmd == 'q':
                reading = False
            else:
                try:
                    segments = self.parse(cmd.split(';'))
                    for id, info in segments:
                        machines[id] = info
                except:
                    errMsg = """Input must be splittable into by-comma-splittable segments with semicolons!
                    Input was:
                    {0}'.format(cmd))"""
                    launchUI(errMsg)
        return machines
            
    # Returns a validated (by self.nameValidator) name for the config
    # (and creates the parameters for self.nameValidator)
    def create(self):
        cmd, reading, self.rawInfo = str, 1, []
        info = '\ncreating config'
        initPrompt = 'Is that name correct? (y/n)\n{0}'.format(prompt)
        secondPrompt = 'Enter a new name for the config please.\n'
        target = input('Name the new config please!\n' + prompt)
        name = self.nameValidator(info, initPrompt, secondPrompt, target)
        return name

    def edit(self):
        pass

    # Loops through a validating-and-replacing-process until the user-input is 'y',
    # returns the validated variable
    def nameValidator(self, info, initPrompt, secondPrompt, target):
        validated = False
        while not validated:
            print(info + ': ' + target)
            cmd = input(initPrompt)
            if cmd == 'y':
                result = target
                validated = True
            elif cmd == 'n':
                target = input(secondPrompt)
            else:
                errMsg = 'not a valid command: {0}'.format(cmd)
                launchUI(errMsg)
        return result

    def new(self):
        self.name = self.create()
        self.machines = self.build()
        self.save()

    # iterates through param, returns comma-split-iterations
    def parse(self, rawInfo):
        for line in rawInfo:
            machine = line.split(',', 2)
            return machine

    def save(self):
        self.file = os.path.join(tcs.CONFIG_DIR, self.name + '.json')
        with open(self.file, 'w') as f:
            json.dump(self.machines, f)

    def setData(self, file, machines):
        self.file = file
        self.machines = machines


# Gets called with a name (to be displayed in the menu) and a list of options for the menu-instance
class Menu:
    # creates the to-be-printed-string by prefixing the return-value of 'self.buildMenu' with the instances name (+ '\n') 
    def __init__(self, name, options):
        self.menuDict = {}
        self.name = name
        self.options = options
        self.text = name + '\n' + self.buildMenu()

    # Builds a dict from raw options with enum-results as keys,
    # comprehends that dicts content as adequate, printable menu-options,
    # returns the result as a string (n: option1 \n n+1: option2)
    def buildMenu(self):
        for i, option in enumerate(self.options):
            self.menuDict[i] = option
            self.menuDict[i][0] = '{0}'.format(self.menuDict[i][0])
        text = ''
        for i, option in enumerate(self.menuDict):
                text += '{0}: {1}\n'.format(i+1, self.menuDict[option][0])
        return text

    # Launches the menu (prints the string)
    # Loops the menu until a valid input has been made
    # On valid input, returns the according value to the chosen option
    def launch(self):
        cmd = None
        while not cmd in range(len(self.menuDict)):
            msg = '\nTEST\n' + self.text[:-1]
            cmd = launchUI(msg)
            if cmd.isdigit():
                if int(cmd) - 1 in range(len(self.menuDict)):
                    return(self.menuDict[int(cmd)-1][1])
                else:
                    errMsg = 'your answer {0} was not in range! (min 1, max {1})'.format(cmd, len(self.menuDict))
                    launchUI(msg)
        return self.name


# Sets the global prompt by calling the prompt-function,
# prints the welcome-message, then calls the main-function
def app():
    global prompt
    prompt = buildPrompt()
    server = libtmux.Server()
    welcomeMsg = 'Welcome to tmuxControl!'
    launchUI(welcomeMsg)
    main()


# Casts 'whoami' and 'hostname' to os, builds and returns a prompt
def buildPrompt():
    promptInfoFile = 'files/promptInfo.txt'
    os.system('whoami > {0} && hostname >> {0}'.format(promptInfoFile))
    with open(promptInfoFile, 'r') as f:
        promptInfo = f.readlines()
        currentUser = promptInfo[0][:-1]
        currentMachine = promptInfo[1][:-1]
    os.unlink(promptInfoFile)
    return '\n{0}@{1}:'.format(currentUser, currentMachine)


# Says Goodbye and quits program
def exitApp():
    goodbyeMsg = '\nGoodbye'
    launchUI(goodbyeMsg)
    sys.exit(0)


# Reads the json-files in tcs.configDir, calls menu (for picking an existing or creating a new config)
def getConfig():
    cfgs = [['Create new config', '']]
    for f in os.listdir(tcs.CONFIG_DIR):
        if 'json' in f:
            cfgs.append([f[:-5], f])
    configMenu = Menu('Config Menu', cfgs)
    chosenConfig = configMenu.launch()
    currentConfig = Config(chosenConfig)
    if chosenConfig in os.listdir(tcs.CONFIG_DIR):
        configFile = os.path.join(tcs.CONFIG_DIR, chosenConfig)
        with open(configFile, 'r') as f:
            machines = json.load(f)   
        currentConfig.setData(configFile, machines)
    else:
        currentConfig.new()


# Will return the tmux-operation(s) to perform on targets
def getOperation():
    return 'operation'


# Initializes the startMenu-options (returns list of lists)
def getStart():
    startMenu = [
        ['Launch tmux-session with config', launchSession],
        ['Manage config', getConfig],
        ['Stop the app', exitApp]
    ]
    return startMenu


# Will return the targets to perform tmux-operations on
def getTargets():
    return [x+1 for x in range(3)]


# Will launch the actual tmux-session - called with:
# a config (list of machines and respective info)
# and a task (for now: ssh-logins (with the included info))
def launchSession(operation, targets):
    #operation(targets)
    launchMsg = 'launch successful!'
    launchUI(launchMsg)


def launchUI(content):
    if type(content) == str:
        content = [[content, getConfig]]
    cmd = tcui.launch(content, tcs.GREEN, tcs.GREEN, tcs.BLACK, tcs.GREEN)
    return cmd


# Instantiates the mainMenu-object (of the Menu-class) with the initial menu-options
# (receives from getStart (which just returns a static dict)),
# then loops the main-menu-launch and calls the returned function
# (depending on the to-be-called-function, parameters may have to be called) (forever)
def main():
    startMenu = getStart()
    cmd = launchUI(startMenu)
    mainMenu = Menu('Main Menu', startMenu)
    run = True
    while run:
        result = mainMenu.launch()
        if 'launchSession' in str(result):
            operation = getOperation()
            targets = getTargets()
            launchSession(operation, targets)
        else:
            result()
        

# The task thats gonna be executed (which this entire thing is about),
# going to be called with a parameter defining the targets (e.g. ssh-connection=operation, machines=targets (including login-information etc))
def operation(targets):
    for target in targets:
        msgTarget = target
    launchSuccessMsg = 'launch successful!'
    launchUI(launchSuccessMsg)