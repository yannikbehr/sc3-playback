#!/usr/bin/env python
"""
Generate bindings from event waveform file.
"""
from collections import defaultdict
import os
from argparse import ArgumentParser

from obspy import read


parser = ArgumentParser(prog='event_bindings',
                        description=__doc__.strip())
parser.add_argument('wfile', type=str,
                    help='Path to the event waveform file.')
parser.add_argument('-r', '--rootdir', type=str,
                    default='./data/',
                    help='Path to the root directory.')
args = parser.parse_args()
basedirname = os.path.basename(args.wfile[0:args.wfile.rfind('.')])
bindings_dir = os.path.join(args.rootdir, basedirname+'_bindings') 
try:
    os.makedirs(bindings_dir)
except FileExistsError:
    pass
for dirname in ['global', 'scautopick', 'seedlink']:
    try:
        os.makedirs(os.path.join(bindings_dir, dirname))
    except FileExistsError:
        pass

# Generate global profiles
fn_bb = os.path.join(bindings_dir, 'global', 'profile_broadband')
with open(fn_bb, 'w') as fh:
    fh.write('detecStream = HH\n')
    fh.write('detecLocid = 10\n')

fn_sm = os.path.join(bindings_dir, 'global', 'profile_strong')
with open(fn_sm, 'w') as fh:
    fh.write('detecStream = HN\n')
    fh.write('detecLocid = 20\n')

# Generate scautopick profile
fn_bb = os.path.join(bindings_dir, 'scautopick', 'profile_broadband')
with open(fn_bb, 'w') as fh:
    fh.write('detecFilter = "RMHP(10)>>BW(4,2,15)>>STALTA(0.5,20)"\n')
    fh.write('timeCorr = -0.05\n')
    
# Generate seedlink profile
fn_bb = os.path.join(bindings_dir, 'seedlink', 'profile_broadband')
with open(fn_bb, 'w') as fh:
    pass

st = read(args.wfile)
stations = defaultdict(list)
for tr in st:
    _st = tr.stats
    stations[_st.station].append(_st.channel)
 
for station, channels in stations.items():
    fn = os.path.join(bindings_dir, 'station_{}_{}'.format('NZ', station))
    with open(fn, 'w') as fh:
        if 'HNZ' in channels:
            fh.write('global:strong\n')
        elif 'HHZ' in channels:
            fh.write('global:broadband\n')
        else:
            print("Channels for station {} are {}".format(station,
                                                          channels))
            continue
        fh.write('scautopick:broadband\n')
        fh.write('seedlink:broadband\n')
