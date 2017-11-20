#!/bin/bash

#
# Run as: seiscomp exec offline-playback.sh [mseed-volume] [output-xml]
#

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 [mseed-volume] [output-xml]"
    exit 0
fi

#
# Optionally use a different database than what is already configured in seiscomp installation
#
#DBFLAG="-d mysql://user:password@host/database"
#DBFLAG="--plugins dbpostgresql -d postgresql://user:password@host/database"
#DBFLAG="--plugins dbsqlite3 -d sqlite3:///home/sysop/sc3_db.sqlite"

STORAGE=$DBFLAG
CONFIGFLAGS="--verbosity=4 " #--console=1" 
FLAGS="$CONFIGFLAGS $STORAGE"

echo "Cleaning database"
scdbstrip --days 0 $FLAGS

echo "Starting scanloc..."
scautoloc --playback  $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &

# Optional second pipeline (scautoloc2)
#scautoloc2 $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &

echo "Starting magtool..."
scmag $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautoloc &
echo "Starting eventtool..."
scevent $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scmag &
echo "Starting sceplog..."
sceplog $CONFIGFLAGS --auto-shutdown=1 --shutdown-master-module=scevent > $2 &
pid=$!

echo "Starting autopick..."
# Optional second pipeline (scautopick2)
#scautopick2 $FLAGS --start-stop-msg=1 --auto-shutdown=1 --shutdown-master-module=scautopick &
scautopick -I $1 $FLAGS --playback --start-stop-msg=1

echo "Finished waveform processing"
wait $pid
echo "Finished event processing"
