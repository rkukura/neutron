# Copyright (c) 2014 OpenStack Foundation, all rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from sqlalchemy.orm import query

from neutron import context
from neutron.db import db_base_plugin_v2
from neutron.db import l3_db
from neutron.db import models_v2
from neutron.openstack.common import uuidutils
from neutron.plugins.ml2 import db as ml2_db
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2 import models
from neutron.tests.unit import testlib_api


class Ml2DBTestCase(testlib_api.SqlTestCase):

    def setUp(self):
        super(Ml2DBTestCase, self).setUp()
        self.ctx = context.get_admin_context()

    def _setup_neutron_network(self, network_id):
        with self.ctx.session.begin(subtransactions=True):
            self.ctx.session.add(models_v2.Network(id=network_id))

    def _setup_neutron_port(self, network_id, port_id):
        mac_address = db_base_plugin_v2.NeutronDbPluginV2._generate_mac()
        with self.ctx.session.begin(subtransactions=True):
            port = models_v2.Port(id=port_id,
                                  network_id=network_id,
                                  mac_address=mac_address,
                                  admin_state_up=True,
                                  status='DOWN',
                                  device_id='',
                                  device_owner='')
            self.ctx.session.add(port)
        return port

    def _setup_neutron_portbinding(self, port_id, host):
        with self.ctx.session.begin(subtransactions=True):
            self.ctx.session.add(models.PortBinding(port_id=port_id,
                                                    host=host))

    def _create_segments(self, segments, is_seg_dynamic=False):
        network_id = 'foo-network-id'
        self._setup_neutron_network(network_id)
        for segment in segments:
            ml2_db.add_network_segment(
                self.ctx.session, network_id, segment,
                is_dynamic=is_seg_dynamic)

        net_segments = ml2_db.get_network_segments(
                           self.ctx.session, network_id,
                           filter_dynamic=is_seg_dynamic)

        for segment_index, segment in enumerate(segments):
            self.assertEqual(segment, net_segments[segment_index])

        return net_segments

    def test_network_segments_for_provider_network(self):
        segment = {api.NETWORK_TYPE: 'vlan',
                   api.PHYSICAL_NETWORK: 'physnet1',
                   api.SEGMENTATION_ID: 1}
        self._create_segments([segment])

    def test_network_segments_is_dynamic_true(self):
        segment = {api.NETWORK_TYPE: 'vlan',
                   api.PHYSICAL_NETWORK: 'physnet1',
                   api.SEGMENTATION_ID: 1}
        self._create_segments([segment], is_seg_dynamic=True)

    def test_network_segments_for_multiprovider_network(self):
        segments = [{api.NETWORK_TYPE: 'vlan',
                    api.PHYSICAL_NETWORK: 'physnet1',
                    api.SEGMENTATION_ID: 1},
                    {api.NETWORK_TYPE: 'vlan',
                     api.PHYSICAL_NETWORK: 'physnet1',
                     api.SEGMENTATION_ID: 2}]
        self._create_segments(segments)

    def test_get_segment_by_id(self):
        segment = {api.NETWORK_TYPE: 'vlan',
                   api.PHYSICAL_NETWORK: 'physnet1',
                   api.SEGMENTATION_ID: 1}

        net_segment = self._create_segments([segment])[0]
        segment_uuid = net_segment[api.ID]

        net_segment = ml2_db.get_segment_by_id(self.ctx.session, segment_uuid)
        self.assertEqual(segment, net_segment)

    def test_get_segment_by_id_result_not_found(self):
        segment_uuid = uuidutils.generate_uuid()
        net_segment = ml2_db.get_segment_by_id(self.ctx.session, segment_uuid)
        self.assertIsNone(net_segment)

    def test_delete_network_segment(self):
        segment = {api.NETWORK_TYPE: 'vlan',
                   api.PHYSICAL_NETWORK: 'physnet1',
                   api.SEGMENTATION_ID: 1}

        net_segment = self._create_segments([segment])[0]
        segment_uuid = net_segment[api.ID]

        ml2_db.delete_network_segment(self.ctx.session, segment_uuid)
        # Get segment and verify its empty
        net_segment = ml2_db.get_segment_by_id(self.ctx.session, segment_uuid)
        self.assertIsNone(net_segment)

    def test_add_port_binding(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id)

        port = ml2_db.add_port_binding(self.ctx.session, port_id)
        self.assertEqual(port_id, port.port_id)

    def test_get_port_binding_host(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        host = 'fake_host'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id)
        self._setup_neutron_portbinding(port_id, host)

        port_host = ml2_db.get_port_binding_host(self.ctx.session, port_id)
        self.assertEqual(host, port_host)

    def test_get_port_binding_host_multiple_results_found(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        port_id_one = 'foo-port-id-one'
        port_id_two = 'foo-port-id-two'
        host = 'fake_host'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id_one)
        self._setup_neutron_portbinding(port_id_one, host)
        self._setup_neutron_port(network_id, port_id_two)
        self._setup_neutron_portbinding(port_id_two, host)

        port_host = ml2_db.get_port_binding_host(self.ctx.session, port_id)
        self.assertIsNone(port_host)

    def test_get_port_binding_host_result_not_found(self):
        port_id = uuidutils.generate_uuid()

        port_host = ml2_db.get_port_binding_host(self.ctx.session, port_id)
        self.assertIsNone(port_host)

    def test_get_port(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id)

        port = ml2_db.get_port(self.ctx.session, port_id)
        self.assertEqual(port_id, port.id)

    def test_get_port_multiple_results_found(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        port_id_one = 'foo-port-id-one'
        port_id_two = 'foo-port-id-two'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id_one)
        self._setup_neutron_port(network_id, port_id_two)

        port = ml2_db.get_port(self.ctx.session, port_id)
        self.assertIsNone(port)

    def test_get_port_result_not_found(self):
        port_id = uuidutils.generate_uuid()
        port = ml2_db.get_port(self.ctx.session, port_id)
        self.assertIsNone(port)

    def test_get_port_from_device_mac(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        self._setup_neutron_network(network_id)
        port = self._setup_neutron_port(network_id, port_id)

        observed_port = ml2_db.get_port_from_device_mac(port['mac_address'])
        self.assertEqual(port_id, observed_port.id)

    def test_get_locked_port_and_binding(self):
        network_id = 'foo-network-id'
        port_id = 'foo-port-id'
        host = 'fake_host'
        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id)
        self._setup_neutron_portbinding(port_id, host)

        port, binding = ml2_db.get_locked_port_and_binding(self.ctx.session,
                                                           port_id)
        self.assertEqual(port_id, port.id)
        self.assertEqual(port_id, binding.port_id)

    def test_get_locked_port_and_binding_result_not_found(self):
        port_id = uuidutils.generate_uuid()

        port, binding = ml2_db.get_locked_port_and_binding(self.ctx.session,
                                                           port_id)
        self.assertIsNone(port)
        self.assertIsNone(binding)

    def test_binding_result(self):
        network_id = uuidutils.generate_uuid()
        port_id = uuidutils.generate_uuid()
        host = 'test_host'
        vif_type = 'test_vif_type'
        vif_details = 'test_vif_details'
        segment = {api.NETWORK_TYPE: 'vlan',
                   api.PHYSICAL_NETWORK: 'physnet1',
                   api.SEGMENTATION_ID: 1}

        self._setup_neutron_network(network_id)
        ml2_db.add_network_segment(self.ctx.session,
                                   network_id,
                                   segment)
        segments = ml2_db.get_network_segments(self.ctx.session,
                                               network_id)
        segment_id = segments[0][api.ID]

        self._setup_neutron_port(network_id, port_id)

        level0 = models.PortBindingLevel(port_id=port_id,
                                         host=host,
                                         level=0,
                                         driver='test_driver_0',
                                         segment_id=segment_id)
        level1 = models.PortBindingLevel(port_id=port_id,
                                         host=host,
                                         level=1,
                                         driver='test_driver_1',
                                         segment_id=segment_id)
        levels = [level0, level1]

        # Verify no binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.get_binding_result(self.ctx.session,
                                               port_id,
                                               host)
            self.assertIsNone(result)

        # Verify no binding levels.
        with self.ctx.session.begin(subtransactions=True):
            result_levels = ml2_db.get_binding_levels(self.ctx.session,
                                                      port_id,
                                                      host)
            self.assertEqual(0, len(result_levels))

        # Set binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.set_binding_result(self.ctx.session,
                                               port_id,
                                               host,
                                               vif_type,
                                               vif_details,
                                               levels)
            self.assertEqual(port_id, result.port_id)
            self.assertEqual(host, result.host)
            self.assertEqual(vif_type, result.vif_type)
            self.assertEqual(vif_details, result.vif_details)

        # Get and verify binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.get_binding_result(self.ctx.session,
                                               port_id,
                                               host)
            self.assertEqual(port_id, result.port_id)
            self.assertEqual(host, result.host)
            self.assertEqual(vif_type, result.vif_type)
            self.assertEqual(vif_details, result.vif_details)

        # Get and verify binding levels.
        with self.ctx.session.begin(subtransactions=True):
            result_levels = ml2_db.get_binding_levels(self.ctx.session,
                                                      port_id,
                                                      host)
            self.assertEqual(2, len(result_levels))
            self.assertEqual(level0, result_levels[0])
            self.assertEqual(level1, result_levels[1])

        # Clear binding result.
        with self.ctx.session.begin(subtransactions=True):
            ml2_db.clear_binding_result(self.ctx.session,
                                        port_id,
                                        host)

        # Verify no binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.get_binding_result(self.ctx.session,
                                               port_id,
                                               host)
            self.assertIsNone(result)

        # Verify no binding levels.
        with self.ctx.session.begin(subtransactions=True):
            result_levels = ml2_db.get_binding_levels(self.ctx.session,
                                                      port_id,
                                                      host)
            self.assertEqual(0, len(result_levels))

    def test_binding_result_no_levels(self):
        network_id = uuidutils.generate_uuid()
        port_id = uuidutils.generate_uuid()
        host = 'test_host'
        vif_type = 'test_vif_type'

        self._setup_neutron_network(network_id)
        self._setup_neutron_port(network_id, port_id)

        # Set binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.set_binding_result(self.ctx.session,
                                               port_id,
                                               host,
                                               vif_type)
            self.assertEqual(port_id, result.port_id)
            self.assertEqual(host, result.host)
            self.assertEqual(vif_type, result.vif_type)
            self.assertEqual(None, result.vif_details)

        # Get and verify binding result.
        with self.ctx.session.begin(subtransactions=True):
            result = ml2_db.get_binding_result(self.ctx.session,
                                               port_id,
                                               host)
            self.assertEqual(port_id, result.port_id)
            self.assertEqual(host, result.host)
            self.assertEqual(vif_type, result.vif_type)
            self.assertEqual('', result.vif_details)

        # Verify binding levels.
        with self.ctx.session.begin(subtransactions=True):
            result_levels = ml2_db.get_binding_levels(self.ctx.session,
                                                      port_id,
                                                      host)
            self.assertEqual(0, len(result_levels))
