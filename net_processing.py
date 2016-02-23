# Copyright 2016 Red Hat Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import os
import yaml

PARAMS = """heat_template_version: 2015-04-30

parameters:
  ControlPlaneIp:
    default: ''
    description: IP address/subnet on the ctlplane network
    type: string
  ExternalIpSubnet:
    default: ''
    description: IP address/subnet on the external network
    type: string
  InternalApiIpSubnet:
    default: ''
    description: IP address/subnet on the internal API network
    type: string
  StorageIpSubnet:
    default: ''
    description: IP address/subnet on the storage network
    type: string
  StorageMgmtIpSubnet:
    default: ''
    description: IP address/subnet on the storage mgmt network
    type: string
  TenantIpSubnet:
    default: ''
    description: IP address/subnet on the tenant network
    type: string
  ManagementIpSubnet: # Only populated when including environments/network-management.yaml
    default: ''
    description: IP address/subnet on the management network
    type: string
  ExternalNetworkVlanID:
    default: 10
    description: Vlan ID for the external network traffic.
    type: number
  InternalApiNetworkVlanID:
    default: 20
    description: Vlan ID for the internal_api network traffic.
    type: number
  StorageNetworkVlanID:
    default: 30
    description: Vlan ID for the storage network traffic.
    type: number
  StorageMgmtNetworkVlanID:
    default: 40
    description: Vlan ID for the storage mgmt network traffic.
    type: number
  TenantNetworkVlanID:
    default: 50
    description: Vlan ID for the tenant network traffic.
    type: number
  ManagementNetworkVlanID:
    default: 60
    description: Vlan ID for the management network traffic.
    type: number
  ExternalInterfaceDefaultRoute:
    default: '10.0.0.1'
    description: default route for the external network
    type: string
  ControlPlaneSubnetCidr: # Override this via parameter_defaults
    default: '24'
    description: The subnet CIDR of the control plane network.
    type: string
  ControlPlaneDefaultRoute: # Override this via parameter_defaults
    description: The default route of the control plane network.
    type: string
  DnsServers: # Override this via parameter_defaults
    default: []
    description: A list of DNS servers (2 max for some implementations) that will be added to resolv.conf.
    type: comma_delimited_list
  EC2MetadataIp: # Override this via parameter_defaults
    description: The IP address of the EC2 metadata server.
    type: string

"""
BASE_RESOURCE_YAML = """
resources:
  OsNetConfigImpl:
    type: OS::Heat::StructuredConfig
    properties:
      group: os-apply-config
      config:
        os_net_config:
          network_config:
"""
BASE_RESOURCE = yaml.safe_load(BASE_RESOURCE_YAML)
OUTPUTS = """
outputs:
  OS::stack_id:
    description: The OsNetConfigImpl resource.
    value: {get_resource: OsNetConfigImpl}
"""

TYPE_LIST = [(0, 'controller.yaml', 'Controller'),
             (1, 'compute.yaml', 'Compute'),
             (2, 'ceph-storage.yaml', 'CephStorage'),
             (3, 'cinder-storage.yaml', 'BlockStorage'),
             (4, 'swift-storage.yaml', 'SwiftStorage')]


def _write_nic_configs(data, base_path):
    nic_path = os.path.join(base_path, 'nic-configs')
    try:
        os.mkdir(base_path)
    except OSError:
        pass
    try:
        os.mkdir(nic_path)
    except OSError:
        pass

    def new_resource():
        resources = copy.deepcopy(BASE_RESOURCE)
        network_config = resources['resources']['OsNetConfigImpl']
        network_config = network_config['properties']['config']
        network_config = network_config['os_net_config']
        network_config['network_config'] = []
        network_config = network_config['network_config']
        return (resources, network_config)

    for filename, node_data in data.items():
        with open(os.path.join(nic_path, filename), 'w') as f:
            f.write(PARAMS)
            resources, network_config = new_resource()
            for i in node_data:
                _process_network_config(i, filename)
                for j in i['members']:
                    _process_bridge_members(j)
                network_config.append(i)
            resource_string = yaml.safe_dump(resources,
                                                default_flow_style=False)
            # Ugly hack to remove unwanted quoting around get_params
            resource_string = resource_string.replace(
                "'{get_param:", "{get_param:")
            resource_string = resource_string.replace("}'", "}")
            f.write(resource_string)
            f.write(OUTPUTS)

def _write_net_iso(data, base_path):
    with open(os.path.join(base_path,
                           'network-isolation.yaml'), 'w') as f:
        def write(content):
            f.write('  ' + content + '\n')
        f.write('resource_registry:\n')
        # When should these be included?
        #write('OS::TripleO::Network::Ports::RedisVipPort: '
                #'../network/ports/vip.yaml')
        #write('OS::TripleO::Controller::Ports::RedisVipPort: '
                #'../network/ports/vip.yaml')
        _write_net_iso_entry(f, 'External', data)
        _write_net_iso_entry(f, 'InternalApi', data, 'internal_api')
        _write_net_iso_entry(f, 'Storage', data)
        _write_net_iso_entry(f, 'StorageMgmt', data, 'storage_mgmt')
        _write_net_iso_entry(f, 'Tenant', data)
        _write_net_iso_entry(f, 'Management', data)

def _write_net_iso_entry(f, net, data, basename=None):
    if basename is None:
        basename = net.lower()

    def write(content):
        format_str = '  ' + content + '\n'
        f.write(format_str % (net, basename))

    if _net_used_all(data, net):
        f.write('  # %s\n' % net)
        write('OS::TripleO::Network::%s: '
              '../network/%s.yaml')
        write('OS::TripleO::Network::Ports::%sVipPort: '
              '../network/ports/%s.yaml')
    for _, filename, template_name in TYPE_LIST:
        if _net_used(data, net, filename):
            write('OS::TripleO::' + template_name + '::Ports::%sPort: '
                  '../network/ports/%s.yaml')

def _net_used_all(data, name):
    return any([_net_used(data, name, fname) for fname, _ in data.items()])

def _net_used(data, name, filename):
    node_data = data[filename]
    for i in node_data:
        if i['network'] == name:
            return True
        for j in i['members']:
            if j['network'] == name:
                return True
    return False

def _process_network_config(d, filename):
    if d['type'] == 'interface' or d['type'] == 'ovs_bridge':
        network = d['network']
        del d['network']
        # This is nonsense unless we're in a bridge
        d.pop('primary', None)
        # TODO: Format this less horribly
        if network == 'ControlPlane':
            d['addresses'] = [
                {'ip_netmask':
                        {'list_join': ['/', ['{get_param: ControlPlaneIp}',
                                            '{get_param: ControlPlaneSubnetCidr}'
                                            ]]}}]
            d['routes'] = [{'ip_netmask': '169.254.169.254/32',
                            'next_hop': '{get_param: EC2MetadataIp}'}]
            # HACK!  Typically non-controller nodes will need this, but
            # it's not a safe assumption.  It's also not necessarily true
            # that controller nodes don't need it.
            if filename != 'controller.yaml':
                d['routes'].append({'default': True,
                                    'next_hop': '{get_param: ControlPlaneDefaultRoute}'})
        elif network == 'External':
            d['addresses'] = [{'ip_netmask':
                                    '{get_param: ExternalIpSubnet}'}]
            d['routes'] = [
                {'ip_netmask': '0.0.0.0/0',
                    'next_hop':
                        '{get_param: ExternalInterfaceDefaultRoute}'}]
        elif network == 'None':
            d.pop('addresses', None)
            d.pop('routes', None)
        else:
            d['addresses'] = [{'ip_netmask':
                                    '{get_param: %sIpSubnet}' % network}]
            del d['routes']

def _process_bridge_members(nd):
    if nd['type'] == 'vlan':
        vlan_id = '{get_param: %sNetworkVlanID}' % nd['network']
        nd['vlan_id'] = vlan_id
        netmask = '{get_param: %sIpSubnet}' % nd['network']
        nd['addresses'] = [{'ip_netmask': netmask}]
    return
