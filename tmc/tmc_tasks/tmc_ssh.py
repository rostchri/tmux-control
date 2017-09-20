import json

#reads taskf_ssh.json, returns dict
def get_default_targets():
    with open('tmc/configs/taskf_ssh.json', 'r') as f:
        machines = f.read()
s = json.loads(machines)
    return machines


#returns dict {'machine':'ssh_command'}
def create_ssh_commands(ssh_machines=get_default_targets()):
    ssh_dict = {}
    for el in ssh_machines:
        user = el['user']
        system = el['machine']
        el['cmd'] = 'neofetch && ssh {0}@{1}'.format(user, system)
    return ssh_machines

