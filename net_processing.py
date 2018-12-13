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

import collections
import copy
import itertools
import os
import pickle
import yaml

import netaddr

TEMPLATE_VERSION = {1: '2015-04-30',
                    2: 'ocata',
                    }
PARAMS = """heat_template_version: %s

parameters:
  ControlPlaneIp:
    default: ''
    description: IP address/subnet on the ctlplane network
    type: string
  ExternalIpSubnet:
    default: ''
    description: IP address/subnet on the external network
    type: string
  ExternalInterfaceRoutes:
    default: []
    description: >
      Routes for the external network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  InternalApiIpSubnet:
    default: ''
    description: IP address/subnet on the internal_api network
    type: string
  InternalApiInterfaceRoutes:
    default: []
    description: >
      Routes for the internal_api network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  StorageIpSubnet:
    default: ''
    description: IP address/subnet on the storage network
    type: string
  StorageInterfaceRoutes:
    default: []
    description: >
      Routes for the storage network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  StorageMgmtIpSubnet:
    default: ''
    description: IP address/subnet on the storage_mgmt network
    type: string
  StorageMgmtInterfaceRoutes:
    default: []
    description: >
      Routes for the storage_mgmt network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  TenantIpSubnet:
    default: ''
    description: IP address/subnet on the tenant network
    type: string
  TenantInterfaceRoutes:
    default: []
    description: >
      Routes for the tenant network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  ManagementIpSubnet: # Only populated when including environments/network-management.yaml
    default: ''
    description: IP address/subnet on the management network
    type: string
  ManagementInterfaceRoutes:
    default: []
    description: >
      Routes for the management network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
  BondInterfaceOvsOptions:
    default: 'bond_mode=active-backup'
    description: The ovs_options string for the bond interface. Set things like
                 lacp=active and/or bond_mode=balance-slb using this option.
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
  ControlPlaneStaticRoutes:
    default: []
    description: >
      Routes for the ctlplane network traffic.
      JSON route e.g. [{'destination':'10.0.0.0/16', 'nexthop':'10.0.0.1'}]
      Unless the default is changed, the parameter is automatically resolved
      from the subnet host_routes attribute.
    type: json
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
BASE_RESOURCE_YAML_2 = """
resources:
  OsNetConfigImpl:
    type: OS::Heat::SoftwareConfig
    properties:
      group: script
      config:
        str_replace:
          template:
            get_file: /usr/share/openstack-tripleo-heat-templates/network/scripts/run-os-net-config.sh
          params:
            $network_config:
              network_config:
"""
BASE_RESOURCE_2 = yaml.safe_load(BASE_RESOURCE_YAML_2)
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
README = """Generated Network Isolation Templates
-------------------------------------
These templates were generated by the UI tool at
https://github.com/cybertron/tripleo-scripts#net-iso-genpy

ui-settings.pickle is specific to the tool.  TripleO will not use it when
doing deployments with these templates, but it is needed to be able to
load the templates into the UI again.  Note that the UI only reads this file,
so any changes made by hand to the templates will not be reflected in the UI.

The network-isolation.yaml file needs to reference the port files shipped with
tripleo-heat-templates, so by default the tool generates the paths assuming
network-isolation.yaml will be copied into the environments/ directory of
tripleo-heat-templates.

If the standard tripleo-heat-templates are in use, then the
network-isolation-absolute.yaml file can be used instead.  It has hard-coded
references to the port files in /usr/share/openstack-tripleo-heat-templates.

If the generated network isolation templates are at ~/generated-templates, an
example deployment command would look like:

openstack overcloud deploy --templates -e ~/generated-templates/network-isolation-absolute.yaml -e ~/generated-templates/network-environment.yaml
"""
V6_NET_ISO_PARAMS="""parameter_defaults:
  CephIPv6: True
  CorosyncIPv6: True
  MongoDbIPv6: True
  NovaIPv6: True
  RabbitIPv6: True
  MemcachedIPv6: True
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
# Used by _order_dict
FIRST_KEYS=['type', 'name']
# members should always be last so keys are not split over a large members list
LAST_KEYS=['addresses', 'routes', 'members']

# Borrowed from
# http://stackoverflow.com/questions/9951852/pyyaml-dumping-things-backwards
def ordered_representer(dumper, data):
    return dumper.represent_mapping(u'tag:yaml.org,2002:map', data.items(),
                                    flow_style=False)
yaml.SafeDumper.add_representer(collections.OrderedDict, ordered_representer)


def _order_dict(data):
    """Order dict in a more human-readable way

    The results will ordered as follows:
    FIRST_KEYS
    all keys not in FIRST_KEYS or LAST_KEYS in alphabetical order
    LAST_KEYS

    This must be the last thing done before the data is dumped as YAML.
    Any further manipulation of the data after this is run on it may change
    the ordering.

    If data has a key named 'members' then _order_dicts will be called
    recursively on its value.

    :param data: The dict to be ordered.
    """
    new_dict = collections.OrderedDict()
    filter_keys = FIRST_KEYS + LAST_KEYS
    rest = {k: v for k, v in data.items() if k not in filter_keys}
    for key in FIRST_KEYS:
        if key in data:
            new_dict[key] = data[key]
    for key in sorted(rest.keys()):
        new_dict[key] = rest[key]
    for key in LAST_KEYS:
        if key in data:
            new_dict[key] = data[key]
    if 'members' in new_dict:
        _order_dicts(new_dict['members'])

    return new_dict


def _order_dicts(node_data):
    """Convert dicts in node_data to a more human-readable format

    :param node_data: A list of dicts to order
    """
    for index, item in enumerate(node_data):
        node_data[index] = _order_dict(item)


def _write_nic_configs(data, global_data, base_path):
    """Write nic configs based on the data passed in"""
    nic_path = os.path.join(base_path, 'nic-configs')
    try:
        os.mkdir(nic_path)
    except OSError:
        pass
    template_version = global_data.get('version', 1)

    def new_resource():
        if template_version == 1:
            resources = copy.deepcopy(BASE_RESOURCE)
            network_config = resources['resources']['OsNetConfigImpl']
            network_config = network_config['properties']['config']
            network_config = network_config['os_net_config']
            network_config['network_config'] = []
            network_config = network_config['network_config']
        else:
            # Version 2, using os-net-config script from tht
            resources = copy.deepcopy(BASE_RESOURCE_2)
            network_config = resources['resources']['OsNetConfigImpl']
            network_config = network_config['properties']['config']
            network_config = network_config['str_replace']['params']
            network_config = network_config['$network_config']
            network_config['network_config'] = []
            network_config = network_config['network_config']
        return (resources, network_config)

    for filename, node_data in data.items():
        with open(os.path.join(nic_path, filename), 'w') as f:
            f.write(PARAMS % TEMPLATE_VERSION[template_version])
            resources, network_config = new_resource()
            for i in node_data:
                _process_network_config(i, filename,
                                        global_data.get('auto_routes', True))
                for j in i.get('members', []):
                    _process_bridge_members(j, i.get('members', []))
                    for k in j.get('members', []):
                        _process_bond_members(k)
                network_config.append(i)
            _order_dicts(network_config)
            resource_string = yaml.safe_dump(resources,
                                             default_flow_style=False)
            # Ugly hack to remove unwanted quoting around get_params
            resource_string = resource_string.replace(
                "'{get_param:", "{get_param:")
            resource_string = resource_string.replace("}'", "}")
            f.write(resource_string)
            f.write(OUTPUTS)

def _write_pickle(data, global_data, base_path):
    # Useful for generating the input json for a unit test
    #import json
    #print json.dumps(data)
    #print json.dumps(global_data)
    try:
        os.mkdir(base_path)
    except OSError:
        pass
    with open(os.path.join(base_path, 'README'), 'w') as f:
        f.write(README)
    file_data = {'data': data, 'global_data': global_data}
    pickle.dump(file_data, open(os.path.join(base_path,
                                             'ui-settings.pickle'), 'wb'))

def _write_net_env(data, global_data, base_path):
    """Write network-environment.yaml based on the data passed in"""
    # This is simple YAML, so instead of generating it with the yaml
    # module, we'll just write it directly as text so we control the
    # formatting.
    with open(os.path.join(base_path,
                            'network-environment.yaml'), 'w') as f:
        def write(content):
            f.write('  ' + content + '\n')
        f.write(NETENV_HEADER)
        if _net_used_all(data, 'ControlPlane')[0]:
            write("ControlPlaneSubnetCidr: '%d'" %
                  global_data['control']['mask'])
            write('ControlPlaneDefaultRoute: %s' %
                  global_data['control']['route'])
            write('EC2MetadataIp: %s' % global_data['control']['ec2'])
        external_used = _net_used_all(data, 'External')
        if external_used[0]:
            write('ExternalNetCidr: %s' % global_data['external']['cidr'])
            write('ExternalAllocationPools: [{"start": "%s", '
                  '"end": "%s"}]' % (global_data['external']['start'],
                                     global_data['external']['end']))
            write('ExternalInterfaceDefaultRoute: %s' %
                  global_data['external']['gateway'])
            if external_used[1]:
                write('ExternalNetworkVlanID: %d' %
                      global_data['external']['vlan'])
            write('NeutronExternalNetworkBridge: "%s"' %
                  global_data['external']['bridge'])
        for camel, lower in SIMILAR_NETS:
            used = _net_used_all(data, camel)
            if used[0]:
                write('%sNetCidr: %s' % (camel, global_data[lower]['cidr']))
                write('%sAllocationPools: [{"start": "%s", '
                    '"end": "%s"}]' % (camel,
                                       global_data[lower]['start'],
                                       global_data[lower]['end']))
                if used[1]:
                    write('%sNetworkVlanID: %d' % (camel,
                                                   global_data[lower]['vlan']))
        write('DnsServers: ["%s", "%s"]' % (global_data['dns1'],
                                            global_data['dns2']))
        if global_data['bond_options']:
            write('BondInterfaceOvsOptions: %s' % global_data['bond_options'])

def _write_net_iso(data, global_data, base_path,
                   filename='network-isolation.yaml', template_path='..'):
    """Write network-isolation.yaml based on the data passed in

    :param data: nic-config data
    :param global_data: common data across all networks and roles
    :param base_path: output directory
    :param filename: output filename
    :param template_path: path to root of tripleo-heat-templates
    """
    ipv6 = global_data.get('ipv6', False)
    with open(os.path.join(base_path, filename), 'w') as f:
        f.write('resource_registry:\n')
        # By default, we run redis on the internal network with net-iso.
        # Without internal enabled, this doesn't seem to work.
        def write(content):
            f.write('  ' + content + '\n')
        if _net_used_all(data, 'InternalApi')[0]:
            vip_name = 'vip'
            if ipv6:
                vip_name = 'vip_v6'
            write('# Redis')
            path = os.path.join(template_path, 'network/ports/%s.yaml' % vip_name)
            write('OS::TripleO::Network::Ports::RedisVipPort: %s'% path)
        for i in ALL_NETS[1:]:
            _write_net_iso_entry(f, i[0], data, template_path, i[1], ipv6=ipv6)
        if ipv6:
            f.write(V6_NET_ISO_PARAMS)

def _write_net_iso_entry(f, net, data, template_path, basename=None,
                         ipv6=False):
    """Write the entries for a single network to f"""
    if basename is None:
        basename = net.lower()
    # OVS and Neutron don't support ipv6 tenant networks yet.
    if ipv6 and basename != 'tenant':
        basename = basename + '_v6'

    def write(content):
        format_str = '  ' + content + '\n'
        f.write(format_str % (net, template_path, basename))

    if _net_used_all(data, net)[0]:
        f.write('  # %s\n' % net)
        write('OS::TripleO::Network::%s: '
              '%s/network/%s.yaml')
        write('OS::TripleO::Network::Ports::%sVipPort: '
              '%s/network/ports/%s.yaml')
    for _, filename, template_name in TYPE_LIST:
        if _net_used(data, net, filename)[0]:
            write('OS::TripleO::' + template_name + '::Ports::%sPort: '
                  '%s/network/ports/%s.yaml')

def _net_used_all(data, name):
    """Check whether a network is used in any nic-config file

    :returns: A tuple where the first element is whether the network is used
              at all, and the second element is whether the network is used on
              a VLAN.
    """
    return (any([_net_used(data, name, fname)[0]
                 for fname, _ in data.items()]),
            any([_net_used(data, name, fname)[1]
                 for fname, _ in data.items()])
            )

def _net_used(data, name, filename):
    """Determine whether nics are configured to use a network

    Returns whether a nic in filename is configured to use the network
    defined by name.  The return value is in the form of a tuple - the first
    element of the tuple is whether the network is used at all, the second
    whether the network is used by a VLAN.  name is the camelcase form of the
    network.
    """
    node_data = data[filename]
    for i in node_data:
        if i.get('network', '') == name:
            return True, i['type'] == 'vlan'
        for j in i['members']:
            if j.get('network', '') == name:
                return True, j['type'] == 'vlan'
    return False, False

def _process_all(d):
    if 'mtu' in d and d['mtu'] == -1:
        del d['mtu']
    for m in d.get('members', []):
        if m['type'] == 'route':
            new_route = copy.deepcopy(m)
            del new_route['name']
            del new_route['type']
            new_route.pop('members', None)
            d['routes'].append(new_route)
    if d['type'] == 'ovs_bridge' or d['type'] == 'ovs_bond':
        d['members'] = [m for m in d['members'] if m['type'] != 'route']

def _process_network_config(d, filename, auto_routes):
    """Tweak config data for top-level interfaces and bridges

    There is some data in the internal data structures of the UI that doesn't
    belong in the output files, or that needs to be adjusted/added.  This
    function is responsible for doing that.
    """
    _process_all(d)
    if d['type'] == 'interface' or d['type'] == 'ovs_bridge':
        network = d['network']
        del d['network']
        # This is nonsense unless we're in a bridge, which we can't be at
        # this level of nesting.
        d.pop('primary', None)
        if d['type'] == 'interface':
            d.pop('members', None)
            d.pop('port_name', None)
        # TODO: Format this less horribly
        if network == 'ControlPlane':
            d['addresses'] = [
                {'ip_netmask':
                        {'list_join': ['/', ['{get_param: ControlPlaneIp}',
                                            '{get_param: ControlPlaneSubnetCidr}'
                                            ]]}}]
            d['routes'].append({'ip_netmask': '169.254.169.254/32',
                                'next_hop': '{get_param: EC2MetadataIp}'})
            # HACK!  Typically non-controller nodes will need this, but
            # it's not a safe assumption.  It's also not necessarily true
            # that controller nodes don't need it.
            if filename != 'controller.yaml' and auto_routes:
                d['routes'].append({'default': True,
                                    'next_hop': '{get_param: ControlPlaneDefaultRoute}'})
        elif network == 'External':
            d['addresses'] = [{'ip_netmask':
                                    '{get_param: ExternalIpSubnet}'}]
            if auto_routes:
                d['routes'].append(
                    {'ip_netmask': '0.0.0.0/0',
                        'next_hop':
                            '{get_param: ExternalInterfaceDefaultRoute}'})
        elif network == 'None':
            d.pop('addresses', None)
        else:
            d['addresses'] = [{'ip_netmask':
                                   '{get_param: %sIpSubnet}' % network}]
        if d['type'] == 'ovs_bridge':
            br_type = d.pop('bridge_type', 'ovs')
            d['type'] = '%s_bridge' % br_type
    if 'routes' in d and not d['routes']:
        del d['routes']

def _find_bond(siblings):
    bonds = [b for b in siblings if b['type'].endswith('_bond')]
    if len(bonds) > 1:
        raise RuntimeError('Multiple bonds found on one bridge')
    try:
        return bonds[0]
    except IndexError:
        return

def _process_dpdk_interface(nd):
    """Convert DPDK interface data

    DPDK ports are treated as interfaces, but they actually need to be a
    separate object which contains an interface.  This function handles
    that conversion.
    """
    if nd['type'] != 'interface':
        return
    if nd.get('interface_type', 'interface') == 'ovs_dpdk_port':
        nd['type'] = nd.pop('interface_type')
        nd['members'] = [{'type': 'interface', 'name': nd['name']}]
        nd['name'] = nd.pop('port_name')
    else:
        nd.pop('port_name', None)

def _process_bridge_members(nd, siblings):
    """The same as _process_network_config, except for bridge members

    Also takes a siblings parameter that allows VLAN items to be
    automatically associated with the appropriate device."""
    _process_all(nd)
    if nd['type'] == 'vlan':
        network = nd['network']
        del nd['network']
        del nd['members']
        nd.pop('name', None)
        bond = _find_bond(siblings)
        if bond is not None:
            nd['device'] = bond['name']
        if network == 'External':
            # This shares some logic with _process_network_config. Refactor?
            nd['addresses'] = [{'ip_netmask':
                                    '{get_param: ExternalIpSubnet}'}]
            nd['routes'].append(
                {'ip_netmask': '0.0.0.0/0',
                    'next_hop':
                        '{get_param: ExternalInterfaceDefaultRoute}'})
            nd['vlan_id'] = '{get_param: ExternalNetworkVlanID}'
        elif network == 'None':
            raise RuntimeError('VLANs must have a network set')
        else:
            vlan_id = '{get_param: %sNetworkVlanID}' % network
            nd['vlan_id'] = vlan_id
            netmask = '{get_param: %sIpSubnet}' % network
            nd['addresses'] = [{'ip_netmask': netmask}]
            if not nd.get('routes'):
                nd.pop('routes', None)

    elif nd['type'] == 'interface':
        nd.pop('network', None)
        nd.pop('addresses', None)
        nd.pop('routes', None)
        nd.pop('use_dhcp', None)
        nd.pop('members', None)
    elif nd['type'] == 'ovs_bond':
        if nd.get('bond_type', 'ovs') == 'linux':
            nd['type'] = 'linux_bond'
            nd['bonding_options'] = nd['ovs_options']
            del nd['ovs_options']
        elif nd.get('bond_type', 'ovs') == 'team':
            nd['type'] = 'team'
            nd['bonding_options'] = nd['ovs_options']
            del nd['ovs_options']
        elif nd.get('bond_type', 'ovs') == 'ovs_dpdk':
            nd['type'] = 'ovs_dpdk_bond'
            del nd['ovs_options']
        nd.pop('bond_type', None)
        nd.pop('network', None)
        if len(nd['members']) < 2:
            raise RuntimeError('Bonds must contain at least two interfaces')
    _process_dpdk_interface(nd)
    if 'routes' in nd and not nd['routes']:
        del nd['routes']

def _process_bond_members(nd):
    _process_all(nd)
    if nd['type'] == 'interface':
        nd.pop('addresses', None)
        nd.pop('network', None)
        nd.pop('use_dhcp', None)
        nd.pop('routes', None)
    _process_dpdk_interface(nd)

def _validate_config(data, global_data):
    _check_duplicate_vlans(data, global_data)
    _check_duplicate_networks(data)
    _check_duplicate_bonds(data)
    _check_duplicate_nics(data)
    _check_overlapping_cidrs(data, global_data)
    _check_ips_in_cidr(data, global_data)
    _check_primary_interfaces(data)
    _check_bridge_members(data)

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
            used = _net_used_all(data, _lower_to_camel(name))[0]
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
            if 'network' not in i:
                continue
            if i['network'] in seen and i['network'] != 'None':
                raise RuntimeError(err_msg % (i['network'], filename))
            for j in i['members']:
                if 'network' not in j:
                    continue
                if j['network'] in seen and j['network'] != 'None':
                    raise RuntimeError(err_msg % (j['network'], filename))
                seen.add(j['network'])
            seen.add(i['network'])

def _check_duplicate_bonds(data):
    for filename, d in data.items():
        seen = set()
        for i in d:
            if i['type'] != 'ovs_bridge':
                continue
            for j in i['members']:
                if j['type'] != 'ovs_bond':
                    continue
                if j['name'] in seen:
                    raise RuntimeError('Duplicate bond name "%s" found in '
                                       '"%s"' %
                                       (j['name'], filename))
                seen.add(j['name'])

def _check_duplicate_nics(data):
    for filename, d in data.items():
        seen = set()
        def process_interfaces(d):
            for i in d:
                if i['type'] == 'interface':
                    name = i['name']
                    if name in seen:
                        raise RuntimeError('Duplicate nic name: "%s"' % name)
                    seen.add(name)
                if 'members' in i:
                    process_interfaces(i['members'])
        process_interfaces(d)

def _check_overlapping_cidrs(data, global_data):
    cidrs = []
    for name, d in global_data.items():
        try:
            cidr = d['cidr']
        except (KeyError, TypeError):
            continue
        camel = _lower_to_camel(name)
        if _net_used_all(data, camel)[0]:
            new_cidr = netaddr.IPNetwork(cidr)
            if new_cidr in cidrs:
                raise RuntimeError('Duplicate CIDR found: "%s"' % new_cidr)
            cidrs.append(new_cidr)
    for x, y in itertools.product(cidrs, cidrs):
        if x == y:
            # We checked for duplicate CIDRs above, and don't want to check a
            # CIDR against itself.
            continue
        if x in y or y in x:
            raise RuntimeError('Overlapping CIDRs detected: "%s" and "%s"' %
                               (x, y))

def _validate_addr_in_cidr(ip, cidr, name):
        if netaddr.IPAddress(ip) not in netaddr.IPNetwork(cidr):
            raise RuntimeError('%s "%s" not in CIDR "%s"' % (name, ip, cidr))

def _check_ips_in_cidr(data, global_data):
    for name, d in global_data.items():
        try:
            cidr = d['cidr']
        except (KeyError, TypeError):
            continue
        camel = _lower_to_camel(name)
        if _net_used_all(data, camel)[0]:
            _validate_addr_in_cidr(d['start'], cidr, '%s start' % camel)
            _validate_addr_in_cidr(d['end'], cidr, '%s end' % camel)
            if 'gateway' in d:
                _validate_addr_in_cidr(d['gateway'], cidr,
                                       '%s gateway' % camel)

def _check_primary_interfaces(data):
    """Validate that there is exactly one primary interface on a bond"""
    multi_err = 'Found multiple primary interfaces on bond "%s"'
    missing_err = 'Found no primary interface on bond "%s"'
    def process_bond(m):
        have_primary = False
        for i in m['members']:
            if i['type'] == 'interface':
                if i['primary']:
                    if have_primary:
                        raise RuntimeError(multi_err % m['name'])
                    have_primary = True
        if not have_primary:
            raise RuntimeError(missing_err % m['name'])

    for filename, d in data.items():
        for item in d:
            if item['type'] == 'ovs_bridge':
                for m in item['members']:
                    if m['type'] == 'ovs_bond':
                        process_bond(m)

def _check_bridge_members(data):
    """Validate that there is exactly one bond/interface per bridge"""
    multi_err = 'Found multiple bonds/interfaces on bridge "%s"'
    missing_err = 'Found no interface or bond on bridge "%s"'
    for filename, d in data.items():
        for item in d:
            if item['type'] == 'ovs_bridge':
                have_one = False
                for m in item['members']:
                    if m['type'] == 'interface' or m['type'] == 'ovs_bond':
                        if have_one:
                            raise RuntimeError(multi_err % item['name'])
                        have_one = True
                if not have_one:
                    raise RuntimeError(missing_err % item['name'])


def _load(base_path):
    file_data = pickle.load(open(os.path.join(base_path,
                                              'ui-settings.pickle'), 'rb'))
    nic_data = file_data['data']
    global_data = file_data['global_data']
    return nic_data, global_data

def _index_from_filename(filename):
    return [i[0] for i in TYPE_LIST if i[1] == filename][0]
