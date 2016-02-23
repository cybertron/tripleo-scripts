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


DATA_MAJOR = 0
DATA_MINOR = 1


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

        generate_layout = QtGui.QHBoxLayout()
        self.base_path = QtGui.QLineEdit('/tmp/templates')
        generate_layout.addWidget(self.base_path, 5)

        set_path = QtGui.QPushButton('Set Output Path')
        set_path.clicked.connect(self._set_output_path)
        generate_layout.addWidget(set_path, 1)

        generate = QtGui.QPushButton('Generate')
        generate.clicked.connect(self._generate_templates)
        generate_layout.addWidget(generate, 3)
        main_layout.addLayout(generate_layout)

    def _ui_to_dict(self):
        """Convert the UI data to a more readable dict

        :returns: dict representing the current UI state
        """
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
        return retval

    def _generate_templates(self):
        base_path = self.base_path.text()

        data = self._ui_to_dict()
        global_data = self._global_to_dict()
        net_processing._validate_config(data, global_data)
        net_processing._write_nic_configs(data, base_path)
        # We need a fresh, unmolested copy of the dict for the following steps
        data = self._ui_to_dict()
        net_processing._write_net_env(data, global_data, base_path)
        net_processing._write_net_iso(data, base_path)
        print 'Templates generated successfully'

    def _set_output_path(self):
        new_path = QtGui.QFileDialog.getExistingDirectory(self,
            'Select Output Directory', self.base_path.text())
        if new_path:
            self.base_path.setText(new_path)

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