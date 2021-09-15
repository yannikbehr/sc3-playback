#!/usr/bin/env python
"""
Created on Mar 28, 2014

@author: behry
"""
from datetime import datetime, timedelta
import os
import logging

from cachier import cachier
from obspy.clients.fdsn import Client as FDSN_Client
from obspy import UTCDateTime, Stream
import numpy as np
import ipdb


def myhash(args, kwds):
    self = args[0]
    key = []
    for a in args[1:]:
        if isinstance(a, list):
            key.append(tuple(a))
        else:
            key.append(a)
    key.append(str(self.t1))
    key.append(str(self.t2))
    key.append(str(self.latitude))
    key.append(str(self.longitude))
    key.append(str(self.radius))
    key = tuple(key)
    key += tuple(sorted(kwds.items()))
    return key


class EventData:

    def __init__(self, event, savedir='/tmp', radius=2., offset_before=600,
                 offset_after=600):
        """
        Parameters:
        -----------
        event: dict-like
               Event parameters to download data for
        radius: float
                Radius in degrees within which to look
                for stations
        offset_before: float
                       Number of seconds before event
                       time to start waveform request
        offset_after: float
                      Number of seconds after event
                      time to end waveform request
        """
        self.mylogger = logging.getLogger('MyLogger')
        self.mylogger.setLevel(logging.ERROR)
        self.client = FDSN_Client(base_url='http://service.geonet.org.nz',
                                  debug=False)
        self.t1 = UTCDateTime(event['time']) - offset_before
        self.t2 = UTCDateTime(event['time']) + offset_after
        self.latitude = event['lat']
        self.longitude = event['lon']
        self.radius = radius
        self.inv = self.get_inventory(['HHZ','HNZ', 'HHE',
                                       'HHN', 'HNE', 'HNN',
                                       'HN1', 'HN2', 'HH1',
                                       'HH2'])
        if not os.path.isdir(savedir):
            print("Creating download directory \n {:s}".format(savedir))
            os.makedirs(savedir)
        self.filename = os.path.join(savedir, event['name']+'.ms')

    @cachier(stale_after=timedelta(hours=1),
             cache_dir='/tmp/.cache', hash_params=myhash)
    def get_inventory(self, channels, level='channel'):
        inv = self.client.get_stations(latitude=self.latitude,
                                       longitude=self.longitude,
                                       maxradius=self.radius,
                                       startbefore=self.t1, endafter=self.t2,
                                       network='NZ', channel=','.join(channels),
                                       level=level)
        return inv

    def get_waveforms(self, rmresponse=False, rmsensitivity=True):

        print("Starting to request data for:")
        stmain = Stream()
        for net in self.inv:
           for stat in net:
               for chan in stat:
                   try:
                        nslc = '{}.{}.{}.{}'
                        nslc = nslc.format(net.code, stat.code,
                                           chan.location_code,
                                           chan.code)
                        print("---> {}".format(nslc))
                        st = self.client.get_waveforms(net.code, stat.code,
                                                       chan.location_code, chan.code,
                                                       self.t1, self.t2,
                                                       attach_response=rmresponse & rmsensitivity)
                        if rmresponse:
                            st.remove_response(output="VEL")
                        if rmsensitivity:
                            st.remove_sensitivity()
                        stmain += st
                   except Exception as e:
                        print(e)
                        self.mylogger.error("%s" % nslc)
                        continue
        stmain.write(self.filename, format='MSEED')


def test_inventory():
    ed = EventData(Darfield)
    inv = ed.get_inventory(['HHZ', 'HNZ'])
    for net in inv:
        for stat in net:
            for chan in stat:
                nslc = '{}.{}.{}.{}'
                nslc = nslc.format(net.code, stat.code,
                                   chan.location_code,
                                   chan.code)
                print(nslc)

if __name__ == '__main__':
    # Events
    Darfield = [dict(name='Darfield_2010',
                    time='2010-09-03T16:35:41Z',
                    lat=-43.53, lon=172.17, dep=11)]
    Kaikoura = [dict(name='Kaikoura_2016',
                    time='2016-11-13T11:02:56Z',
                    lat=-42.69, lon=173.02, dep=15)] 


    from argparse import ArgumentParser
    import json
    parser = ArgumentParser(prog='event_data',
                            description=__doc__.strip())
    parser.add_argument('-e', '--events', type=str,
                        default='Darfield',
                        help='Name of event or json file with event data.')
    parser.add_argument('-o', '--outdir', type=str,
                        default='/tmp',
                        help='Directory to write waveform files to.')
    args = parser.parse_args()
    try:
        with open(args.events, 'r') as fh:
            config = json.load(fh)
            events = config['events']
    except FileNotFoundError:
        events = eval(args.events)
    for event in events:
        ed = EventData(event, savedir=args.outdir)
        ed.get_waveforms(rmsensitivity=False)
