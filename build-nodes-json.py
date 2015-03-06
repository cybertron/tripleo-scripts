#!/usr/bin/env python

import json
import os
import sys

from novaclient import client as novaclient

bmc_base = 'bmc'
baremetal_base = 'baremetal'
private_net = 'private'
provision_net = 'undercloud'
username = os.environ.get('OS_USERNAME')
password = os.environ.get('OS_PASSWORD')
tenant = os.environ.get('OS_TENANT_NAME')
auth_url = os.environ.get('OS_AUTH_URL')
node_template = {
    'pm_type': 'pxe_ipmitool',
    'mac': '',
    'cpu': '',
    'memory': '',
    'disk': '',
    'arch': 'x86_64',
    'pm_user': 'admin',
    'pm_password': 'password',
    'pm_addr': '',
    }

if not username or not password or not tenant or not auth_url:
    print 'Source an appropriate rc file first'
    sys.exit(1)

nova = novaclient.Client(2, username, password, tenant, auth_url)

bmcs = nova.servers.list(search_opts={'name': bmc_base})
baremetals = nova.servers.list(search_opts={'name': baremetal_base})
nodes = []

for pair in zip(bmcs, baremetals):
    bmc = pair[0]
    baremetal = pair[1]
    node = dict(node_template)
    node['pm_addr'] = bmc.addresses[private_net][0]['addr']
    node['mac'] = [baremetal.addresses[provision_net][0]['OS-EXT-IPS-MAC:mac_addr']]
    flavor = nova.flavors.get(baremetal.flavor['id'])
    node['cpu'] = flavor.vcpus
    node['memory'] = flavor.ram
    node['disk'] = flavor.disk
    nodes.append(node)

with open('nodes.json', 'w') as node_file:
    node_file.write(json.dumps({'nodes': nodes}))
