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


DATA_MAJOR = 1
DATA_MINOR = 2


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
        try:
            for w in widget:
                self.layout.addWidget(w)
                self.label.setToolTip(w.toolTip())
        except TypeError:
            self.layout.addWidget(widget)
            self.label.setToolTip(widget.toolTip())


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
        self._nested_models = {}
        self._last_selected = None

        self._setup_ui()
        if len(sys.argv) > 1:
            self._load_templates(sys.argv[1])
        self._update_enabled_networks()
        self.show()

    def _setup_ui(self):
        self.resize(1280, 700)
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
        add_bond = QtGui.QPushButton('Add Bond')
        add_bond.clicked.connect(self._add_bond)
        button_layout.addWidget(add_bond)
        add_route = QtGui.QPushButton('Add Route')
        add_route.clicked.connect(self._add_route)
        button_layout.addWidget(add_route)
        delete = QtGui.QPushButton('Delete')
        delete.clicked.connect(self._delete_current)
        button_layout.addWidget(delete)
        main_layout.addLayout(button_layout)

        pane_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(pane_layout)

        self.node_type = NetworkListWidget()
        def new_item(name):
            item = QtGui.QListWidgetItem(
                QtGui.QIcon(os.path.join('icons', 'network-server.png')), name)
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
        self.interfaces.current_changed.connect(self._interface_changed)
        self.interfaces.focused.connect(self._interface_focused)
        pane_layout.addWidget(self.interfaces, 100)

        self.nested_interfaces = NetworkListView()
        self.nested_interfaces.setIconSize(QtCore.QSize(64, 64))
        self.nested_interfaces.current_changed.connect(self._nested_changed)
        self.nested_interfaces.focused.connect(self._nested_focused)
        pane_layout.addWidget(self.nested_interfaces, 100)

        self.leaf_interfaces = NetworkListView()
        self.leaf_interfaces.setIconSize(QtCore.QSize(64, 64))
        self.leaf_interfaces.current_changed.connect(self._leaf_changed)
        self.leaf_interfaces.focused.connect(self._leaf_focused)
        pane_layout.addWidget(self.leaf_interfaces, 100)

        # Can't do this before self.nested_interfaces exists
        self.node_type.setCurrentRow(0)
        self._last_selected = self.node_type

        input_layout = QtGui.QVBoxLayout()
        pane_layout.addLayout(input_layout, 100)

        self.item_name = QtGui.QLineEdit()
        self.item_name.textEdited.connect(self._name_changed)
        input_layout.addWidget(PairWidget('Name', self.item_name))

        self.network_group = QtGui.QGroupBox('Network Options')
        network_layout = QtGui.QVBoxLayout()
        self.network_group.setLayout(network_layout)
        self.network_group.setVisible(False)
        input_layout.addWidget(self.network_group)
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
        network_layout.addWidget(PairWidget('Network', self.network_type))

        self.mtu = QtGui.QSpinBox()
        self.mtu.setMinimum(-1)
        self.mtu.setMaximum(65535)
        self.mtu.setToolTip('A value of -1 will cause the default MTU to be '
                            'used')
        self.mtu.valueChanged.connect(self._mtu_changed)
        network_layout.addWidget(PairWidget('MTU', self.mtu))

        self.interface_group = QtGui.QGroupBox('Interface Options')
        interface_layout = QtGui.QVBoxLayout()
        self.interface_group.setLayout(interface_layout)
        self.interface_group.setVisible(False)
        input_layout.addWidget(self.interface_group)
        self.primary = QtGui.QCheckBox()
        self.primary.stateChanged.connect(self._primary_changed)
        interface_layout.addWidget(PairWidget('Primary', self.primary))

        self.route_group = QtGui.QGroupBox('Route Options')
        route_layout = QtGui.QVBoxLayout()
        self.route_group.setLayout(route_layout)
        self.route_group.setVisible(False)
        input_layout.addWidget(self.route_group)
        self.route_netmask = QtGui.QLineEdit()
        self.route_netmask.textEdited.connect(self._route_changed)
        route_layout.addWidget(PairWidget('CIDR', self.route_netmask))
        self.route_next_hop = QtGui.QLineEdit()
        self.route_next_hop.textEdited.connect(self._route_changed)
        route_layout.addWidget(PairWidget('Next Hop', self.route_next_hop))
        self.route_default = QtGui.QCheckBox()
        self.route_default.stateChanged.connect(self._route_changed)
        route_layout.addWidget(PairWidget('Default', self.route_default))

        self.bond_group = QtGui.QGroupBox('Bond Options')
        bond_layout = QtGui.QVBoxLayout()
        self.bond_group.setLayout(bond_layout)
        self.bond_group.setVisible(False)
        input_layout.addWidget(self.bond_group)
        self.bond_type = QtGui.QComboBox()
        self.bond_type.addItem('OVS')
        self.bond_type.addItem('Linux')
        self.bond_type.addItem('Team')
        self.bond_type.currentIndexChanged.connect(self._bond_changed)
        bond_layout.addWidget(PairWidget('Bond Type', self.bond_type))

        self.bridge_group = QtGui.QGroupBox('Bridge Options')
        bridge_layout = QtGui.QVBoxLayout()
        self.bridge_group.setLayout(bridge_layout)
        self.bridge_group.setVisible(False)
        input_layout.addWidget(self.bridge_group)
        self.bridge_type = QtGui.QComboBox()
        self.bridge_type.addItem('OVS')
        self.bridge_type.addItem('OVS User')
        self.bridge_type.currentIndexChanged.connect(self._bridge_changed)
        bridge_layout.addWidget(PairWidget('Bridge Type', self.bridge_type))

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

        self.internal_api_cidr = QtGui.QLineEdit()
        self.internal_api_cidr.setText('172.17.0.0/24')
        internal_layout.addWidget(PairWidget('CIDR', self.internal_api_cidr))

        self.internal_api_start = QtGui.QLineEdit()
        self.internal_api_start.setText('172.17.0.10')
        internal_layout.addWidget(PairWidget('IP Start',
                                             self.internal_api_start))

        self.internal_api_end = QtGui.QLineEdit()
        self.internal_api_end.setText('172.17.0.250')
        internal_layout.addWidget(PairWidget('IP End',
                                             self.internal_api_end))

        self.internal_api_vlan = QtGui.QSpinBox()
        self.internal_api_vlan.setMinimum(1)
        self.internal_api_vlan.setMaximum(4096)
        self.internal_api_vlan.setValue(2)
        internal_layout.addWidget(PairWidget('VLAN ID',
                                             self.internal_api_vlan))

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

        # General options
        general_group = QtGui.QGroupBox('General Options')
        general_layout = QtGui.QHBoxLayout()
        general_group.setLayout(general_layout)
        main_layout.addWidget(general_group)

        self.dns1 = QtGui.QLineEdit('8.8.8.8')
        self.dns2 = QtGui.QLineEdit('8.8.4.4')
        general_layout.addWidget(PairWidget('DNS Servers', [self.dns1,
                                                            self.dns2]))

        self.bond_options = QtGui.QLineEdit()
        general_layout.addWidget(PairWidget('Bond Options', self.bond_options))

        self.auto_routes = QtGui.QCheckBox()
        self.auto_routes.setChecked(True)
        self.auto_routes.setToolTip('Include standard default routes automatically. '
                                    'When unchecked, default routes will need to be '
                                    'configured manually for each node type.')
        general_layout.addWidget(PairWidget('Automatic Default Routes', self.auto_routes))

        self.ipv6 = QtGui.QCheckBox()
        self.ipv6.setToolTip('Configure networks to use IPv6 when possible.')
        general_layout.addWidget(PairWidget('IPv6', self.ipv6))

        generate_layout = QtGui.QHBoxLayout()
        self.base_path = QtGui.QLineEdit('templates')
        self.base_path.setToolTip('network-[environment|isolation].yaml will '
                                  'be written to this path, and nic config '
                                  'files will be written to a nic-configs '
                                  'subdirectory at this location.')
        generate_layout.addWidget(PairWidget('Output Path', self.base_path), 5)

        set_path = QtGui.QPushButton('Set Output Path')
        set_path.clicked.connect(self._set_output_path)
        generate_layout.addWidget(set_path, 1)

        load = QtGui.QPushButton('Load Existing')
        load.clicked.connect(self._load)
        generate_layout.addWidget(load, 1)

        generate = QtGui.QPushButton('Generate')
        generate.clicked.connect(self._generate_templates)
        generate_layout.addWidget(generate, 3)
        main_layout.addLayout(generate_layout)

    def _ui_to_dict(self):
        """Convert the UI data to a more readable dict

        :returns: dict representing the current UI state
        """
        def process_leaf(model, d):
            for i in range(model.rowCount()):
                nd = copy.deepcopy(model.item(i).data())
                d['members'].append(nd)

        def process_bridge(model, d):
            for i in range(model.rowCount()):
                nd = copy.deepcopy(model.item(i).data())
                d['members'].append(nd)
                nd['members'] = []
                if nd['type'] == 'ovs_bond' or nd['type'] == 'vlan':
                    item = model.item(i)
                    nested_model = self._nested_models[item]
                    process_leaf(nested_model, nd)

        retval = {}
        for index, filename, _ in net_processing.TYPE_LIST:
            retval[filename] = []
            current_item = self.node_type.item(index)
            current_model = self._node_models[current_item]
            for i in range(current_model.rowCount()):
                d = copy.deepcopy(current_model.item(i).data())
                d['members'] = []
                item = current_model.item(i)
                nested_model = self._interface_models[item]
                process_bridge(nested_model, d)
                retval[filename].append(d)
        return retval

    def _dict_to_ui(self, data):
        """Populate the UI with values from a dict

        The dict must be structured the same as the output from _ui_to_dict.
        """
        def populate(data, current_model, next_models):
            for d in data:
                new_data = copy.deepcopy(d)
                new_data.pop('members', None)
                item = QtGui.QStandardItem()
                if d['type'] == 'interface':
                    item.setIcon(QtGui.QIcon(
                        os.path.join('icons', 'network-wired.png')))
                elif d['type'] == 'ovs_bridge':
                    item.setIcon(QtGui.QIcon(
                        os.path.join('icons', 'bridge.png')))
                elif d['type'] == 'ovs_bond':
                    item.setIcon(QtGui.QIcon(
                        os.path.join('icons', 'repository.png')))
                elif d['type'] == 'vlan':
                    item.setIcon(QtGui.QIcon(
                        os.path.join('icons', 'network-workgroup.png')))
                elif d['type'] == 'route':
                    item.setIcon(QtGui.QIcon(
                        os.path.join('icons', 'arrow-right.png')))
                item.setText(d['name'])
                item.setData(new_data)
                self._add_item(item, current_model, next_models)
                if next_models is self._interface_models:
                    populate(d['members'], next_models[item],
                             self._nested_models)
                elif next_models is self._nested_models:
                    populate(d['members'], next_models[item], None)

        self._interface_models = {}
        self._last_selected = None
        # Initialize all node models
        for i in range(self.node_type.count()):
            current_item = self.node_type.item(i)
            self._node_models[current_item] = QtGui.QStandardItemModel(0, 1)
        for filename, all_data in data.items():
            index = net_processing._index_from_filename(filename)
            current_model = self._node_models[self.node_type.item(index)]
            populate(all_data, current_model, self._interface_models)
        self._node_type_changed(None)

    def _global_to_dict(self):
        """Convert the global UI data to a dict

        :return: dict representing the current global UI state
        """
        retval = {}
        retval['major'] = DATA_MAJOR
        retval['minor'] = DATA_MINOR
        retval['control'] = {}
        retval['control']['mask'] = self.control_mask.value()
        retval['control']['route'] = self.control_route.text()
        retval['control']['ec2'] = self.control_ec2.text()
        retval['external'] = {}
        retval['external']['cidr'] = self.external_cidr.text()
        retval['external']['start'] = self.external_start.text()
        retval['external']['end'] = self.external_end.text()
        retval['external']['gateway'] = self.external_gateway.text()
        retval['external']['vlan'] = self.external_vlan.value()
        retval['external']['bridge'] = self.external_bridge.text()
        for _, net in net_processing.SIMILAR_NETS:
            retval[net] = {}
            retval[net]['cidr'] = getattr(self, '%s_cidr' % net).text()
            retval[net]['start'] = getattr(self, '%s_start' % net).text()
            retval[net]['end'] = getattr(self, '%s_end' % net).text()
            retval[net]['vlan'] = getattr(self, '%s_vlan' % net).value()
        retval['dns1'] = self.dns1.text()
        retval['dns2'] = self.dns2.text()
        retval['bond_options'] = self.bond_options.text()
        retval['auto_routes'] = self.auto_routes.isChecked()
        retval['ipv6'] = self.ipv6.isChecked()
        return retval

    def _dict_to_global(self, data):
        """Populate the UI with values from a dict

        The dict must be structured the same as the output from _global_to_dict
        """
        if data['major'] != DATA_MAJOR or data['minor'] > DATA_MINOR:
            self._error('Loaded data version %d.%d is not compatible '
                        'with current version %d.%d' %
                        (data['major'], data['minor'],
                         DATA_MAJOR, DATA_MINOR))
        self.control_mask.setValue(data['control']['mask'])
        self.control_route.setText(data['control']['route'])
        self.control_ec2.setText(data['control']['ec2'])
        self.external_cidr.setText(data['external']['cidr'])
        self.external_start.setText(data['external']['start'])
        self.external_end.setText(data['external']['end'])
        self.external_gateway.setText(data['external']['gateway'])
        self.external_vlan.setValue(data['external']['vlan'])
        self.external_bridge.setText(data['external']['bridge'])
        for _, net in net_processing.SIMILAR_NETS:
            getattr(self, '%s_cidr' % net).setText(data[net]['cidr'])
            getattr(self, '%s_start' % net).setText(data[net]['start'])
            getattr(self, '%s_end' % net).setText(data[net]['end'])
            getattr(self, '%s_vlan' % net).setValue(data[net]['vlan'])
        self.dns1.setText(data.get('dns1', ''))
        self.dns2.setText(data.get('dns2', ''))
        self.bond_options.setText(data.get('bond_options', ''))
        self.auto_routes.setChecked(data.get('auto_routes', True))
        self.ipv6.setChecked(data.get('ipv6', False))

    def _error(self, message):
        QtGui.QMessageBox.critical(self, 'Error', message)
        raise RuntimeError(message)

    def _generate_templates(self):
        base_path = self.base_path.text()

        data = self._ui_to_dict()
        global_data = self._global_to_dict()
        try:
            net_processing._validate_config(data, global_data)
            net_processing._write_pickle(data, global_data, base_path)
            net_processing._write_nic_configs(data, global_data, base_path)
            # We need a fresh, unmolested copy of the dict for the following steps
            data = self._ui_to_dict()
            net_processing._write_net_env(data, global_data, base_path)
            net_processing._write_net_iso(data, global_data, base_path)
            net_processing._write_net_iso(data, global_data, base_path,
                filename='network-isolation-absolute.yaml',
                template_path='/usr/share/openstack-tripleo-heat-templates')
        except RuntimeError as e:
            self._error(str(e))
        QtGui.QMessageBox.information(self, 'Success!',
                                      'Templates generated successfully')
        print 'Templates generated successfully'

    def _set_output_path(self):
        new_path = QtGui.QFileDialog.getExistingDirectory(self,
            'Select Output Directory', self.base_path.text())
        if new_path:
            self.base_path.setText(new_path)

    def _load(self):
        load_path = QtGui.QFileDialog.getExistingDirectory(self,
            'Select Previously Generated Directory', self.base_path.text())
        if load_path:
            self._load_templates(load_path)

    def _load_templates(self, load_path):
        self.base_path.setText(load_path)
        data, global_data = net_processing._load(load_path)
        # Global first because that's where the version check happens
        self._dict_to_global(global_data)
        self._dict_to_ui(data)

    def _node_type_changed(self, index):
        self.interfaces.setModel(
            self._node_models[self.node_type.currentItem()])
        self.nested_interfaces.setModel(QtGui.QStandardItemModel(0, 1))
        self.leaf_interfaces.setModel(QtGui.QStandardItemModel(0, 1))

    def _node_type_focused(self):
        self._last_selected = self.node_type

    def _interface_changed(self, index):
        row = index.row()
        if row >= 0:
            item = index.model().item(row)
            self.nested_interfaces.setModel(self._interface_models[item])
            self.leaf_interfaces.setModel(QtGui.QStandardItemModel(0, 1))
            self._update_input(item)
        else:
            self.nested_interfaces.setModel(QtGui.QStandardItemModel(0, 1))
            self.leaf_interfaces.setModel(QtGui.QStandardItemModel(0, 1))

    def _interface_focused(self):
        self._last_selected = self.interfaces
        self._interface_changed(self.interfaces.currentIndex())

    def _nested_changed(self, index):
        row = index.row()
        if row >= 0:
            item = index.model().item(row)
            self.leaf_interfaces.setModel(self._nested_models[item])
            self._update_input(item)

    def _nested_focused(self):
        self._last_selected = self.nested_interfaces
        self._nested_changed(self.nested_interfaces.currentIndex())

    def _leaf_changed(self, index):
        row = index.row()
        if row >= 0:
            item = index.model().item(row)
            self._update_input(item)

    def _leaf_focused(self):
        self._last_selected = self.leaf_interfaces
        self._leaf_changed(self.leaf_interfaces.currentIndex())

    def _next_nic_name(self):
        """Guess a reasonable next nic number

        Looks through the existing configuration to find the highest numbered
        nic, then returns the name of the next in line.
        """
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
                    if nd['type'] == 'ovs_bond':
                        item = nested.item(j)
                        leaf = self._nested_models[item]
                        for k in range(leaf.rowCount()):
                            ld = leaf.item(k).data()
                            next_nic_num = calculate_from_data(ld,
                                                               next_nic_num)
        nic_name = 'nic%d' % next_nic_num
        return nic_name

    def _new_nic_item(self, nic_name, network='ControlPlane'):
        item = QtGui.QStandardItem(
            QtGui.QIcon(os.path.join('icons', 'network-wired.png')),
            nic_name)
        item.setData({'type': 'interface',
                      'name': nic_name,
                      'use_dhcp': False,
                      'addresses': [],
                      'routes': [],
                      'network': network,
                      'primary': True,
                      'mtu': -1,
                      })
        return item

    def _add_interface(self):
        err_msg = ('Can only add interfaces to top-level nodes, bridges, and '
                   'bonds.')
        if self._last_selected is self.node_type:
            current_item = self.node_type.currentItem()
            current_model = self._node_models[current_item]
            nic_name = self._next_nic_name()
            item = self._new_nic_item(nic_name)
            self._add_item(item, current_model, self._interface_models)
        elif self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            if current_item.data()['type'] != 'ovs_bridge':
                self._error(err_msg)
            current_model = self._interface_models[current_item]
            nic_name = self._next_nic_name()
            item = self._new_nic_item(nic_name, 'None')
            self._add_item(item, current_model, self._nested_models)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
            if current_item.data()['type'] != 'ovs_bond':
                self._error(err_msg)
            current_model = self._nested_models[current_item]
            nic_name = self._next_nic_name()
            item = self._new_nic_item(nic_name, 'None')
            # Only default the first interface in a bond to primary
            if current_model.rowCount():
                d = item.data()
                d['primary'] = False
                item.setData(d)
            self._add_item(item, current_model)
        else:
            self._error(err_msg)

    def _add_item(self, item, model, submodels=None):
        if submodels is not None:
            submodels[item] = QtGui.QStandardItemModel(0, 1)
        model.appendRow(item)
        self._update_enabled_networks()

    def _add_bridge(self):
        if self._last_selected is self.node_type:
            current_item = self.node_type.currentItem()
            current_model = self._node_models[current_item]
            bridge_name = 'br-ex'
            item = QtGui.QStandardItem(
                QtGui.QIcon(os.path.join('icons', 'bridge.png')), bridge_name)
            item.setData({'type': 'ovs_bridge',
                          'name': bridge_name,
                          'use_dhcp': False,
                          'dns_servers': '{get_param: DnsServers}',
                          'addresses': [],
                          'routes': [],
                          'members': [],
                          'network': 'None',
                          'mtu': -1,
                          })
            self._add_item(item, current_model, self._interface_models)
        else:
            self._error('Can only add bridges to top-level nodes')

    def _add_vlan(self):
        def new_item():
            item = QtGui.QStandardItem(
                QtGui.QIcon(os.path.join('icons', 'network-workgroup.png')),
                'VLAN')
            item.setData({'type': 'vlan',
                          'vlan_id': '',
                          'addresses': [],
                          'routes': [],
                          'network': 'External',
                          'name': 'VLAN',
                          'mtu': -1,
                          })
            return item

        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            current_model = self._interface_models[current_item]
            item = new_item()
            self._add_item(item, current_model, self._nested_models)
        else:
            self._error('Can only add VLANs to bridges')

    def _add_bond(self):
        err_msg = 'Can only add bonds to OVS bridges'
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            if current_item.data()['type'] != 'ovs_bridge':
                self._error(err_msg)
            current_model = self._interface_models[current_item]
            bond_name = 'bond1'
            item = QtGui.QStandardItem(
                QtGui.QIcon(os.path.join('icons', 'repository.png')),
                bond_name)
            # The ovs_bond type is a historical artifact from when these only
            # supported OVS bonds.  Since it turns out that linux_bonds are
            # very similar, the same object is used, but the type is left
            # alone for compatibility purposes.  It will be mapped to the
            # appropriate value in net_processing.
            # NOTE(bnemec): bond_type was added later - you cannot assume all
            # bond items will have that key.
            item.setData({'type': 'ovs_bond',
                          'name': bond_name,
                          'ovs_options':
                              '{get_param: BondInterfaceOvsOptions}',
                          'network': 'None',
                          'mtu': -1,
                          'bond_type': 'ovs',
                          'routes': [],
                          })
            self._add_item(item, current_model, self._nested_models)
        else:
            self._error(err_msg)

    def _add_route(self):
        def new_item():
            item = QtGui.QStandardItem(
                QtGui.QIcon(os.path.join('icons', 'arrow-right.png')),
                'Route')
            item.setData({'type': 'route',
                          'ip_netmask': '0.0.0.0/0',
                          'next_hop': '0.0.0.0',
                          'name': 'Route',
                          'default': False,
                          })
            return item

        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
            current_model = self._interface_models[current_item]
            item = new_item()
            self._add_item(item, current_model, self._nested_models)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
            current_model = self._nested_models[current_item]
            item = new_item()
            self._add_item(item, current_model)
        else:
            self._error('Cannot add route to this device')

    def _delete_current(self):
        if self._last_selected is self.node_type:
            self._error('Cannot delete top-level node type')
        elif self._last_selected is self.interfaces:
            current_index = self.interfaces.currentIndex()
        elif self._last_selected is self.nested_interfaces:
            current_index = self.nested_interfaces.currentIndex()
        elif self._last_selected is self.leaf_interfaces:
            current_index = self.leaf_interfaces.currentIndex()
        else:
            self._error('Cannot delete.  Unexpected UI state.')
        current_index.model().takeRow(current_index.row())

    def _update_input(self, item):
        """Update UI input elements to match selected item

        Should be called any time the selected item changes so the UI stays
        in sync.
        """
        d = item.data()
        if d['type'] == 'route':
            self.route_group.setVisible(True)
            self.network_group.setVisible(False)
        else:
            self.route_group.setVisible(False)
            self.network_group.setVisible(True)
        if d['type'] == 'interface':
            self.interface_group.setVisible(True)
        else:
            self.interface_group.setVisible(False)
        if d['type'] == 'ovs_bond':
            self.bond_group.setVisible(True)
        else:
            self.bond_group.setVisible(False)
        if d['type'] == 'ovs_bridge':
            self.bridge_group.setVisible(True)
        else:
            self.bridge_group.setVisible(False)

        self.network_type.setCurrentIndex(
            self.network_type.findText(d.get('network', 'None')))
        if 'primary' in d:
            self.primary.setDisabled(False)
            self.primary.setChecked(d['primary'])
        else:
            self.primary.setDisabled(True)
        self.item_name.setText(d['name'])
        if 'mtu' in d:
            self.mtu.setVisible(True)
            self.mtu.setValue(d['mtu'])
        else:
            self.mtu.setVisible(False)
        if 'ip_netmask' in d:
            self.route_netmask.setText(d['ip_netmask'])
            self.route_next_hop.setText(d['next_hop'])
            self.route_default.setChecked(d['default'])
        else:
            self.route_netmask.setText('')
            self.route_next_hop.setText('')
        if d['type'] == 'ovs_bond':
            if d.get('bond_type', 'ovs') == 'ovs':
                self.bond_type.setCurrentIndex(0)
            elif d.get('bond_type', 'ovs') == 'linux':
                self.bond_type.setCurrentIndex(1)
            elif d.get('bond_type', 'ovs') == 'team':
                self.bond_type.setCurrentIndex(2)
        if d['type'] == 'ovs_bridge':
            if d.get('bridge_type', 'ovs') == 'ovs':
                self.bridge_type.setCurrentIndex(0)
            elif d.get('bridge_type', 'ovs') == 'ovs_user':
                self.bridge_type.setCurrentIndex(1)

    def _network_type_changed(self, _):
        new_name = self.network_type.currentText()
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        elif self._last_selected is self.leaf_interfaces:
            current_item = get_current_item(self.leaf_interfaces)
        else:
            self._error('Cannot change network type of nodes')
        d = current_item.data()
        if 'network' in d:
            d['network'] = new_name
        current_item.setData(d)
        self._update_enabled_networks()

    def _update_enabled_networks(self):
        data = self._ui_to_dict()
        self.external_group.setEnabled(
            net_processing._net_used_all(data, 'External')[0])
        self.internal_group.setEnabled(
            net_processing._net_used_all(data, 'InternalApi')[0])
        self.storage_group.setEnabled(
            net_processing._net_used_all(data, 'Storage')[0])
        self.storage_mgmt_group.setEnabled(
            net_processing._net_used_all(data, 'StorageMgmt')[0])
        self.tenant_group.setEnabled(
            net_processing._net_used_all(data, 'Tenant')[0])
        self.management_group.setEnabled(
            net_processing._net_used_all(data, 'Management')[0])

    def _primary_changed(self, state):
        if self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        if self._last_selected is self.leaf_interfaces:
            current_item = get_current_item(self.leaf_interfaces)
        else:
            # This should be a RuntimeError, but right now we don't
            # differentiate properly between when this changes due to user
            # input and when it's changed programmatically, which causes
            # this error to be raised incorrectly.
            return
            #self._error('Cannot set primary on top-level interfaces')
        d = current_item.data()
        d['primary'] = self.primary.isChecked()
        current_item.setData(d)

    def _name_changed(self, text):
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        elif self._last_selected is self.leaf_interfaces:
            current_item = get_current_item(self.leaf_interfaces)
        else:
            self._error('Cannot change name of node types')
        current_item.setText(text)
        d = current_item.data()
        d['name'] = self.item_name.text()
        current_item.setData(d)

    def _mtu_changed(self, value):
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        elif self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        elif self._last_selected is self.leaf_interfaces:
            current_item = get_current_item(self.leaf_interfaces)
        else:
            self._error('Cannot set MTU on top-level nodes')
        d = current_item.data()
        d['mtu'] = value
        current_item.setData(d)

    def _route_changed(self, _):
        if self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        elif self._last_selected is self.leaf_interfaces:
            current_item = get_current_item(self.leaf_interfaces)
        else:
            self._error('Cannot set route options here')
        d = current_item.data()
        d['ip_netmask'] = self.route_netmask.text()
        d['next_hop'] = self.route_next_hop.text()
        d['default'] = self.route_default.isChecked()
        current_item.setData(d)

    def _bond_changed(self, _):
        new_name = self.bond_type.currentText()
        if self._last_selected is self.nested_interfaces:
            current_item = get_current_item(self.nested_interfaces)
        d = current_item.data()
        d['bond_type'] = new_name.lower()
        current_item.setData(d)

    def _bridge_changed(self, _):
        new_name = self.bridge_type.currentText()
        if self._last_selected is self.interfaces:
            current_item = get_current_item(self.interfaces)
        d = current_item.data()
        d['bridge_type'] = new_name.lower().replace(' ', '_')
        current_item.setData(d)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    form = MainForm()

    sys.exit(app.exec_())
