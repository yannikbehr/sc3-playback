#!/bin/bash

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 [mseed-volume] [output-xml]"
    exit 0
fi

SCPATH="/opt/seiscomp3/bin/seiscomp exec"
DBFLAG="-d mysql://sysop:sysop@localhost/seiscomp3"
STORAGE=$DBFLAG
CONFIGFLAGS="--verbosity=4"
FLAGS="$CONFIGFLAGS $STORAGE"

echo "Cleaning database"
$SCPATH scdbstrip --days 0 $FLAGS
echo "Starting scanloc..."
$SCPATH scautoloc --playback  $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &
#$SCPATH scanloc2 $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &

echo "Starting magtool..."
$SCPATH scmag $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautoloc &
echo "Starting eventtool..."
$SCPATH scevent $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scmag &
echo "Starting sceplog..."
$SCPATH sceplog $CONFIGFLAGS --auto-shutdown=1 --shutdown-master-module=scevent > $2 &
pid=$!
# Start autopick
#$SCPATH autopick2 $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &
echo "Starting autopick..."
$SCPATH scautopick -I $1 $FLAGS --playback --start-stop-msg=1 
echo "Finished waveform processing"
wait $pid
echo "Finished event processing"

