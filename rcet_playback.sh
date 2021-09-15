#!/bin/bash
DATADIR='/home/sysop/data'

function usage(){
cat <<EOF
Usage: $0 [Options] 
Run FinDer playback.

Arguments:
    Eventname
    Waveform-file
Optional Arguments:
    -h, --help              Show this message.
    --datadir               Provided alternative data directory.
EOF
}



POSITIONAL=()
# Processing command line options
while [ $# -gt 0 ]
do
	case "$1" in 
        --datadir) DATADIR="$2";shift;;
		-h) usage; exit 0;;
		-*) usage			
			exit 1;;
        *) POSITIONAL+=("$1");;
	esac
	shift	
done

# Set positional parameters to the contents of POSITIONAL
set -- "${POSITIONAL[@]}" 

if [ $# -ne 2 ]; then
    usage
    exit 1
fi

EVENT=$1
WAVEFORMS=$2

PBDIR="${DATADIR}/${EVENT}"
DBNAME="${EVENT}.sqlite3"
cd $PBDIR

STARTTIME=$(/usr/bin/python /home/sysop/sc3-playback/ms_starttime.py ${WAVEFORMS})
/opt/seiscomp3/share/FinDer/finder_file/finder_run /home/sysop/data/finder_geonet_calcmask.config /home/sysop/data 0 0 no > finder_output.log
cp /home/sysop/data/seedlink.ini /opt/seiscomp3/var/lib/seedlink/ 
/usr/bin/python /home/sysop/sc3-playback/make-mseed-playback.py -u playback -I file://${WAVEFORMS} --plugins dbsqlite3 \
-d sqlite3://${DBNAME} --start "${STARTTIME}" --end "2010-09-03T17:30:00"
MSFILE=`ls *sorted-mseed|head -1`
#seiscomp enable seedlink scfinder
seiscomp enable seedlink
/usr/bin/python /home/sysop/sc3-playback/playback.py ${DBNAME} ${MSFILE} -m realtime -c dot_seiscomp3

