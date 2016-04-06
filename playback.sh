#!/bin/bash


source ./playback.cfg
PREPARATION="false"
PLAYBACK="false"
INVENTORY="inventory.xml"
CONFIG="config.xml"
EVENTID=""
START=""
END=""
CONFIGDIR="${HOME}/.seiscomp3"
FILEIN=""
ACTION=""
MODE="historic"
DELAYS=""

function usage(){
cat <<EOF
Usage: $0 [Options] action 

Arguments:
    action          Decide what to do:
                      prep: Prepare playback files
                      pb: run playback (requires a previous 'prep')
                      all: do both in one go 
Options:
    -h              Show this message.
     --configdir     Configuration directory to use. (Default: ${HOME}/.seiscomp3).
  Event IDs:
    --evid          Give an eventID for playback.
    --fin           Give a file with one eventID per line for playback.
    
  Time window
    --start         Give the starttime of a playback time window. Note that 
                    these options are mutually exclusive with the Event ID 
                    options.
    --end           Give the endtime of a playback time window. Note that these
                    options are mutually exclusive with the Event ID options.
                    
  Playback
    --mode          Choose between 'realtime' and 'historic'. For 'realtime' the
                    records in the input file will get a new timestamp relative 
                    to the current system time at startup. For 'historic' the 
                    input records will keep their original timestamp. 
                    (Default: 'historic')
    --delaytbl      Pass the path to an ascii file containing the average delays
                    for every station in the network as well as a default delay
                    that is applied to each station that is not explicitly 
                    listed. The format of the file is as follows:
                    
                    default: 2.0
                    CH.AIGLE: 5.2
                    CH.VANNI: 3.5
                    ...
EOF
}

function processinput(){
if [ -n "$EVENTID" ]; then
	if [ -n "$START" ] || [ -n "$END" ]; then
		echo "You can only use event IDs OR time windows."
		usage
		exit 1
	fi
fi
	
if [ -z "$EVENTID" ] && [ -z "$FILEIN" ]; then
	if [ -z "$START" ] || [ -z "$END" ]; then
		echo "Either chose an event ID or a time window with start and end time."
		usage
		exit 1
	fi
fi

if [ -n "$EVENTID" ] && [ -n "$FILEIN" ]; then
	echo "Please define event IDs either in a file OR on the command line."
	usage
	exit 1
fi

if [ -z "$ACTION" ]; then
	echo "Please define an action."
	usage
	exit 1
fi

if [ -n "$DELAYTBL" ]; then
	DELAYS="-d ${DELAYTBL}"
fi

if [ -n "$FILEIN" ]; then
	index=0
	my_re="^#"
	while read line; do
		if [[ ! $line =~ $my_re ]]; then
			evids[$index]=$line
			((index++))
		fi
	done < $FILEIN
	TMP=`basename ${FILEIN}`
	PBDIR=data/${TMP%\.*}
	if [ ! -d "$PBDIR" ]; then
		mkdir -p $PBDIR
	fi
fi

if [ -n "$EVENTID" ]; then
	evids[0]=$EVENTID
	# get the last part of the event ID and use it to name the output 
	# directory
	PBDIR=data/${EVENTID##*/}
	if [ ! -d $PBDIR ]; then
		mkdir -p $PBDIR
	fi
	
fi

if [ "$MODE" != "historic" ] && [ "$MODE" != "realtime" ]; then
	echo "Playback mode has to be either 'historic' or 'realtime'."
	usage
	exit 1
fi

if [ ${ACTION} == "prep" ]; then
	PREPARATION="true"
elif [ ${ACTION} == "pb" ]; then
	PLAYBACK="true"
elif [ ${ACTION} == "all" ]; then
	PREPARATION="true"
	PLAYBACK="true"
else
	echo "action has to be one of 'prep', 'pb', 'all'"
	usage
	exit 1
fi

}

function setupdb(){
	for TMPID in ${evids[@]}; do
		EVENTNAME=${TMPID##*/}
		echo "Retrieving event information for ${TMPID} ..."
		scxmldump --debug -f -E ${TMPID} -P -A -M -F ${DBCONN} > ${EVENTNAME}.xml
	done
	echo "Retrieving inventory ..."
	scxmldump -f -I $DBCONN  > $INVENTORY
	echo "Retrieving configuration ..."
	scxmldump -f -C $DBCONN  > $CONFIG
	echo "Initializing sqlite database ..."
	if [ -f ${PBDB} ]; then
		rm ${PBDB}
	fi
	sqlite3 -batch -init $SQLITEINIT $PBDB
	echo "Populating sqlite database ..."
	scdb --plugins dbsqlite3 -d sqlite3://${PBDB} -i $INVENTORY
	scdb --plugins dbsqlite3 -d sqlite3://${PBDB} -i $CONFIG
	cp ${PBDB} ${PBDB%\.*}_no_event.sqlite 
}

if [ "$#" -gt 5 ] || [ $# -lt 3 ]; then
	echo "Too few command line arguments."
    usage
    exit 0
fi

# Processing command line options
while [ $# -gt 1 ]
do
	case "$1" in 
		--evid) EVENTID="$2";shift;;
		--start) START="$2";shift;;
		--end) END="$2";shift;;
		--configdir) CONFIGDIR="$2";shift;;
		--fin) FILEIN="$2"; shift;;
		--mode) MODE="$2"; shift;;
		--delaytbl) DELAYTBL="$2";shift;;
		-h) usage; exit 0;;
		-*) usage			
			exit 1;;
		*) break;;
	esac
	shift	
done

ACTION=$1

processinput

if [ $PREPARATION != "false" ]; then
	echo "Preparing playback files ..."
	if [ -z "$START" ]; then
		cd $PBDIR
		setupdb
		for TMPID in ${evids[@]}; do
				../../make-mseed-playback.py  -u playback -H ${HOST} ${DBCONN} -E ${TMPID} -I sdsarchive://${SDSARCHIVE}
		done
		cd -
	else
		echo "blub"
		#./make-mseed-playback.py  -u playback -H ${HOST} --plugins dbpostgresql -d postgres://${DBHOST} --debug --start 2015-03-05T20:00:00 --end 2015-03-05T20:15:00  -I sdsarchive://${SDSARCHIVE}
	fi
fi

if [ $PLAYBACK != "false" ]; then
	echo "Running playback ..."
	if [ -z "$START" ];then
		for TMPID in ${evids[@]}; do
			EVTNAME=${TMPID##*/}
			MSFILE=`ls ${PBDIR}/*${EVTNAME}*.sorted-mseed`
			EVNTFILE=`ls ${PBDIR}/*${EVTNAME}*.xml`
			./playback.py ${PBDIR}/${PBDB} ${MSFILE} ${DELAYS} -c ${CONFIGDIR} -m ${MODE} -e ${EVNTFILE} 
		done
	fi 
fi

