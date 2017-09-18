#returns dict {'machine':'ssh_command'} for els in list [['user', 'machine'],[...]]
def ssh_command(ssh_machines):
    ssh_dict = {}
    for el in ssh_machines:
        el[0] = ssh_user
        el[1] = ssh_machine
        cmd_string = 'ssh {0}@{1}'.format(ssh_user, ssh_machine)
        ssh_dict[ssh_machine] = cmd_string
    return(ssh_dict)

