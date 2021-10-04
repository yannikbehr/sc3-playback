#!/usr/bin/env python
"""
Get starttime of a MiniSEED file 
"""

import seiscomp3.IO,seiscomp3.Kernel,datetime
from seiscomp3 import Config, System

def ms_starttime(filename):
    """
    Get starttime of a MiniSEED file.
    """
    stream = seiscomp3.IO.RecordStream.Open("file://" + filename)
    input = seiscomp3.IO.RecordInput(stream, seiscomp3.Core.Array.INT,
                     seiscomp3.Core.Record.SAVE_RAW)
    tmin = datetime.datetime.utcnow()
    tmax = datetime.datetime(1970, 1, 1)
    while True:
        try:
            rec = input.next()
        except:
            break
        if not rec:
            break
        te = rec.endTime().toString("%FT%T.%4fZ")
        ts = rec.startTime().toString("%FT%T.%4fZ")
        dts = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        dte = datetime.datetime.strptime(te, "%Y-%m-%dT%H:%M:%S.%fZ")
        if dte < tmin:
            tmin = dte
            Id = rec.streamID()
        if dte > tmax:
            tmax = dte
    return tmin.strftime("%Y-%m-%dT%H:%M:%S"), tmax.strftime("%Y-%m-%dT%H:%M:%S")
    
if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('filename',
                        help="Path to MiniSEED file.")
    args = parser.parse_args()
    tmin, tmax = ms_starttime(args.filename)
    print("%s %s" % (tmin, tmax))
    

