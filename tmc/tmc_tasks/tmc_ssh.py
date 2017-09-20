import json

#reads default ssh-targets ('taskf_ssh.json' in configs), returns dict
def get_default_targets():
    with open('tmc/configs/taskf_ssh.json', 'r') as f:
        machines = f.read()
        machines = json.loads(machines)
    return machines


#returns dict {'machine':'ssh_command'} for els in list [['user', 'machine'],[...]]
def create_ssh_commands(ssh_machines=get_default_targets()):
    ssh_dict = {}
    for el in ssh_machines:
        el['cmd'] = 'neofetch && ssh {0}@{1}'.format(el['user'], el['machine'])
    return ssh_machines

