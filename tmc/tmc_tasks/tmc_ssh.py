import json

#reads taskf_ssh.json, returns dict
def get_targets(f):
    with open(f, 'r') as f:
        machines = f.read()
    machines = json.loads(machines)
    return machines


#returns dict {'machine':'ssh_command'}
def create_ssh_commands(f):
    ssh_machines = get_targets(f)
    ssh_dict = {}
    for el in ssh_machines:
        user = el['user']
        system = el['machine']
        el['cmd'] = 'neofetch && ssh {0}@{1}'.format(user, system)
    return ssh_machines

