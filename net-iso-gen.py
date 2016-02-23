#!/usr/bin/env python
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

# Icon files come from the Oxygen project.  See LICENSE for details.

import copy
import os
import sys
import yaml

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4 import QtCore
from PyQt4 import QtGui

import net_processing


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


def get_current_item(model):
    current_index = model.currentIndex()
    return current_index.model().item(current_index.row())


class PairWidget(QtGui.QWidget):
    def __init__(self, label, widget, parent=None):
        super(PairWidget, self).__init__(parent)

        self.layout = QtGui.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = label
        try:
            self.layout.addWidget(self.label)
        except TypeError:
            self.label = QtGui.QLabel(label)
            self.layout.addWidget(self.label)

        self.widget = widget
        self.layout.addWidget(self.widget)


class NetworkListView(QtGui.QListView):
    focused = QtCore.pyqtSignal()
    current_changed = QtCore.pyqtSignal(QtCore.QModelIndex)
    def __init__(self, parent=None):
        super(NetworkListView, self).__init__(parent)

    def focusInEvent(self, event):
        self.focused.emit()

    def currentChanged(self, current, old):
        self.current_changed.emit(current)

class NetworkListWidget(QtGui.QListWidget):
    focused = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(NetworkListWidget, self).__init__(parent)

    def focusInEvent(self, event):
        self.focused.emit()


class MainForm(QtGui.QMainWindow):
    def __init__(self):
        super(MainForm, self).__init__()

        # TODO(bnemec): Need to delete any created models before exiting.
        # Otherwise the garbage collection doesn't always happen in the right
        # order and we get some timer errors at close.
        self._node_models = {}
        self._interface_models = {}
        self._last_selected = None

        self._setup_ui()
        self.show()

    def _setup_ui(self):
        self.resize(1280, 650)
        self.setWindowTitle('Network Isolation Template Generator')

        self.setCentralWidget(QtGui.QWidget())
        main_layout = QtGui.QVBoxLayout()
        self.centralWidget().setLayout(main_layout)

        button_layout = QtGui.QHBoxLayout()
        add_interface = QtGui.QPushButton('Add Interface')
        add_interface.clicked.connect(self._add_interface)
        button_layout.addWidget(add_interface)
        add_bridge = QtGui.QPushButton('Add Bridge')
        add_bridge.clicked.connect(self._add_bridge)
        button_layout.addWidget(add_bridge)
        add_vlan = QtGui.QPushButton('Add VLAN')
        add_vlan.clicked.connect(self._add_vlan)
        button_layout.addWidget(add_vlan)
        delete = QtGui.QPushButton('Delete')
        delete.clicked.connect(self._delete_current)
        button_layout.addWidget(delete)
        main_layout.addLayout(button_layout)

        pane_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(pane_layout)

        self.node_type = NetworkListWidget()
        def new_item(name):
            item = QtGui.QListWidgetItem(QtGui.QIcon('network-server.svgz'), name)
            self.node_type.addItem(item)
            self._node_models[item] = QtGui.QStandardItemModel(0, 1)
        new_item('Controller')
        new_item('Compute')
        new_item('Ceph')
        new_item('Block Storage')
        new_item('Swift')
        self.node_type.setIconSize(QtCore.QSize(64, 64))
        self.node_type.currentRowChanged.connect(self._node_type_changed)
        self.node_type.focused.connect(self._node_type_focused)
        pane_layout.addWidget(self.node_type, 100)

        self.interfaces = NetworkListView()
        self.interfaces.setIconSize(QtCore.QSize(64, 64))
        # Can't do this before self.interfaces exists
        self.node_type.setCurrentRow(0)
        self.interfaces.current_changed.connect(self._interface_changed)
        self.interfaces.focused.connect(self._interface_focused)
        pane_layout.addWidget(self.interfaces, 100)

        self.nested_interfaces = NetworkListView()
        self.nested_interfaces.setIconSize(QtCore.QSize(64, 64))
        self.nested_interfaces.current_changed.connect(self._nested_changed)
        self.nested_interfaces.focused.connect(self._nested_focused)
        pane_layout.addWidget(self.nested_interfaces, 100)

        input_layout = QtGui.QVBoxLayout()
        pane_layout.addLayout(input_layout, 100)

        self.item_name = QtGui.QLineEdit()
        self.item_name.textEdited.connect(self._name_changed)
        input_layout.addWidget(PairWidget('Name', self.item_name))

        self.network_type = QtGui.QComboBox()
        self.network_type.addItem('None')
        self.network_type.addItem('ControlPlane')
        self.network_type.addItem('External')
        self.network_type.addItem('InternalApi')
        self.network_type.addItem('Storage')
        self.network_type.addItem('StorageMgmt')
        self.network_type.addItem('Tenant')
        self.network_type.addItem('Management')
        self.network_type.currentIndexChanged.connect(self._network_type_changed)
        input_layout.addWidget(PairWidget('Network', self.network_type))

        self.primary = QtGui.QCheckBox()
        self.primary.stateChanged.connect(self._primary_changed)
        input_layout.addWidget(PairWidget('Primary', self.primary))

        input_layout.addStretch()

        params_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(params_layout)

        # Control Plane
        self.control_group = QtGui.QGroupBox('Control Plane')
        control_layout = QtGui.QVBoxLayout()
        self.control_group.setLayout(control_layout)
        params_layout.addWidget(self.control_group)

        self.control_mask = QtGui.QSpinBox()
        self.control_mask.setMinimum(8)
        self.control_mask.setMaximum(31)
        self.control_mask.setValue(24)
        control_layout.addWidget(PairWidget('Mask Length',
                                            self.control_mask))

        self.control_route = QtGui.QLineEdit()
        self.control_route.setText('192.0.2.1')
        control_layout.addWidget(PairWidget('Gateway',
                                            self.control_route))

        self.control_ec2 = QtGui.QLineEdit()
        self.control_ec2.setText('192.0.2.1')
        control_layout.addWidget(PairWidget('EC2 Metadata',
                                            self.control_ec2))

        # External
        self.external_group = QtGui.QGroupBox('External')
        external_layout = QtGui.QVBoxLayout()
        self.external_group.setLayout(external_layout)
        params_layout.addWidget(self.external_group)

        self.external_cidr = QtGui.QLineEdit()
        self.external_cidr.setText('10.0.0.0/24')
        external_layout.addWidget(PairWidget('CIDR', self.external_cidr))

        self.external_start = QtGui.QLineEdit()
        self.external_start.setText('10.0.0.10')
        external_layout.addWidget(PairWidget('IP Start',
                                             self.external_start))

        self.external_end = QtGui.QLineEdit()
        self.external_end.setText('10.0.0.50')
        external_layout.addWidget(PairWidget('IP End',
                                             self.external_end))

        self.external_gateway = QtGui.QLineEdit()
        self.external_gateway.setText('10.0.0.1')
        external_layout.addWidget(PairWidget('Default Gateway',
                                             self.external_gateway))

        self.external_vlan = QtGui.QSpinBox()
        self.external_vlan.setMinimum(1)
        self.external_vlan.setMaximum(4096)
        external_layout.addWidget(PairWidget('VLAN ID', self.external_vlan))

        self.external_bridge = QtGui.QLineEdit()
        self.external_bridge.setText("''")
        external_layout.addWidget(PairWidget('Neutron Bridge',
                                             self.external_bridge))

        # Internal API
        self.internal_group = QtGui.QGroupBox('Internal API')
        internal_layout = QtGui.QVBoxLayout()
        self.internal_group.setLayout(internal_layout)
        params_layout.addWidget(self.internal_group)

        self.internal_cidr = QtGui.QLineEdit()
        self.internal_cidr.setText('172.17.0.0/24')
        internal_layout.addWidget(PairWidget('CIDR', self.internal_cidr))

        self.internal_start = QtGui.QLineEdit()
        self.internal_start.setText('172.17.0.10')
        internal_layout.addWidget(PairWidget('IP Start',
                                             self.internal_start))

        self.internal_end = QtGui.QLineEdit()
        self.internal_end.setText('172.17.0.250')
        internal_layout.addWidget(PairWidget('IP End',
                                             self.internal_end))

        self.internal_vlan = QtGui.QSpinBox()
        self.internal_vlan.setMinimum(1)
        self.internal_vlan.setMaximum(4096)
        self.internal_vlan.setValue(2)
        internal_layout.addWidget(PairWidget('VLAN ID', self.internal_vlan))

        # Storage
        self.storage_group = QtGui.QGroupBox('Storage')
        storage_layout = QtGui.QVBoxLayout()
        self.storage_group.setLayout(storage_layout)
        params_layout.addWidget(self.storage_group)

        self.storage_cidr = QtGui.QLineEdit()
        self.storage_cidr.setText('172.18.0.0/24')
        storage_layout.addWidget(PairWidget('CIDR', self.storage_cidr))

        self.storage_start = QtGui.QLineEdit()
        self.storage_start.setText('172.18.0.10')
        storage_layout.addWidget(PairWidget('IP Start',
                                             self.storage_start))

        self.storage_end = QtGui.QLineEdit()
        self.storage_end.setText('172.18.0.250')
        storage_layout.addWidget(PairWidget('IP End',
                                             self.storage_end))

        self.storage_vlan = QtGui.QSpinBox()
        self.storage_vlan.setMinimum(1)
        self.storage_vlan.setMaximum(4096)
        self.storage_vlan.setValue(3)
        storage_layout.addWidget(PairWidget('VLAN ID', self.storage_vlan))

        # Storage Mgmt
        self.storage_mgmt_group = QtGui.QGroupBox('Storage Mgmt')
        storage_mgmt_layout = QtGui.QVBoxLayout()
        self.storage_mgmt_group.setLayout(storage_mgmt_layout)
        params_layout.addWidget(self.storage_mgmt_group)

        self.storage_mgmt_cidr = QtGui.QLineEdit()
        self.storage_mgmt_cidr.setText('172.19.0.0/24')
        storage_mgmt_layout.addWidget(PairWidget('CIDR', self.storage_mgmt_cidr))

        self.storage_mgmt_start = QtGui.QLineEdit()
        self.storage_mgmt_start.setText('172.19.0.10')
        storage_mgmt_layout.addWidget(PairWidget('IP Start',
                                             self.storage_mgmt_start))

        self.storage_mgmt_end = QtGui.QLineEdit()
        self.storage_mgmt_end.setText('172.19.0.250')
        storage_mgmt_layout.addWidget(PairWidget('IP End',
                                             self.storage_mgmt_end))

        self.storage_mgmt_vlan = QtGui.QSpinBox()
        self.storage_mgmt_vlan.setMinimum(1)
        self.storage_mgmt_vlan.setMaximum(4096)
        self.storage_mgmt_vlan.setValue(4)
        storage_mgmt_layout.addWidget(PairWidget('VLAN ID', self.storage_mgmt_vlan))

        # Tenant
        self.tenant_group = QtGui.QGroupBox('Tenant')
        tenant_layout = QtGui.QVBoxLayout()
        self.tenant_group.setLayout(tenant_layout)
        params_layout.addWidget(self.tenant_group)

        self.tenant_cidr = QtGui.QLineEdit()
        self.tenant_cidr.setText('172.16.0.0/24')
        tenant_layout.addWidget(PairWidget('CIDR', self.tenant_cidr))

        self.tenant_start = QtGui.QLineEdit()
        self.tenant_start.setText('172.16.0.10')
        tenant_layout.addWidget(PairWidget('IP Start',
                                             self.tenant_start))

        self.tenant_end = QtGui.QLineEdit()
        self.tenant_end.setText('172.16.0.250')
        tenant_layout.addWidget(PairWidget('IP End',
                                             self.tenant_end))

        self.tenant_vlan = QtGui.QSpinBox()
        self.tenant_vlan.setMinimum(1)
        self.tenant_vlan.setMaximum(4096)
        self.tenant_vlan.setValue(5)
        tenant_layout.addWidget(PairWidget('VLAN ID', self.tenant_vlan))

        # Management
        self.management_group = QtGui.QGroupBox('Management')
        management_layout = QtGui.QVBoxLayout()
        self.management_group.setLayout(management_layout)
        params_layout.addWidget(self.management_group)

        self.management_cidr = QtGui.QLineEdit()
        self.management_cidr.setText('172.20.0.0/24')
        management_layout.addWidget(PairWidget('CIDR', self.management_cidr))

        self.management_start = QtGui.QLineEdit()
        self.management_start.setText('172.20.0.10')
        management_layout.addWidget(PairWidget('IP Start',
                                             self.management_start))

        self.management_end = QtGui.QLineEdit()
        self.management_end.setText('172.20.0.250')
        management_layout.addWidget(PairWidget('IP End',
                                             self.management_end))

        self.management_vlan = QtGui.QSpinBox()
        self.management_vlan.setMinimum(1)
        self.management_vlan.setMaximum(4096)
        self.management_vlan.setValue(6)
        management_layout.addWidget(PairWidget('VLAN ID', self.management_vlan))

        generate = QtGui.QPushButton('Generate')
        generate.clicked.connect(self._generate_templates)
        main_layout.addWidget(generate)

    def _ui_to_dict(self):
        """Convert the UI data to a more readable dict

        :returns: dict representing the current UI state"""
        retval = {}
        for index, filename, _ in net_processing.TYPE_LIST:
            retval[filename] = []
            current_item = self.node_type.item(index)
            current_model = self._node_models[current_item]
            for i in range(current_model.rowCount()):
                d = copy.deepcopy(current_model.item(i).data())
                d['members'] = []
                if d['type'] == 'ovs_bridge':
                    item = current_model.item(i)
                    nested_model = self._interface_models[item]
                    for j in range(nested_model.rowCount()):
                        nd = copy.deepcopy(nested_model.item(j).data())
                        d['members'].append(nd)
                retval[filename].append(d)
        return retval

    # This whole function should probably be moved to net_processing, but it
    # has an unfortunate amount of direct usage of the UI elements right now.
    def _generate_templates(self):
        # FIXME(bnemec): Make this path configurable
        base_path = '/tmp/templates'
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

        data = self._ui_to_dict()
        for filename, node_data in data.items():
            with open(os.path.join(nic_path, filename), 'w') as f:
                f.write(PARAMS)
                resources, network_config = new_resource()
                for i in node_data:
                    net_processing._process_network_config(i, filename)
                    for j in i['members']:
                        net_processing._process_bridge_members(j)
                    network_config.append(i)
                resource_string = yaml.safe_dump(resources,
                                                 default_flow_style=False)
                # Ugly hack to remove unwanted quoting around get_params
                resource_string = resource_string.replace(
                    "'{get_param:", "{get_param:")
                resource_string = resource_string.replace("}'", "}")
                # And fix the lack of them around the /
                #resource_string = resource_string.replace("- /", "- '/'")
                f.write(resource_string)
                f.write(OUTPUTS)

        # We need a fresh, unmolested copy of the dict for the following steps
        data = self._ui_to_dict()
        # This is simple YAML, so instead of generating it with the yaml
        # module, we'll just write it directly as text so we control the
        # formatting.
        with open(os.path.join(base_path,
                               'network-environment.yaml'), 'w') as f:
            def write(content):
                f.write('  ' + content + '\n')
            f.write(NETENV_HEADER)
            if net_processing._net_used_all(data, 'ControlPlane'):
                write("ControlPlaneSubnetCidr: '%d'" %
                      self.control_mask.value())
                write('ControlPlaneDefaultRoute: %s' %
                      self.control_route.text())
                write('EC2MetadataIp: %s' % self.control_ec2.text())
            if net_processing._net_used_all(data, 'External'):
                write('ExternalNetCidr: %s' % self.external_cidr.text())
                write('ExternalAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.external_start.text(),
                                         self.external_end.text()))
                write('ExternalInterfaceDefaultRoute: %s' %
                      self.external_gateway.text())
                write('ExternalNetworkVlanID: %d' % self.external_vlan.value())
                write('NeutronExternalNetworkBridge: "%s"' %
                      self.external_bridge.text())
            if net_processing._net_used_all(data, 'InternalApi'):
                write('InternalApiNetCidr: %s' % self.internal_cidr.text())
                write('InternalApiAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.internal_start.text(),
                                         self.internal_end.text()))
                write('InternalApiNetworkVlanID: %d' % self.internal_vlan.value())
            if net_processing._net_used_all(data, 'Storage'):
                write('StorageNetCidr: %s' % self.storage_cidr.text())
                write('StorageAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.storage_start.text(),
                                         self.storage_end.text()))
                write('StorageNetworkVlanID: %d' % self.storage_mgmt_vlan.value())
            if net_processing._net_used_all(data, 'StorageMgmt'):
                write('StorageMgmtNetCidr: %s' % self.storage_mgmt_cidr.text())
                write('StorageMgmtAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.storage_mgmt_start.text(),
                                         self.storage_mgmt_end.text()))
                write('StorageMgmtNetworkVlanID: %d' % self.storage_mgmt_vlan.value())
            if net_processing._net_used_all(data, 'Tenant'):
                write('TenantNetCidr: %s' % self.tenant_cidr.text())
                write('TenantAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.tenant_start.text(),
                                         self.tenant_end.text()))
                write('TenantNetworkVlanID: %d' % self.tenant_vlan.value())
            if net_processing._net_used_all(data, 'Management'):
                write('ManagementNetCidr: %s' % self.management_cidr.text())
                write('ManagementAllocationPools: [{"start": "%s", '
                      '"end": "%s"}]' % (self.management_start.text(),
                                         self.management_end.text()))
                write('ManagementNetworkVlanID: %d' % self.management_vlan.value())

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
            net_processing._write_net_iso(f, 'External', data)
            net_processing._write_net_iso(f, 'InternalApi', data, 'internal_api')
            net_processing._write_net_iso(f, 'Storage', data)
            net_processing._write_net_iso(f, 'StorageMgmt', data, 'storage_mgmt')
            net_processing._write_net_iso(f, 'Tenant', data)
            net_processing._write_net_iso(f, 'Management', data)

    def _node_type_changed(self, index):
        self.interfaces.setModel(
            self._node_models[self.node_type.currentItem()])
        self.nested_interfaces.setModel(QtGui.QStandardItemModel(0, 1))

    def _node_type_focused(self):
        self._last_selected = self.node_type

    def _interface_changed(self, index):
        row = index.row()
        if row >= 0:
            item = index.model().item(row)
            self.nested_interfaces.setModel(self._interface_models[item])
            self._update_input(item)
        else:
            self.nested_interfaces.setModel(QtGui.QStandardItemModel(0, 1))

    def _interface_focused(self):
        self._last_selected = self.interfaces
        self._interface_changed(self.interfaces.currentIndex())

    def _nested_changed(self, index):
        row = index.row()
        if row >= 0:
            item = index.model().item(row)
            self._update_input(item)

    def _nested_focused(self):
        self._last_selected = self.nested_interfaces
        self._nested_changed(self.nested_interfaces.currentIndex())

    def _next_nic_name(self):
        current_item = self.node_type.currentItem()
        current_model = self._node_models[current_item]
        next_nic_num = 1

        def calculate_from_data(d, next_nic_num):
            if d['type'] == 'interface':
                if d['name'].startswith('nic'):
                    nic_num = int(d['name'][3:])
                    next_nic_num = max(next_nic_num, nic_num + 1)
            return next_nic_num

        for i in range(current_model.rowCount()):
            d = current_model.item(i).data()
            if d['type'] == 'interface':
                next_nic_num = calculate_from_data(d, next_nic_num)
            elif d['type'] == 'ovs_bridge':
                item = current_model.item(i)
                nested = self._interface_models[item]
                for j in range(nested.rowCount()):
                    nd = nested.item(j).data()
                    next_nic_num = calculate_from_data(nd, next_nic_num)
        nic_name = 'nic%d' % next_nic_num
        return nic_name

    def _new_nic_item(self, nic_name):
        item = QtGui.QStandardItem(QtGui.QIcon('network-wired.png'),
                                   nic_name)
        item.setData({'type': 'interface',
                      'name': nic_name,
                      'use_dhcp': False,
                      'addresses': [],
                      'routes': [],
                      'network': 'ControlPlane',
                      'primary': True,
                      })
        return item

    def _add_interface(self):
        if self._last_selected is self.node_type:
            current_item = self.node_type.currentItem()
            current_model = self._node_models[current_item]
            nic_name = self._next_nic_name()
            item = self._new_nic_item(nic_name)
            self._interface_models[item] = QtGui.QStandardItemModel(0, 1)
            current_model.appendRow(item)
        elif self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            current_model = self._interface_models[current_item]
            nic_name = self._next_nic_name()
            item = self._new_nic_item(nic_name)
            current_model.appendRow(item)
        else:
            raise RuntimeError('Can only add interfaces to top-level nodes '
                               'and bridges.')

    def _add_bridge(self):
        if self._last_selected is self.node_type:
            current_item = self.node_type.currentItem()
            current_model = self._node_models[current_item]
            bridge_name = 'br-ex'
            item = QtGui.QStandardItem(QtGui.QIcon('bridge.svgz'), bridge_name)
            item.setData({'type': 'ovs_bridge',
                          'name': bridge_name,
                          'use_dhcp': False,
                          'dns_servers': '{get_param: DnsServers}',
                          'addresses': [],
                          'routes': [],
                          'members': [],
                          'network': 'None',
                          })
            self._interface_models[item] = QtGui.QStandardItemModel(0, 1)
            current_model.appendRow(item)
        else:
            raise RuntimeError('Can only add bridges to top-level nodes')

    def _add_vlan(self):
        if self._last_selected is self.node_type:
            # This is probably needed for linux bridges
            pass
        elif self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            current_model = self._interface_models[current_item]
            item = QtGui.QStandardItem(QtGui.QIcon('network-workgroup.svgz'),
                                       'VLAN')
            item.setData({'type': 'vlan',
                          'vlan_id': '',
                          'addresses': [],
                          'routes': [],
                          'network': 'External',
                          'name': 'VLAN',
                          })
            self._interface_models[item] = QtGui.QStandardItemModel(0, 1)
            current_model.appendRow(item)
        else:
            raise RuntimeError('Can only add VLANs to top-level nodes and '
                               'bridges')

    def _delete_current(self):
        if self._last_selected is self.node_type:
            raise RuntimeError('Cannot delete top-level node type')
        elif self._last_selected is self.interfaces:
            current_index = self.interfaces.currentIndex()
            current_index.model().takeRow(current_index.row())
        elif self._last_selected is self.nested_interfaces:
            current_index = self.nested_interfaces.currentIndex()
            current_index.model().takeRow(current_index.row())

    def _update_input(self, item):
        d = item.data()
        self.network_type.setCurrentIndex(
            self.network_type.findText(d['network']))
        if 'primary' in d:
            self.primary.setDisabled(False)
            self.primary.setChecked(d['primary'])
        else:
            self.primary.setDisabled(True)
        self.item_name.setText(d['name'])

    def _network_type_changed(self, index):
        new_name = self.network_type.currentText()
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        else:
            raise RuntimeError('Cannot change network type of nodes')
        d = current_item.data()
        d['network'] = new_name
        current_item.setData(d)

    def _primary_changed(self, state):
        if self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
            d = current_item.data()
            d['primary'] = self.primary.isChecked()
            current_item.setData(d)
        else:
            # This should be a RuntimeError, but right now we don't
            # differentiate properly between when this changes due to user
            # input and when it's changed programmatically, which causes
            # this error to be raised incorrectly.
            pass
            #raise RuntimeError('Cannot set primary on top-level interfaces')

    def _name_changed(self, text):
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        else:
            raise RuntimeError('Cannot change name of node types')
        current_item.setText(text)
        d = current_item.data()
        d['name'] = self.item_name.text()
        current_item.setData(d)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    form = MainForm()

    sys.exit(app.exec_())