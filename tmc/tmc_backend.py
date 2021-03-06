import json
import os
import sys
import time

import libtmux

from tmc_modules import tmc_session_manager
from tmc_tasks import tmc_ssh
from tmc_tasks import tmc_ansible_v1
import tmc_ui as tcui
import tmc_settings as tcs


example_file = 'tmc/configs/taskf_ssh.json'

class Config:
    
    def __init__(self, name):
        self.machines = {}
        self.name = name
    
    # Builds a new config via user-input, returns dict in desired format
    def build(self):
        machines, reading = {}, True
        cfg_prompt = [
            ['enter your config-content!'],
            ['syntax: machine,info;machine,info [...]'],
            ['enter q to leave config-reading-mode.'],
            [''],
            ['Press any key to enter reading mode']
        ]
        while reading:
            cmd = launch_ui(cfg_prompt, 'str')
            if cmd == 'q':
                reading = False
            else:
                try:
                    segments = cmd.split(';')
                    for x in segments:
                        print('parsing ' + x)
                        machine, info = self.parse(x)
                        machines[machine] = info
                except:
                    err_msg = [
                        ['Input-format must be key,val;key,val'],
                        ['Input was:'],
                        ['{0}'.format(cmd)]
                    ]
                    launch_ui(err_msg, 'str')
        return machines
            
    # Returns a validated (by self.name_validator) name for the config
    # (and creates the parameters for self.name_validator)
    def create(self):
        cmd, reading, self.raw_info = str, 1, []
        info = 'creating config'
        init_prompt = 'Is that name correct? (y/n)'
        second_prompt = 'Enter a new name for the config please.'
        target = launch_ui('Name the new config please!', 'str')
        validation_prompt = [[target], [init_prompt], ['']]
        name = self.name_validator(info, init_prompt, second_prompt, target, validation_prompt)
        return name

    def edit(self):
        pass

    # Loops through a validating-and-replacing-process until the user-input is 'y',
    # returns the validated variable
    def name_validator(self, info, init_prompt, second_prompt, target, validation_prompt):
        validated = False
        while not validated:
            cmd = launch_ui(validation_prompt, 'chr')
            if cmd == 'y':
                result = target
                validated = True
            elif cmd == 'n':
                target = launch_ui(second_prompt, 'chr')
            else:
                err_msg = 'not a valid command: {0}'.format(cmd)
                launch_ui(err_msg, 'chr')
        return result

    def new(self):
        self.name = self.create()
        self.machines = self.build()
        self.save()

    # iterates through param, returns comma-split-iterations
    def parse(self, data):
        machine, info = data.split(',')
        return machine, info

    def save(self):
        self.file = os.path.join(tcs.CONFIG_DIR, self.name + '.json')
        with open(self.file, 'w') as f:
            json.dump(self.machines, f)

    def set_data(self, file, machines):
        self.file = file
        self.machines = machines


# called with a name (to be displayed in the menu) and a list of options for the menu-instance
class Menu:
    
    def __init__(self, name, options):
        self.menu_dict = {}
        self.name = name
        self.options = options
        self.text = [[self.name]] + self.build_menu()

    # Builds a dict from raw options with enum-results as keys,
    # comprehends that dicts content as adequate, printable menu-options,
    # returns the result as a string (n: option1 \n n+1: option2)
    def build_menu(self):
        for i, option in enumerate(self.options):
            self.menu_dict[i] = option
            self.menu_dict[i][0] = '{0}'.format(self.menu_dict[i][0])
        text = []
        for i, option in enumerate(self.menu_dict):
            text.append(['{0}: {1}'.format(i+1, self.menu_dict[option][0])])
        text.append('')
        return text

    # Launches the menu (prints the string)
    # Loops the menu until a valid input has been made
    # On valid input, returns the according value to the chosen option
    def launch(self):
        cmd = None
        while not cmd in range(len(self.menu_dict)):
            msg = self.text[:-1]
            cmd = launch_ui(msg, 'chr')
            if cmd.isdigit():
                if int(cmd) - 1 in range(len(self.menu_dict)):
                    return(self.menu_dict[int(cmd)-1][1])
                else:
                    err_msg = 'your answer was not in range!'
                    launch_ui(msg, 'chr')
        return self.name


# Sets the global prompt by calling the prompt-function,
# prints the welcome-message, then calls the main-function
def app():
    global prompt
    prompt = build_prompt()
    welcome_msg = 'Welcome to tmuxControl!'
    launch_ui(welcome_msg, 'chr')
    main()


# Casts 'whoami' and 'hostname' to os, builds and returns a prompt
def build_prompt():
    prompt_info_file = tcs.FILE_DIR + '/prompt_info.txt'
    if not os.path.isdir(tcs.FILE_DIR):
        os.mkdir(tcs.FILE_DIR)
    os.system('whoami > {0} && hostname >> {0}'.format(prompt_info_file))
    with open(prompt_info_file, 'r') as f:
        prompt_info = f.readlines()
        current_user = prompt_info[0][:-1]
        current_machine = prompt_info[1][:-1]
    os.unlink(prompt_info_file)
    return '\n{0}@{1}:'.format(current_user, current_machine)


# Says Goodbye and quits program
def exit_app():
    bye_msg = 'Goodbye'
    launch_ui(bye_msg, 'chr')
    os.system('tmux kill-session -t tmc_ops')
    os.system('tmux kill-session -t tmc_adm')
    sys.exit(0)


# Reads jsons in tcs.configDir, calls menu (for picking an existing or creating a new config)
def get_config():
    cfgs = [['Create new config', '']]
    if not os.path.isdir(tcs.CONFIG_DIR):
        os.mkdir(tcs.CONFIG_DIR)
    for f in os.listdir(tcs.CONFIG_DIR):
        if 'json' in f:
            cfgs.append([f[:-5], f])
    config_menu = Menu('Config Menu', cfgs)
    chosen_config = config_menu.launch()
    current_config = Config(chosen_config)
    if chosen_config in os.listdir(tcs.CONFIG_DIR):
        config_file = os.path.join(tcs.CONFIG_DIR, chosen_config)
        with open(config_file, 'r') as f:
            machines = json.load(f)   
        current_config.set_data(config_file, machines)
    else:
        current_config.new()


# Initializes the start_menu-options (returns list of lists)
def get_start():
    start_menu = [
        ['Launch tmux-session with config', execute],
        ['Manage config', get_config],
        ['Stop the app', exit_app]
    ]
    return start_menu


# Will launch the actual tmux-session - called with:
# a config (list of machines and respective info)
# and a task (for now: ssh-logins (with the included info))


def launch_ui(content, desired_return):
    if type(content) == str:
        content = [[content]]
    cmd = tcui.launch(content, tcs.BLACK, tcs.BLACK, tcs.WHITE, tcs.BLACK, desired_return)
    return cmd


# Instantiates the main_menu-object (of the Menu-class) with the initial menu-options
# (receives from get_start (which just returns a static dict)),
# then loops the main-menu-launch and calls the returned function
# (depending on the to-be-called-function, parameters may have to be called) (forever)
def main():
    start_menu = get_start()
    main_menu = Menu('Main Menu', start_menu)
    run = True
    while run:
        cmd = main_menu.launch()
        cmd()
        cmd = ''
        

# The task thats gonna be executed (which this entire thing is about),
# going to be called with a parameter defining the targets,
# (e.g. ssh-connection=task, machines=targets (including login-information etc))
def execute():
    init_ops()
    launch_msg = 'launch successful!'
    launch_ui(launch_msg, 'chr')


# gets the commands by the operations respective module (tmc_$OPERATION),
# launches one window per machine and issues the dicts cmd-value to that window
def init_ops(f=example_file, operation='ansible'):
    server = libtmux.Server()
    if operation == 'ssh':
        # get dict with machine-info and ssh-commands (key = ssh)
        target_dict = tmc_ssh.create_ssh_commands(f)
    elif operation == 'ansible':
        target_dict = tmc_ansible_v1.create_ansible_v1_commands('/home/dey25201/Projekte/Talanx/ansible')
    elif operation == 'foo':
        # target_dict = tmc_foo.create_foo_commands()
        pass
    # add window-names and -ids to target-dict (window_id, window_name)
    # also actually creates ops-session and the windows
    print >> sys.stderr, "%s" %(target_dict)
    try:
      target_dict = tmc_session_manager.create_windows(target_dict)
      #session = server.find_where({ "session_name": "tmc_ops" })
      #pane_id = 1
      #for el in target_dict:
      #  window = session.find_where({ "window_name": el['window_name']})
      #  pane = window.select_pane('%{0}'.format(pane_id))
      #  pane = pane.select_pane()
      #  pane.send_keys(el['cmd'])
      #  pane_id += 1
    except (Exception,),e:
      exc_type, exc_obj, exc_tb = sys.exc_info()
      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
      print >> sys.stderr, "### Unexpected exception: '%s' [%s] in file '%s' at line: %d" % (str(e), exc_type, fname, exc_tb.tb_lineno)
