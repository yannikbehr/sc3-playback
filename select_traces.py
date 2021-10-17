#!/usr/bin/env python
"""
Further select traces in waveform file.
"""
from argparse import ArgumentParser
import io
import logging
import sys

from obspy import (Stream,
                   read,
                   read_inventory,
                   UTCDateTime)

def select_traces(st, inv, tc=True, colloc=False, triggered=True):
    """
    Refine selection of traces for playback.
    
    Parameters:
    -----------
    st : :class:`obspy.Stream`
         All data originally collected for playback
    inv : :class:`obspy.Inventory`
         Station inventory
    tc : boolean
         If 'True' only select stations with 3 components.
    colloc : boolean
             If 'True' include collocated broadband sensors.
    
    Returns:
    --------
    :class:`obspy.Stream` : The selected data.
    """
    required_bits = 4
    newst = Stream()
    if tc:
        required_bits = 7
    for _st in inv.networks[0]: 
        hn_stream = Stream()
        hn_bits = 0
        for bit, c in zip([1, 2, 4], ['HNN', 'HNE', 'HNZ']):
            _tmpst = st.select(network='NZ', station=_st.code, location='20', channel=c)
            if len(_tmpst) > 0:
                _tmpst.merge(method=1, fill_value=0, interpolation_samples=-1)
                hn_stream += _tmpst
                hn_bits += bit

        if hn_bits >= required_bits:
            newst += hn_stream
            if not colloc:
                continue

        if triggered:
            hn1_stream = Stream()
            hn1_bits = 0
            for bit, c in zip([1, 2, 4], ['HN1', 'HN2', 'HNZ']):
                _tmpst = st.select(network='NZ', station=_st.code, location='20', channel=c)
                if len(_tmpst) > 0:
                    _tmpst.merge(method=1, fill_value=0, interpolation_samples=-1)
                    hn1_stream += _tmpst
                    hn1_bits += bit

            if hn1_bits >= required_bits:
                newst += hn1_stream
                if not colloc:
                    continue

        hh_stream = Stream()
        hh_bits = 0
        for bit, c in zip([1, 2, 4], ['HHN', 'HHE', 'HHZ']):
            _tmpst = st.select(network='NZ', station=_st.code, location='10', channel=c)
            if len(_tmpst) > 0:
                _tmpst.merge(method=1, fill_value=0, interpolation_samples=-1)
                hh_stream += _tmpst
                hh_bits += bit

        if hh_bits >= required_bits:
            newst += hh_stream
    return newst

def pad_traces(st):
    """
    Pad traces so that they all start and stop at the same time. 
    """
    tmin = UTCDateTime()
    tmax = UTCDateTime(0)
    for tr in st:
        if tr.stats.starttime < tmin:
            tmin = tr.stats.starttime
        if tr.stats.endtime > tmax:
            tmax = tr.stats.endtime
    for tr in st:
        _mn = int(tr.data.mean())
        tr.trim(tmin, tmax, pad=True, fill_value=_mn)
    return st


if __name__ == '__main__':
    parser = ArgumentParser(prog='event_inventory',
                            description=__doc__.strip())
    parser.add_argument('wfile', type=str,
                        help='Path to the event waveform file.')
    parser.add_argument('-i', '--inventory', type=str,
                        default='./data/complete.xml',
                        help='Path to the master inventory file.')
    parser.add_argument('-p', '--pad', action='store_true',
                        help="Pad traces so that start and stop times are identical")
    helpstring = 'Use all collocated sensors. Else, use only strong-motion sensors'
    parser.add_argument('-c', '--collocated', action='store_true', 
                        help=helpstring)
    helpstring = 'Include triggered sensors (i.e. HN1, HN2, HNZ).'
    parser.add_argument('-t', '--triggered', action='store_true', 
                        help=helpstring)
    args = parser.parse_args()
    invfn = args.inventory
    logging.basicConfig(stream=sys.stderr)
    logging.debug("Reading inventory file: " + invfn)
    inv = read_inventory(invfn)
    wfn = args.wfile
    if wfn == '-':
        wfn = sys.stdin.read().rstrip()
    logging.debug("Reading waveform file: " + wfn)
    st = read(wfn)
    newst = select_traces(st, inv, tc=True, colloc=args.collocated,
                          triggered=args.triggered)
    if args.pad:
        newst = pad_traces(newst)
    output = io.BytesIO()
    newst.write(output, format='MSEED')
    sys.stdout.buffer.write(output.getvalue())