## Copyright 2009 Laurent Bovet <laurent.bovet@windmaster.ch>
##                Jordi Puigsegur <jordi.puigsegur@gmail.com>
##
##  This file is part of wfrog
##
##  wfrog is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

import os
import os.path
import csv
import time
from datetime import datetime
import sys

class CsvStorage(object):
    '''
    Stores samples in a CSV file.

    [ Properties ]

    path [string]:
        The path to the CSV file.
    '''

    path = None

    columns = [ 'timestamp', 'localtime', 'temp', 'hum', 'wind', 'wind_dir', 'wind_gust', 'wind_gust_dir', 'dew_point', 'rain', 'rain_rate', 'pressure', 'uv_index' ]

    logger = logging.getLogger('storage.csv')

    def write_sample(self, sample, context={}):
        if os.path.exists(self.path):
            file = open(self.path, 'a')
            writer = csv.writer(file)
        else:
            file = open(self.path, 'w')
            writer = csv.writer(file)
            writer.writerow(self.columns)
            file.flush()

        sample_row = []
        for key in self.columns:
            if key == 'timestamp':
                value = int(time.mktime(sample[key]))
            elif key == 'localtime':
                value = time.strftime('%Y-%m-%d %H:%M:%S', sample['timestamp'])
            else:
                value = sample[key]
            sample_row.append(value)

        writer.writerow(sample_row)

        self.logger.debug("Writing row: %s", sample_row)

        file.close()


    def traverse_samples(self, callback, from_time=datetime.fromtimestamp(0), to_time=datetime.now(), context={}):
        from_timestamp = int(time.mktime(from_time.timetuple()))
        file = self._position_cursor(from_timestamp)
        to_timestamp = time.mktime(to_time.timetuple())
        reader = csv.reader(file)
        for line in reader:
            if int(line[0]) < from_timestamp:
                continue
            if int(line[0]) => to_timestamp:
                break
            sample = {}
            for i in range(0,len(line)-1):
                sample[self.columns[i]] = line[i]
            callback(sample, context)

    def _position_cursor(self, timestamp):
        if not os.path.exists(self.path):
            return None

        size = os.path.getsize(self.path)
        step = offset = size / 2
        file = open(self.path, 'r')

        while abs(step) > 1:
            last_pos = file.tell()
            if last_pos + offset < 0:
                break

            file.seek(offset, os.SEEK_CUR)
            (current_timestamp, shift) = self._get_timestamp(file)

            if current_timestamp is None:
                file.seek(last_pos)
                break

            pos = file.tell()

            if current_timestamp == timestamp:
                break

            if current_timestamp < timestamp:
                step = abs(step) / 2
            else:
                step = - abs(step) / 2

            offset = step - shift

        return file

    timestamp_length = 10

    def _get_timestamp(self, file):
        skip = file.readline()
        shift = len(skip) + len('\n')
        timestamp_string = file.read(self.timestamp_length)
        if(timestamp_string.strip() == ''): # End of file
            return (None, 0)
        file.seek(-self.timestamp_length, os.SEEK_CUR)
        return ( int(timestamp_string), shift)


def dump(value, context):
    print repr(value)


if __name__ == '__main__':

    s = CsvStorage()

    s.path = '/tmp/wfrog.csv'

    timestamp = int(sys.argv[1])

    f = s._position_cursor(timestamp)

    if f is not None:
        print f.readline()
        f.close()

    s = CsvStorage()

    s.path = '/tmp/wfrog.csv'

    format = "%Y-%m-%d %H:%M:%S"

    s.traverse_samples(dump, from_time=datetime.strptime('2010-03-12 23:32:00', format) ,
        to_time=datetime.strptime('2010-03-12 23:50:00', format))

