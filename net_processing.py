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

TYPE_LIST = [(0, 'controller.yaml', 'Controller'),
             (1, 'compute.yaml', 'Compute'),
             (2, 'ceph-storage.yaml', 'CephStorage'),
             (3, 'cinder-storage.yaml', 'BlockStorage'),
             (4, 'swift-storage.yaml', 'SwiftStorage')]

def _write_net_iso(f, net, data, basename=None):
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
