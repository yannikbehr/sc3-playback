#!/bin/bash
#####################################################################
# Playback script to test VS magnitude estimates in SeisComp3.
#
# The script will start all necessary SeisComp3 modules, including 
# the logging programs, to generate VS magnitude estimates from a 
# given sorted and multiplexed MiniSEED file. 
# Y.Behr 2/13
# adapted to run in seiscomp3-seattle 1/14
#####################################################################

# processes to be stopped with playback.sh --stop
stopprocs="scenvelope scautoloc sceventvs msrtsimul scrttv scautopick"

function killer(){
    echo "stopping all processes from this script"
    echo "($stopprocs)"
    killall $stopprocs 2>/dev/null
    sleep 1
    killall -9 $stopprocs 2>/dev/null
}

function sc3status(){
    spreadstatus=`ps -u $USER -o args|grep ^spread|wc -l`
    if [ $spreadstatus -lt 1 ]; then
        echo "spread is not running"
        exit 1
    fi
    masterstatus=`ps -u $USER -o args|grep ^scmaster|wc -l`
    if [ $spreadstatus -lt 1 ]; then
        echo "scmaster is not running"
        exit 1
    fi
}

function usage(){
cat <<EOF
Usage: $0 [Options] input-file

Options:
    -h              Show this message.
    --db-disable    Do not use a database. This requires a valid inventory
                    and configuration xml file to be present in the current
                    working directory. [default names: 'inventory.xml', 'config.xml']
    --console       Print log messages to stdout.
    --mode          Choose the playback mode. Can be either 'realtime' 'historic' or 'fast'.
                    'realtime': The records in the input file will get a new 
                                timestamp relative to the current system time. 
                                Records are sent to SeisComp3's SeedLink server 
                                which therefore has to have the mseedfifo plugin enabled.
                    'historic': The input records will keep their original timestamp 
                                and are directly sent to downstream processing 
                                modules, bypassing the SeedLink server. A fully 
                                configured SeedLink server is therefore not 
                                required for this type of playback. [default]
                    'fast'    : This type of playback is mainly intended for 
                                debugging purposes. The MiniSEED file is played
                                back as fast as it can be read. This can lead to
                                artifacts in the VS magnitude results since some
                                modules will finish processing before others.
    --skip          In modes 'realtime' and 'historic' you can skip a given number
                    of minutes from the beginning of the records. Argument can be 
                    any integer number that is less than the length of the input records.
    --scrttv        In mode 'historic' this will start scrttv so that the waveforms can
                    be observed as they are coming in. This option requires a date
                    in the format "2012-01-28 16:01:00" which marks the end of the 
                    viewing window of scrttv.
    --reports       Path to a directory where playback log-files are written to.
    --stop          Stop all processes started by $0
    --logenv        Log envelope values.
    --delaytbl      Pass the path to an ascii file containing the average delays for every 
                    station in the network as well as a default delay that is applied to 
                    each station that is not explicitly listed. The format of the file 
                    is as follows:
                    
                    default: 2.0
                    CH.AIGLE: 5.2
                    CH.VANNI: 3.5
                    ...
                    
EOF
}

if [ "$#" -gt 13 ]; then
    usage
    exit 0
fi

# Check whether spread and scmaster are running
sc3status

# Set default values
DBFLAG=""
STORAGE=$DBFLAG
CONSOLE="--console=0"
SKIP=0
MODE="historic"
WAVEFORMS="false"
LOGFILE=output.xml
INVENTORY="./inventory_seattle.xml"
CONFIG="./config_seattle.xml"
REPORTDIR="./"
LOGENV=false
DELAYS=""

# Processing command line options
while [ $# -gt 0 ]
do
	case "$1" in 
		--console) CONSOLE="--console=1";;
		--mode) MODE="$2";shift;;
		--scrttv) WAVEFORMS="$2";shift;;
		--db-disable) STORAGE="--inventory-db=${INVENTORY} --config-db=${CONFIG}";;
		--skip) SKIP="$2";shift;;
		--stop) killer; exit 0;;
		--reports) REPORTDIR="$2";shift;;
		--logenv) LOGENV=true;;
		--delaytbl) DELAYS="-d $2";shift;;
		-h) usage; exit 0;;
		-*) usage			
			exit 1;;
		*) break;;
	esac
	shift	
done
MSEEDFILE=$1
FILETYPE=`echo ${MSEEDFILE} |cut -d: -f1`
FLAGS=" --verbosity=4 $CONSOLE $STORAGE"

# Check command line arguments
if [ "$FILETYPE" == "arclink"  ] || [ "$FILETYPE" == "slink" ]; then
	echo "Currently only MiniSEED files can be used as input."
	exit 1  
fi

################ Processing #############################

# react to signals like Ctrl-c by calling the killer function
trap killer SIGHUP SIGINT SIGTERM

# Start the VS magnitude tool
echo "Starting VS magnitude tool..."
if $LOGENV; then
	FLAGS="$FLAGS --envelope-log"
fi
echo $FLAGS

case "$MODE" in
	realtime) scvsmag $FLAGS --auto-shutdown=1  --processing-log ./scvsmag-processing-info.log\
				--shutdown-master-module=scenvelope --start-stop-msg=1&
				;;
	historic) scvsmag $FLAGS --auto-shutdown=1 --processing-log ./scvsmag-processing-info.log\
				--shutdown-master-module=scenvelope --playback --start-stop-msg=1&
				;;
	fast) scvsmag $FLAGS --auto-shutdown=1 --processing-log ./scvsmag-processing-info.log\
				--shutdown-master-module=scenvelope --playback --timeref ot --start-stop-msg=1&
				;;
esac

echo "Starting logging..."
sceplog -S EVENT -S LOCATION -S MAGNITUDE -S PICK  > $LOGFILE \
--auto-shutdown=1 --shutdown-master-module=scvsmag&
scvsmaglog --playback --auto-shutdown=1 --shutdown-master-module=scvsmag --savedir=$REPORTDIR &


echo "Starting envelope processing..."
case "$MODE" in 
	realtime) echo "running real-time playback"
			if [ "$WAVEFORMS" == "false" ]; then
				msrtsimul -c -m realtime -j $SKIP $DELAYS ${MSEEDFILE}\
				|scenvelope $FLAGS --start-stop-msg=1 -I - &
				pid_env=$!
			else
				msrtsimul -c -m realtime -j $SKIP $DELAYS ${MSEEDFILE}|\
				tee >(scenvelope $FLAGS --start-stop-msg=1 -I -) |\
				scrttv $FLAGS -S PICK -S LOCATION --plugins dmvs -N --auto-shutdown=1 \
				--shutdown-master-module=scenvelope -I - &
				pid_env=$!
			fi
			 ;;
	historic) echo "running historic playback"
			if [ "$WAVEFORMS" == "false" ]; then
				msrtsimul -c -m historic -j $SKIP $DELAYS ${MSEEDFILE}\
				|scenvelope $FLAGS --start-stop-msg=1 -I - &
				pid_env=$!
			else
				msrtsimul -c -m historic -j $SKIP $DELAYS ${MSEEDFILE}|\
				tee >(scenvelope $FLAGS --start-stop-msg=1 -I -) |\
				scrttv $FLAGS -S VS --plugins dmvs --end-time "$WAVEFORMS" -N --auto-shutdown=1 \
				--shutdown-master-module=scenvelope -I - &
				pid_env=$!
			fi
			 ;;
	fast) echo "running fast playback"
		scenvelope $FLAGS -I ${MSEEDFILE} --start-stop-msg=1&
		pid_env=$!
esac

echo "Starting the associator..."
scautoloc $FLAGS --playback --start-stop-msg=1 --auto-shutdown=1 \
--shutdown-master-module=scautopick &
echo "Starting the event tool..."
scevent --verbosity=4 --db-disable --start-stop-msg=1 --auto-shutdown=1 \
--shutdown-master-module=scenvelope &
pid_event=$!

echo "Starting picking..."
case "$MODE" in 
	realtime) msrtsimul -c -m realtime -j $SKIP $DELAYS ${MSEEDFILE}| scautopick $FLAGS --start-stop-msg=1 -u yb -I - ;;
	historic) msrtsimul -c -m historic -j $SKIP $DELAYS ${MSEEDFILE}| scautopick $FLAGS --start-stop-msg=1 -u yb -I - ;;
	fast) scautopick $FLAGS --start-stop-msg=1 -u yb -I ${MSEEDFILE}
esac

echo "Finished waveform processing"
wait $pid_event
echo "Finished event processing"
wait $pid_env
echo "Finished envelope processing"
