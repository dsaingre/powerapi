# Copyright (c) 2021, INRIA
# Copyright (c) 2021, University of Lille
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from powerapi.report.report import Report, BadInputData, CSV_HEADER_COMMON, CsvLines


CSV_HEADER_HWPC = CSV_HEADER_COMMON + ['socket', 'cpu']


class HWPCReport(Report):
    """
    HWPCReport class

    JSON HWPC format

    .. code-block:: json

        {
         'timestamp': $int,
         'sensor': '$str',
         'target': '$str',
         'groups' : {
            '$group_name': {
               '$socket_id': {
                   '$core_id': {
                       '$event_name': '$int',
                       ...
                   }
                   ...
               }
               ...
            }
            ...
         }
        }
    """

    def __init__(self, timestamp: datetime, sensor: str, target: str, groups: Dict[str, Dict], metadata: Dict[str, Any] = {}):
        """
        Initialize an HWPC report using the given parameters.
        :param datetime timestamp: Timestamp of the report
        :param str sensor: Sensor name
        :param str target: Target name
        :param Dict groups: Events groups
        """
        Report.__init__(self, timestamp, sensor, target, metadata)

        #: (dict): Events groups
        self.groups = groups

    def __repr__(self) -> str:
        return 'HWCPReport(%s, %s, %s, %s, %s)' % (self.timestamp, self.sensor, self.target, sorted(self.groups.keys()), str(self.metadata))

    @staticmethod
    def from_json(data: Dict) -> HWPCReport:
        """
        Generate a report using the given data.
        :param data: Dictionary containing the report attributes
        :return: The HWPC report initialized with the given data
        """
        try:
            ts = Report._extract_timestamp(data['timestamp'])
            metadata = {} if 'metadata' not in data else data['metadata']
            return HWPCReport(ts, data['sensor'], data['target'], data['groups'], metadata)
        except KeyError as exn:
            raise BadInputData('HWPC report require field ' + str(exn.args[0]) + ' in json document', data) from exn
        except ValueError as exn:
            raise BadInputData(exn.args[0], data) from exn

    @staticmethod
    def to_json(report: HWPCReport) -> Dict:
        return report.__dict__

    @staticmethod
    def from_mongodb(data: Dict) -> HWPCReport:
        """
        :return: a HWPCReport from a dictionary pulled from mongodb
        """
        return HWPCReport.from_json(data)

    @staticmethod
    def to_mongodb(report: HWPCReport) -> Dict:
        """
        :return: a dictionary, that can be stored into a mongodb, from a given HWPCReport
        """
        return HWPCReport.to_json(report)

    @staticmethod
    def from_csv_lines(lines: CsvLines) -> HWPCReport:
        """
        :param lines: list of pre-parsed lines. a line is a tuple composed with :
                         - the file name where the line were read
                         - a dictionary where key is column name and value is the value read from the line
        :return: a HWPCReport that contains value from the given lines
        """
        sensor_name = None
        target = None
        timestamp = None
        groups = {}
        metadata = {}

        for file_name, row in lines:
            group_name = file_name[:-4] if file_name[len(file_name) - 4:] == '.csv' else file_name
            try:
                if sensor_name is None:
                    sensor_name = row['sensor']
                    target = row['target']
                    timestamp = HWPCReport._extract_timestamp(row['timestamp'])
                else:
                    if sensor_name != row['sensor']:
                        raise BadInputData('csv line with different sensor name are mixed into one report', row)
                    if target != row['target']:
                        raise BadInputData('csv line with different target are mixed into one report', row)
                    if timestamp != HWPCReport._extract_timestamp(row['timestamp']):
                        raise BadInputData('csv line with different timestamp are mixed into one report', row)

                HWPCReport._create_group(row, groups, group_name)

                for key, value in row.items():
                    if key not in CSV_HEADER_HWPC:
                        metadata[key] = value

            except KeyError as exn:
                raise BadInputData('missing field ' + str(exn.args[0]) + ' in csv file ' + file_name, row) from exn
            except ValueError as exn:
                raise BadInputData(exn.args[0], row) from exn

        return HWPCReport(timestamp, sensor_name, target, groups, metadata)

    @staticmethod
    def _create_group(row, groups, group_name):

        if group_name not in groups:
            groups[group_name] = {}

        if row['socket'] not in groups[group_name]:
            groups[group_name][row['socket']] = {}

        if row['cpu'] not in groups[group_name][row['socket']]:
            groups[group_name][row['socket']][row['cpu']] = {}

    @staticmethod
    def create_empty_report():
        """
        Creates an empty report
        """
        return HWPCReport(None, None, None, {})
