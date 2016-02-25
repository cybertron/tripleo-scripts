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
import pickle
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
NETENV_HEADER = """
resource_registry:
  OS::TripleO::BlockStorage::Net::SoftwareConfig: nic-configs/cinder-storage.yaml
  OS::TripleO::Compute::Net::SoftwareConfig: nic-configs/compute.yaml
  OS::TripleO::Controller::Net::SoftwareConfig: nic-configs/controller.yaml
  OS::TripleO::ObjectStorage::Net::SoftwareConfig: nic-configs/swift-storage.yaml
  OS::TripleO::CephStorage::Net::SoftwareConfig: nic-configs/ceph-storage.yaml

parameter_defaults:
"""
TYPE_LIST = [(0, 'controller.yaml', 'Controller'),
             (1, 'compute.yaml', 'Compute'),
             (2, 'ceph-storage.yaml', 'CephStorage'),
             (3, 'cinder-storage.yaml', 'BlockStorage'),
             (4, 'swift-storage.yaml', 'SwiftStorage')]
ALL_NETS = [('ControlPlane', 'control'),
            ('External', 'external'),
            ('InternalApi', 'internal_api'),
            ('Storage', 'storage'),
            ('StorageMgmt', 'storage_mgmt'),
            ('Tenant', 'tenant'),
            ('Management', 'management')
            ]
# SIMILAR_NETS are the networks with uniform parameters.  ControlPlane and
# External both have some unique ones that require special handling.
SIMILAR_NETS = ALL_NETS[2:]


def _write_nic_configs(data, base_path):
    """Write nic configs based on the data passed in"""
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
                for j in i.get('members', []):
                    _process_bridge_members(j)
                    for k in j.get('members', []):
                        _process_bond_members(k)
                network_config.append(i)
            resource_string = yaml.safe_dump(resources,
                                                default_flow_style=False)
            # Ugly hack to remove unwanted quoting around get_params
            resource_string = resource_string.replace(
                "'{get_param:", "{get_param:")
            resource_string = resource_string.replace("}'", "}")
            f.write(resource_string)
            f.write(OUTPUTS)

def _write_pickle(data, global_data, base_path):
    file_data = {'data': data, 'global_data': global_data}
    pickle.dump(file_data, open(os.path.join(base_path,
                                             'ui-settings.pickle'), 'wb'))

def _write_net_env(data, global_data, base_path):
    """Write network-environment.yaml based on the data passed in"""
    _write_pickle(data, global_data, base_path)
    # This is simple YAML, so instead of generating it with the yaml
    # module, we'll just write it directly as text so we control the
    # formatting.
    with open(os.path.join(base_path,
                            'network-environment.yaml'), 'w') as f:
        def write(content):
            f.write('  ' + content + '\n')
        f.write(NETENV_HEADER)
        if _net_used_all(data, 'ControlPlane'):
            write("ControlPlaneSubnetCidr: '%d'" %
                  global_data['control']['mask'])
            write('ControlPlaneDefaultRoute: %s' %
                  global_data['control']['route'])
            write('EC2MetadataIp: %s' % global_data['control']['ec2'])
        if _net_used_all(data, 'External'):
            write('ExternalNetCidr: %s' % global_data['external']['cidr'])
            write('ExternalAllocationPools: [{"start": "%s", '
                  '"end": "%s"}]' % (global_data['external']['start'],
                                     global_data['external']['end']))
            write('ExternalInterfaceDefaultRoute: %s' %
                  global_data['external']['gateway'])
            write('ExternalNetworkVlanID: %d' %
                  global_data['external']['vlan'])
            write('NeutronExternalNetworkBridge: "%s"' %
                  global_data['external']['bridge'])
        for camel, lower in SIMILAR_NETS:
            if _net_used_all(data, camel):
                write('%sNetCidr: %s' % (camel, global_data[lower]['cidr']))
                write('%sAllocationPools: [{"start": "%s", '
                    '"end": "%s"}]' % (camel,
                                       global_data[lower]['start'],
                                       global_data[lower]['end']))
                write('%sNetworkVlanID: %d' % (camel,
                                               global_data[lower]['vlan']))
        write('DnsServers: ["%s", "%s"]' % (global_data['dns1'],
                                            global_data['dns2']))
        write('BondInterfaceOvsOptions: %s' % global_data['bond_options'])

def _write_net_iso(data, base_path):
    """Write network-isolation.yaml based on the data passed in"""
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
        for i in ALL_NETS[1:]:
            _write_net_iso_entry(f, i[0], data, i[1])

def _write_net_iso_entry(f, net, data, basename=None):
    """Write the entries for a single network to network-isolation.yaml"""
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
    """Check whether a network is used in any nic-config file"""
    return any([_net_used(data, name, fname) for fname, _ in data.items()])

def _net_used(data, name, filename):
    """Determine whether nics are configured to use a network

    Returns whether a nic in filename is configured to use the network
    defined by name.  name is the camelcase form of the network.
    """
    node_data = data[filename]
    for i in node_data:
        if i['network'] == name:
            return True
        for j in i['members']:
            if j['network'] == name:
                return True
    return False

def _process_network_config(d, filename):
    """Tweak config data for top-level interfaces and bridges

    There is some data in the internal data structures of the UI that doesn't
    belong in the output files, or that needs to be adjusted/added.  This
    function is responsible for doing that.
    """
    if d['mtu'] == -1:
        del d['mtu']
    if d['type'] == 'interface' or d['type'] == 'ovs_bridge':
        network = d['network']
        del d['network']
        # This is nonsense unless we're in a bridge
        d.pop('primary', None)
        if d['type'] == 'interface':
            d.pop('members', None)
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
    """The same as _process_network_config, except for bridge members"""
    if nd['mtu'] == -1:
        del nd['mtu']
    if nd['type'] == 'vlan':
        network = nd['network']
        del nd['network']
        nd.pop('name', None)
        if network == 'External':
            # This shares some logic with _process_network_config. Refactor?
            nd['addresses'] = [{'ip_netmask':
                                    '{get_param: ExternalIpSubnet}'}]
            nd['routes'] = [
                {'ip_netmask': '0.0.0.0/0',
                    'next_hop':
                        '{get_param: ExternalInterfaceDefaultRoute}'}]
            nd['vlan_id'] = '{get_param: ExternalNetworkVlanID}'
            if not nd['device']:
                nd.pop('device', None)
        elif network == 'None':
            raise RuntimeError('VLANs must have a network set')
        else:
            vlan_id = '{get_param: %sNetworkVlanID}' % network
            nd['vlan_id'] = vlan_id
            netmask = '{get_param: %sIpSubnet}' % network
            nd['addresses'] = [{'ip_netmask': netmask}]
            nd.pop('routes', None)
            if not nd['device']:
                nd.pop('device', None)
    elif nd['type'] == 'interface':
        nd.pop('network', None)
        nd.pop('addresses', None)
        nd.pop('routes', None)
        nd.pop('use_dhcp', None)
    elif nd['type'] == 'ovs_bond':
        nd.pop('network', None)
        #nd['members'] = [{'type': 'interface', 'name': m1, 'primary': True},
        #                 {'type': 'interface', 'name': m2},
        #                 ]
    return

def _process_bond_members(nd):
    if nd['mtu'] == -1:
        del nd['mtu']
    if nd['type'] == 'interface':
        nd.pop('addresses')
        nd.pop('network')
        nd.pop('use_dhcp')
        nd.pop('routes')

def _validate_config(data, global_data):
    _check_duplicate_vlans(data, global_data)
    _check_duplicate_networks(data)
    _check_invalid_vlan_devices(data)
    # TODO(bnemec): Check for conflicting cidrs
    #               Duplicate nics
    #               Duplicate bonds
    #               Warn if vlan device is not set when using bonds?

def _lower_to_camel(lower):
    """Given a lower-case network name, return the camel-cased form

    Uses the ALL_NETS structure for the mapping.

    Example: control -> ControlPlane
             storage_mgmt -> StorageMgmt
    """
    result = [i[0] for i in ALL_NETS if i[1] == lower]
    if len(result) == 1:
        return result[0]
    raise IndexError('Expected one result, found: %d' % len(result))

def _check_duplicate_vlans(data, global_data):
    seen = set()
    for name, d in global_data.items():
        try:
            used = _net_used_all(data, _lower_to_camel(name))
            if d['vlan'] in seen and used:
                raise RuntimeError('Duplicate VLAN found: %s' % d['vlan'])
            if used:
                seen.add(d['vlan'])
        except (TypeError, KeyError, IndexError):
            pass

def _check_duplicate_networks(data):
    err_msg = 'Duplicate network assignment found: %s in %s'
    for filename, d in data.items():
        seen = set()
        for i in d:
            if i['network'] in seen and i['network'] != 'None':
                raise RuntimeError(err_msg % (i['network'], filename))
            for j in i['members']:
                if j['network'] in seen and j['network'] != 'None':
                    raise RuntimeError(err_msg % (j['network'], filename))
                seen.add(j['network'])
            seen.add(i['network'])

def _check_invalid_vlan_devices(data):
    err_msg = 'VLAN device not found: %s'
    for filename, d in data.items():
        bonds = set()
        for i in d:
            if i['type'] == 'ovs_bridge':
                for j in i['members']:
                    if j['type'] == 'ovs_bond':
                        bonds.add(j['name'])
        for i in d:
            if i['type'] == 'ovs_bridge':
                for j in i['members']:
                    if (j['type'] == 'vlan' and j['device'] and
                            j['device'] not in bonds):
                        raise RuntimeError(err_msg % j['device'])

def _load(base_path):
    file_data = pickle.load(open(os.path.join(base_path,
                                              'ui-settings.pickle'), 'rb'))
    nic_data = file_data['data']
    global_data = file_data['global_data']
    return nic_data, global_data

def _index_from_filename(filename):
    return [i[0] for i in TYPE_LIST if i[1] == filename][0]
