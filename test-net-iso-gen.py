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

import json
import os
import shutil
import tempfile
import unittest

import net_processing

class TestOutput(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(self.output_path)

    def _test(self, input_path):
        self.output_path = tempfile.mkdtemp()
        with open(os.path.join(input_path, 'nic-input.json')) as f:
            data = json.loads(f.read())
        with open(os.path.join(input_path, 'global-input.json')) as f:
            global_data = json.loads(f.read())
        net_processing._write_net_env(data, global_data, self.output_path)
        with open(os.path.join(self.output_path,
                               'network-environment.yaml')) as actual:
            with open(os.path.join(input_path,
                                   'network-environment.yaml')) as expected:
                self.assertEqual(expected.read(), actual.read())

        net_processing._write_net_iso(data, self.output_path)
        with open(os.path.join(self.output_path,
                               'network-isolation.yaml')) as actual:
            with open(os.path.join(input_path,
                                   'network-isolation.yaml')) as expected:
                self.assertEqual(expected.read(), actual.read())

        net_processing._write_nic_configs(data, self.output_path)
        opath = os.path.join(self.output_path, 'nic-configs')
        for f in os.listdir(opath):
            with open(os.path.join(opath, f)) as actual:
                with open(os.path.join(input_path,
                                       'nic-configs', f)) as expected:
                    self.assertEqual(expected.read(), actual.read())

    def test_nics_basic(self):
        self._test('test-data/nics-basic')

    def test_all_the_things(self):
        self._test('test-data/all-the-things')

class TestValidations(unittest.TestCase):
    def _load_data(self, name):
        with open('test-data/%s/nic-input.json' % name) as f:
            data = json.loads(f.read())
        with open('test-data/%s/global-input.json' % name) as f:
            global_data = json.loads(f.read())
        return data, global_data

    def test_validate_config(self):
        data, global_data = self._load_data('all-the-things')
        net_processing._validate_config(data, global_data)

    def test_vlans_valid(self):
        data, global_data = self._load_data('all-the-things')
        net_processing._check_duplicate_vlans(data, global_data)

    def test_vlans_invalid(self):
        data, global_data = self._load_data('duplicate-vlans')
        self.assertRaises(RuntimeError, net_processing._check_duplicate_vlans,
                          data, global_data)

    def test_networks_valid(self):
        data, _ = self._load_data('all-the-things')
        net_processing._check_duplicate_networks(data)

    def test_networks_invalid(self):
        data, _ = self._load_data('duplicate-networks')
        self.assertRaises(RuntimeError,
                          net_processing._check_duplicate_networks,
                          data)

    def test_cidrs_valid(self):
        data, global_data = self._load_data('all-the-things')
        net_processing._check_overlapping_cidrs(data, global_data)

    def test_cidrs_duplicate(self):
        data, global_data = self._load_data('duplicate-cidrs')
        self.assertRaises(RuntimeError,
                          net_processing._check_overlapping_cidrs,
                          data, global_data)

    def test_cidrs_overlapping(self):
        data, global_data = self._load_data('overlapping-cidrs')
        self.assertRaises(RuntimeError,
                          net_processing._check_overlapping_cidrs,
                          data, global_data)

    def test_ips_in_cidr_valid(self):
        data, global_data = self._load_data('all-the-things')
        net_processing._check_ips_in_cidr(data, global_data)

    def test_start_not_in_cidr(self):
        data, global_data = self._load_data('start-not-in-cidr')
        self.assertRaises(RuntimeError,
                          net_processing._check_ips_in_cidr,
                          data, global_data)

    def test_end_not_in_cidr(self):
        data, global_data = self._load_data('end-not-in-cidr')
        self.assertRaises(RuntimeError,
                          net_processing._check_ips_in_cidr,
                          data, global_data)

    def test_gateway_not_in_cidr(self):
        data, global_data = self._load_data('gateway-not-in-cidr')
        self.assertRaises(RuntimeError,
                          net_processing._check_ips_in_cidr,
                          data, global_data)

    def test_duplicate_nics_valid(self):
        data, _ = self._load_data('all-the-things')
        net_processing._check_duplicate_nics(data)

    def test_duplicate_nics_bond(self):
        data, _ = self._load_data('duplicate-nics')
        self.assertRaises(RuntimeError,
                          net_processing._check_duplicate_nics,
                          data)

if __name__ == '__main__':
    unittest.main()
