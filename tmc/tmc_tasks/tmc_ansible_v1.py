import sys
import os

# ansible v1 imports 
from ansible.inventory import Inventory, InventoryParser, InventoryDirectory

def ansible_inventory(ansiblehosts,subset=None):
  if os.path.isdir(ansiblehosts) or os.path.isfile(ansiblehosts):
    inventory = Inventory(ansiblehosts)
    if subset:
      inventory.subset(subset)
  else:
    print >> sys.stderr, "### ERROR ansible-hosts %s not found" %(ansiblehosts)
  return(inventory)

# import specific variables which are usefull to contact ansible-host
# TODO: it would be possible to get even more information about the ansible-host here
def ansible_variables(inventory,hosts):
  result={}
  group_vars={}
  groups={}

  # TODO: kommt man einfacher an die gruppen?
  for g in inventory.get_groups():
    if not g.name == 'all':
        group_vars[g.name]=g.get_variables()
        #print >> sys.stderr, "# group: %s" %(g.name)
        for h in g.get_hosts():
            #print >> sys.stderr, "   %s" %(h.name)
            if not groups.has_key(h.name):
                groups[h.name]=[]
            groups[h.name].append(g.name)


  for h in inventory.list_hosts(hosts): 
    variables = inventory.get_variables(h) 
    #print >> sys.stderr, variables
    #verbose = ''
    #if variables.has_key('ansible_ssh_host'):
    #    verbose = "%s ansible_ssh_host: \"%s\"" %(verbose,variables['ansible_ssh_host'])
    #if variables.has_key('comment'):
    #    verbose = "%s comment: \"%s\"" %(verbose,variables['comment'])
    #print >> sys.stderr, "# %s%s" %(variables['inventory_hostname'],verbose)
    #print >> sys.stderr, "# %s"   %(variables)

    if not result.has_key(h):
        result[h]={}

    result[h]['groups']=groups[h]
      
    if variables.has_key('ansible_ssh_host'):
        result[h]['ansible_ssh_host'] = variables['ansible_ssh_host']
    if variables.has_key('ansible_ssh_user'):
        result[h]['ansible_ssh_user'] = variables['ansible_ssh_user']
    if variables.has_key('comment'):
        result[h]['comment'] = variables['comment']
    if variables.has_key('inventory_hostname'):
        result[h]['inventory_hostname'] = variables['inventory_hostname']
  return(result)

def create_ansible_v1_commands(myansibleprojectdir,myansiblehostlist=['all']):
    hostsubset = ':'.join(myansiblehostlist)
    inventory = ansible_inventory('%s/hosts' %(myansibleprojectdir),hostsubset)
    variables = ansible_variables(inventory,hostsubset)
    return variables

