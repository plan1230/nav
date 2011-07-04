# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#

from twisted.internet import defer
from twisted.internet import threads

from nav.mibs import reduce_index
from nav.mibs.entity_mib import EntityMib

import mibretriever

UNITS_OF_MEASUREMENTS = {
    1: 'Other',
    2: 'Unknown',
    3: 'VoltsAC',
    4: 'VoltsDC',
    5: 'Amperes',
    6: 'Watts',
    7: 'Hertz',
    8: 'Celsius',
    9: 'Percent Relative Humidity',
    10: 'rpm',
    11: 'Cubic meters per min.',
    12: 'Truthvalue {true(1), false(2)}',
}

DATA_SCALE = {
    1: 'yocto',
    2: 'zepto',
    3: 'atto',
    4: 'femto',
    5: 'pico',
    6: 'nano',
    7: 'micro',
    8: 'milli',
    9: None,
   10: 'kilo',
   11: 'mega',
   12: 'giga',
   13: 'tera',
   14: 'exa',
   15: 'peta',
   16: 'zetta',
   17: 'yotta',
  }

class EntitySensorMib(mibretriever.MibRetriever):
    from nav.smidumps.entity_sensor_mib import MIB as mib

    def get_module_name(self):
        return self.mib.get('moduleName', None)

    def _get_sensors(self):
        """ Collect all sensors."""
        df = self.retrieve_columns([
                'entPhySensorType',
                'entPhySensorScale',
                'entPhySensorPrecision',
                'entPhySensorValue',
                'entPhySensorOperStatus',
                'entPhySensorUnitsDisplay',
                ])
        df.addCallback(reduce_index)
        return df
            
    def _collect_entity_names(self):
        """ Collect all entity-names on netbox."""
        entity_mib = EntityMib(self.agent_proxy)
        df = entity_mib.retrieve_columns([
                'entPhysicalDescr',
                'entPhysicalName',
                ])
        df.addCallback(reduce_index)
        return df

    @defer.inlineCallbacks
    def can_return_sensors(self):
        sensors = yield self._get_sensors()
        self.logger.error('EntitySensorMib:: can_return_sensors: ip = %s' % self.agent_proxy.ip)
        self.logger.error('EntitySensorMib:: can_return_sensors: len = %d' % len(sensors))
        if len(sensors) > 0:
            self.logger.error('EntitySensorMib:: can_return_sensors: Return True')
            defer.returnValue(True)
        self.logger.error('EntitySensorMib:: can_return_sensors: Return False')
        defer.returnValue(False)
        
    @defer.inlineCallbacks
    def get_all_sensors(self):
        """ Collect all sensors and names on a netbox, and match
            sensors with names.
            
            Return a list with dictionaries, each dictionary
            represent a sensor."""
        sensors = yield self._get_sensors()
        entity_names = yield self._collect_entity_names()
        for idx, row in entity_names.items():
            if idx in sensors:
                sensors[idx]['entPhysicalDescr'] = row.get(
                                                    'entPhysicalDescr',None)
                sensors[idx]['entPhysicalName'] = row.get(
                                                    'entPhysicalName', None)
        result = []
        for row_id, row in sensors.items():
            row_oid = row.get(0, None)
            mibobject = self.nodes.get('entPhySensorValue', None)
            oid = str(mibobject.oid) + str(row_oid)
            unit_of_measurement = row.get('entPhySensorType', 2)
            scale = row.get('entPhySensorScale', None)
            op_status = row.get('entPhySensorOperStatus', None)
            description = row.get('entPhysicalDescr')
            name = row.get('entPhysicalName', None)
            internal_name = name
            if op_status == 1:
                result.append({
                    'oid': oid,
                    'unit_of_measurement': UNITS_OF_MEASUREMENTS.get(
                                                unit_of_measurement, None),
                    'scale': DATA_SCALE.get(scale, None),
                    'description': description,
                    'name': name,
                    'internal_name': internal_name,
                    'mib': self.get_module_name(),
                    })
        ##self.logger.error('get_all_sensors: result=%s' % result)
        defer.returnValue(result)
