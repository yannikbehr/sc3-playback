#!/bin/bash
DATADIR=""

function usage(){
cat <<EOF
Usage: $0 [Options] 
Run FinDer playback.

Arguments:
    Waveform-file
    Database-file 
    Config-dir
Optional Arguments:
    -h, --help              Show this message.
    --datadir               Provide alternative data directory.
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

if [ $# -ne 3 ]; then
    usage
    exit 1
fi

WAVEFORMS=$1
DATABASE=$2
CONFIGDIR=$3

if [ -z $DATADIR ];then
    DATADIR=$(dirname ${DATABASE})
fi
cd $DATADIR

TIMES=($(/usr/bin/python /home/sysop/sc3-playback/ms_starttime.py ${WAVEFORMS}))
STARTTIME=${TIMES[0]}
ENDTIME=${TIMES[1]}
/opt/seiscomp3/share/FinDer/finder_file/finder_run ${CONFIGDIR}/finder_geonet_calcmask.config ${CONFIGDIR} 0 0 no > finder_output.log
cp ${CONFIGDIR}/seedlink.ini /opt/seiscomp3/var/lib/seedlink/ 
/usr/bin/python /home/sysop/sc3-playback/make-mseed-playback.py -u playback -I file://${WAVEFORMS} --plugins dbsqlite3 \
-d sqlite3://${DATABASE} --start "${STARTTIME}" --end "${ENDTIME}"
MSFILE=`ls *sorted-mseed|head -1`
seiscomp enable seedlink scfinder
#seiscomp enable seedlink
/usr/bin/python /home/sysop/sc3-playback/playback.py ${DATABASE} ${MSFILE} -m realtime -c ${CONFIGDIR}