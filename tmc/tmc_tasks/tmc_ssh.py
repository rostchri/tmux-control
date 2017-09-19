#returns dict {'machine':'ssh_command'} for els in list [['user', 'machine'],[...]]
def create_ssh_commands(ssh_machines):
    ssh_dict = {}
    for el in ssh_machines:
        el['cmd'] = 'ssh {0}@{1}'.format(el['user'], el['machine'])
    return(ssh_machines)

