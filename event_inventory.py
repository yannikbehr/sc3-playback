#!/usr/bin/env python
"""
Write an event specific inventory.
"""
import io
import logging
import sys
from obspy import read, read_inventory, Inventory
import copy
from argparse import ArgumentParser


parser = ArgumentParser(prog='event_inventory',
                        description=__doc__.strip())
parser.add_argument('wfile', type=str,
                    help='Path to the event waveform file.')
parser.add_argument('-i', '--inventory', type=str,
                    default='./data/complete.xml',
                    help='Path to the master inventory file.')
args = parser.parse_args()
invfn = args.inventory
logging.debug("Reading inventory file: " + invfn)
inv = read_inventory(invfn)
wfn = args.wfile
if wfn == '-':
    wfn = sys.stdin.read().rstrip()
logging.debug("Reading waveform file: " + wfn)
st = read(wfn)

nslcs = []
selected_stations = []
for tr in st:
    _st = tr.stats
    nslc = dict(network=_st.network,
                station=_st.station,
                location=_st.location,
                channel=_st.channel)
    if nslc not in nslcs:
        nslcs.append(nslc)
    if _st.station not in selected_stations:
        selected_stations.append(_st.station)
selected_channels = ['HHE', 'HHN', 'HHZ', 'HNE', 'HNN', 'HNZ', 'HN1', 'HN2']


stations = []
net = inv.networks[0]
for sta in net:
    if sta.code not in selected_stations:
        continue
    channels = []
    for cha in sta:
        if cha.code not in selected_channels:
            continue
        channels.append(cha)
    sta = copy.copy(sta)
    sta.channels = channels
    stations.append(sta)

net = copy.copy(net)
net.stations = stations
ninv = Inventory()
ninv.networks = [net]
# fout = wfn[0:wfn.rfind('.')] + '.xml'
output = io.BytesIO()
ninv.write(output, format='STATIONXML')
print(output.getvalue().decode('utf-8'))