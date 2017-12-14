#!/bin/bash

PLAYBACKROOT="$( dirname "$( readlink -f "$0")")/"
MAKEMSEEDPLAYBACK="${PLAYBACKROOT}/make-mseed-playback.py"
RUNPLAYBACK="${PLAYBACKROOT}/playback.py"
PLAYBACKDATA="${PLAYBACKROOT}/data"
PREPARATION="false"
FIX="false"
FIXHOST="false"
FIXCLIENT="false"
PLAYBACK="false"
INVENTORY="inventory.xml"
CONFIG="config.xml"
CONFIGDIR="${HOME}/.seiscomp3"
EVENTID=""
BEGIN=""
END=""
FILEIN=""
ACTION=""
MODE="historic"
DELAYS=""
MSVIEW=$HOME"/git/libmseed-2.18/example/msview"

function loadsconf(){
    if [ -f "$CONFIGFILE" ]
    then 
        echo Loading $CONFIGFILE ...
        source "$CONFIGFILE" || (echo Can t load configuration in $CONFIGFILE && exit 1)
    fi
}

function usage(){
cat <<EOF
Usage: $0 [Options] action 

Arguments:
    action          Decide what to do:
                      prep: Prepare playback files
		      pb: run playback (requires a previous 'prep')
                      all: do both in one go 
		      fixhost: fix all missing bindings in the msrtsimul configuration
			for stations in a given inventory (see option --inventory-file)
                      fixhost: fix all missing bindings in the seiscomp configuration
			for stations in a given inventory (see option --inventory-file)                     
Options:
    -h              Show this message.
    --config-file   Use alternative playback configuration file. If none
                    given follows default loading order:
                        1- $SEISCOMPROOT/etc/playback.cfg
                        2- ~/.seiscomp3/playback.cfg (prevails previous)
                        3- ./playback.cfg (prevails all previous)
    --configdir     SeisComP3 configuration directory to use. (Default: 
                    ${HOME}/.seiscomp3).
    --inventory-file Inventory file to use when fixing missing bindings.
		    All the stations from this file will be playedback and 
                    binded (global and scautopick). The inv2imp*.$INVENTORYFORMAT files
                    in playback directory will be used by default if found.
    --inventory-format format of inventory file. Default is fdsnxml.

  Event IDs:
    --evid          Give an eventID for playback.
    --fin           Give a file with one eventID per line for playback.
    --tin           Give a file with one origin time per line for playback.
    
  Time window
    --begin         Give the starttime of a playback time window. Note that 
                    these options are mutually exclusive with the Event ID 
                    options.
    --end           Give the endtime of a playback time window. Note that these
                    options are mutually exclusive with the Event ID options.
                    
  Playback
    --mode          Choose between 'realtime', 'historic' and 'offline'. For 'realtime' 
		    the records in the input file will get a new timestamp relative 
                    to the current system time at startup. For 'historic' the 
                    input records will keep their original timestamp. For 'offline'
                    each enabled module is ran with their builtin parametric playback
		    as fast as possible, not respecting the timestamp of records.  
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
if [ -n "$EVENTID" ] && [ $EVENTID != "none" ] ; then
	if [ -n "$BEGIN" ] || [ -n "$END" ]; then
		echo "You can only use event IDs OR time windows."
		usage
		exit 1
	fi
fi
	
if [ -z "$EVENTID" ] && [ -z "$FILEIN" ]; then
	if [ -z "$BEGIN" ] || [ -z "$END" ]; then
		echo "Either chose an event ID or a time window with start and end time."
		usage
		exit 1
	fi
fi

if [ -n "$EVENTID" ] && [ -n "$FILEIN" ] && [ $EVENTID != "none" ] ; then
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
	PBDIR=${PLAYBACKDATA}/${TMP%\.*}
	if [ ! -d "$PBDIR" ]; then
		mkdir -p "$PBDIR"
	fi
fi

if [ -n "$TIMEIN" ]; then
        index=0
        my_re="....-..-..T..:..:...*"
        while read line; do
                if [[ ! $line =~ $my_re ]]; then
                        evots[$index]=$line
                        ((index++))
                fi
        done < $TIMEIN
        TMP=`basename ${TIMEIN}`
        PBDIR=${PLAYBACKDATA}/${TMP%\.*}a
	echo this is not yet ready
	exit 1
        if [ ! -d "$PBDIR" ]; then
                mkdir -p "$PBDIR"
        fi
	
fi

if [ -n "$EVENTID" ] ; then
	evids[0]=$EVENTID
	# get the last part of the event ID and use it to name the output 
	# directory
	PBDIR=${PLAYBACKDATA}/${EVENTID##*/}
	if [ ! -d "$PBDIR" ]; then
		mkdir -p "$PBDIR"
	fi
	
fi

if [ -n "$BEGIN" ] && [ -n "$END" ]; then
	
	evids=()
	evids=( $( seiscomp exec scevtls  ${DBCONN}  --begin "$BEGIN"  --end "$END" ) )
	echo ${#evids[@]} "events in requested time span (from "$BEGIN" to "$END")"	
	
	PBDIR=${PLAYBACKDATA}/${BEGIN//[!0-9]/}-${END//[!0-9]/}
    #_${#evids[@]}_events  
	if [ ! -d "$PBDIR" ]; then
		mkdir -p "$PBDIR"
	fi	
	echo "data files in " $PBDIR 
	
fi

if [ "$MODE" != "historic" ] && [ "$MODE" != "realtime" ] && [ "$MODE" != "offline" ]; then
	echo "Playback mode has to be either 'historic' or 'realtime' or 'offline."
	usage
	exit 1
fi

if [ "$MODE" == "offline" ] && [ "$1" == "pb"] ; then
	echo Offline playback not yet implemented
	usage
	exit 1
fi

if [ ${ACTION} == "prep" ]; then
	PREPARATION="true"
elif [ ${ACTION} == "pb" ]; then
	PLAYBACK="true"
elif [ ${ACTION} == "fix" ]; then
	FIX="true"
elif [ ${ACTION} == "fixhost" ]; then
        FIXHOST="true"
elif [ ${ACTION} == "fixclient" ]; then
        FIXHOST="true"
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
	if [ -n "$FILEIN" ] ||  [ -n "$EVENTID" ] ; then
		for TMPID in ${evids[@]}; do
			EVENTNAME=${TMPID##*/}
			echo "Retrieving event information for ${TMPID} ..."
			scxmldump --debug -f -E ${TMPID} -P -A -M -F ${DBCONN} > ${EVENTNAME}.xml
		done
	else
		EVENTNAME=${#evids[@]}_events 
		EVENTSIDLIST=""
		for TMPID in ${evids[@]}; do
			EVENTSIDLIST=$EVENTSIDLIST,$TMPID
		done
		echo "Retrieving event information for ${EVENTNAME} ..."
		echo scxmldump --debug -f -E "${EVENTSIDLIST}" -P -A -M -F ${DBCONN}
		scxmldump --debug -f -E "${EVENTSIDLIST}" -P -A -M -F ${DBCONN} > ${EVENTNAME}.xml
	fi
	echo "Retrieving inventory ..."
	scxmldump -f -I $DBCONN  > $INVENTORY
	echo "Retrieving configuration ..."
	scxmldump -f -C $DBCONN  > $CONFIG
	echo "Initializing sqlite database ..."
	if [ -f "${PBDB}" ]; then
		rm "${PBDB}"
	fi
	sqlite3 -batch -init "$SQLITEINIT" "$PBDB" .exit
   	echo "Populating sqlite database ..."
	scdb --plugins dbsqlite3 -d "sqlite3://${PBDB}" -i $INVENTORY
	scdb --plugins dbsqlite3 -d "sqlite3://${PBDB}" -i $CONFIG
	cp "${PBDB}" "${PBDB%\.*}_no_event.sqlite" 
}

if [ "$#" -gt 15 ] || [ $# -lt 3 ]; then
	echo "Too few command line arguments."
    usage
    exit 0
fi

# Processing command line options
while [ $# -gt 1 ]
do
	case "$1" in 
		--evid) EVENTID="$2";shift;;
		--begin) BEGIN="$2";shift;;
		--end) END="$2";shift;;
		--configdir) CONFIGDIR="$2";shift;;
		--fin) FILEIN="$2"; shift;;
		--tin) TIMEIN="$2"; shift;;
		--config-file) CONFIGFILE="$2";shift;;
		--inventory-file) INVENTORYFILE="$2";shift;;
                --inventory-format) INVENTORYFORMAT="$2";shift;;
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

if [ -f "$CONFIGFILE" ] ; then
	loadsconf
else
	# loading order 
	#CONFIGFILE="${PLAYBACKROOT}playback.cfg" # deepest but does not prevails over the over
	#loadsconf
	CONFIGFILE="${SEISCOMP_ROOT}/etc/playback.cfg" # deepest but does not prevails over the over 
	loadsconf
	CONFIGFILE="${HOME}/.seiscomp3/playback.cfg" # prevails over the previous
	loadsconf
	CONFIGFILE="./playback.cfg" #  prevails over all the overs
	loadsconf
fi

processinput
if [ ! -f "$MAKEMSEEDPLAYBACK" ] || [ ! -f "$RUNPLAYBACK" ]; then
	echo "You need the following dependencies:" 
	echo $MAKEMSEEDPLAYBACK 
	echo $RUNPLAYBACK
	exit 1
fi

if [ $PREPARATION != "false" ]
then
	echo "Preparing playback files ..."
	cd "$PBDIR"
	if [ "$MODE" != "offline" ]
	then
		setupdb
	fi
	
	${SEISCOMP_ROOT}/bin/seiscomp check spread
	# if no event requested, then one miniseed file for whole time span 
	if [ -z "$EVENTID" ] && [ -z "$FILEIN" ] 
	then
        	"$MAKEMSEEDPLAYBACK"  -u playback -H ${HOST} ${DBCONN} --debug --start ${BEGIN/ /T} --end ${END/ /T}  -I "${RECORDURL}"
		echo "Examine data with:"
		echo "scrttv --debug --offline --record-file ${PBDIR}/*sorted-mseed"
	
	# otherwise process requested events individually 
	else 
		for TMPID in ${evids[@]}
		do
			"$MAKEMSEEDPLAYBACK"  -u playback -H ${HOST} ${DBCONN} -E ${TMPID} -I "${RECORDURL}" 
			#"sdsarchive://${SDSARCHIVE}"
			echo "Examine data with:"
			echo "scrttv --debug --offline --record-file \"${PBDIR}/${TMPID}\"*.sorted-mseed"
		done
	fi
	cd -
fi

if [ $FIXHOST != "false" ]
then
	MSFILE=`ls "${PBDIR}"/*sorted-mseed|head -1`
	if [ -z "$INVENTORYFORMAT" ]
	then
		INVENTORYFORMAT="fdsnxml"
	fi
	if [ -z "$INVENTORYFILE" ]
	then
		INVENTORYFILE=$PBDIR"/inv2imp*."$INVENTORYFORMAT
	fi
	echo Fixing with $INVENTORYFILE \($INVENTORYFORMAT format and extension required\)
	echo and with $MSFILE
	echo "Fixing the host (or mseedfifo) database... (import all stations, bind all best components)"
	rm ${SEISCOMP_ROOT}/etc/inventory/*xml
	ls ${INVENTORYFILE}| while read F
	do
		seiscomp exec import_inv $INVENTORYFORMAT $F
	done

	ls ${SEISCOMP_ROOT}/etc/key/seedlink/profile_pb || echo WARNING : MAKE A seedlink:pb PROFILE !!!! 
	$MSVIEW $MSFILE |awk '{print $1}'|sort|uniq|grep ${CHANNEL}${ORIENTATION}|awk -F"[,_]" '{print $1,$2,$4,$3}'|while read N S C L
	do
		if grep -q "seedlink" ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
		then
			sed -i 's/seedlink.*/seedlink:pb/' ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
			echo OK binding seedlink:pb for ${N}_${S} \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)	
		else
			echo Adds binding seedlink:pb for ${N}_${S} \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)
			echo "seedlink:pb" >> ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
		fi
	done
	seiscomp update-config
fi
if [ $FIXCLIENT != "false" ]
then

        MSFILE=`ls "${PBDIR}"/*sorted-mseed|head -1`
        if [ -z "$INVENTORYFORMAT" ]
        then
                INVENTORYFORMAT="fdsnxml"
        fi
        if [ -z "$INVENTORYFILE" ]
        then
                INVENTORYFILE=$PBDIR"/inv2imp*."$INVENTORYFORMAT
        fi
        echo Fixing with $INVENTORYFILE \($INVENTORYFORMAT format and extension required\)
	echo and with $MSFILE
	rm ${SEISCOMP_ROOT}/etc/inventory/*xml

	echo "Fixing the client (or processing) database... (clear blacklist, import all stations, bind all best components)"
	cp $HOME/.seiscomp3/global.cfg $HOME/.seiscomp3/globalclient.cfg
	echo "database.type = sqlite3" >> $HOME/.seiscomp3/globalclient.cfg 
	echo "database.parameters = $HOME/test_db_no_event.sqlite" >> $HOME/.seiscomp3/globalclient.cfg
	echo "plugins.dbPlugin.dbDriver = sqlite3" >> ~/.seiscomp3/globalclient.cfg
	echo "plugins.dbPlugin.readConnection = $HOME/test_db_no_event.sqlite" >> $HOME/.seiscomp3/globalclient.cfg
	echo "plugins.dbPlugin.writeConnection = $HOME/test_db_no_event.sqlite" >> $HOME/.seiscomp3/globalclient.cfg
	cp ${PBDIR}/test_db_no_event.sqlite $HOME/test_db_no_event.sqlite
	
	cp $HOME/.seiscomp3/global.cfg $HOME/.seiscomp3/global.cfg.bu || exit 1 && cp $HOME/.seiscomp3/globalclient.cfg $HOME/.seiscomp3/global.cfg
	seiscomp restart spread scmaster

	ls ${INVENTORYFILE}| while read F
	do
		seiscomp exec import_inv $INVENTORYFORMAT $F
	done

	for ORIENTATION in "0," "3," "V," "Z,"
	do
		for CHANNEL in "_BH" "_SH" "_HN" "_EH" "_HH"
		do 
			$MSVIEW $MSFILE |awk '{print $1}'|sort|uniq|grep ${CHANNEL}${ORIENTATION}|awk -F"[,_]" '{print $1,$2,$4,$3}'|while read N S C L 
			do
				LCODE=$L
				if [ -z "$L" ]; then
					LCODE="\"\""
				fi
				echo $N $S $C $L $LCODE

				ls ${SEISCOMP_ROOT}/etc/key/scautopick/profile_Local || echo WARNING : MAKE A scautopick:Local PROFILE !!!!
				if grep -q "scautopick" ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} 
				then
					echo OK binding scautopick:\* for ${N}_${S} \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)
				else
					echo Adds binding scautopick:Local for ${N}_${S} \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)
					echo "scautopick:Local" >> ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
				fi

				PROFILE="auto"${C}${L}
				while read F
				do
					if grep -q "detecStream = $C" $F
					then
						if grep -q "detecLocid = $LCODE" $F
						then
							PROFILE=${F/*_}
							echo OK profile global:${PROFILE}: detecStream = $C and detecLocid = $LCODE \( $F \)
							break
						elif [ -z "$L" ] &&   ! grep -q "detecLocid" $F 
						then
							PROFILE=${F/*_}
							echo OK profile global:${PROFILE}: detecStream = $C  \( $F \) 
							break
						fi
					fi
				done < <( ls ${SEISCOMP_ROOT}/etc/key/global/profile_* )
				echo $PROFILE	
				if [ -f ${SEISCOMP_ROOT}/etc/key/global/profile_${PROFILE} ] 
				then
					echo OK profile global:${PROFILE} \( ${SEISCOMP_ROOT}/etc/key/global/profile_${PROFILE} \)
				else
					echo Adds profile global:${PROFILE} \( ${SEISCOMP_ROOT}/etc/key/global/profile_${PROFILE} \)
					echo "detecLocid = $LCODE" >> ${SEISCOMP_ROOT}/etc/key/global/profile_${PROFILE}
					echo "detecStream = $C" >> ${SEISCOMP_ROOT}/etc/key/global/profile_${PROFILE}
				fi
	
				if grep -q "global" ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} 
				then
					echo OK binding global:${PROFILE} for ${N}_${S} \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)
					sed -i 's/global.*/global:'${PROFILE}'/' ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
				else
					echo Adds binding global:${PROFILE} for ${N}_${S}  \( ${SEISCOMP_ROOT}/etc/key/station_${N}_${S} \)
					echo "global:${PROFILE}" >> ${SEISCOMP_ROOT}/etc/key/station_${N}_${S}
				fi
			done
		done
	done
	seiscomp update-config
	cp $HOME/.seiscomp3/global.cfg.bu $HOME/.seiscomp3/global.cfg || echo WARNING !!! $HOME/.seiscomp3/global.cfg recovery failed ! Recover with: $HOME/.seiscomp3/global.cfg.bu 
	seiscomp restart spread scmaster
	cp $HOME/test_db_no_event.sqlite ${PBDIR}/test_db_no_event.sqlite  || echo WARNING !!! ${PBDIR}/test_db_no_event.sqlite recovery failed ! Recover with: $HOME/test_db_no_event.sqlite
fi

if [ $PLAYBACK != "false" ]
then
	# prepare new db
	echo "Running playback ..."
	echo cp ${PBDIR}/${PBDB%\.*}_no_event.sqlite ${PBDIR}/${PBDB}
	cp "${PBDIR}/${PBDB%\.*}_no_event.sqlite" "${PBDIR}/${PBDB}"	
	
	# make space for new logs
	mkdir -p ${PBDIR}/seiscomp3/log
	ls ${PBDIR}/seiscomp3/* &>/dev/null && rm -r ${PBDIR}/seiscomp3/*
	ls  ${CONFIGDIR}/.logbu &>/dev/null &&    mv   ${CONFIGDIR}/log/* ${CONFIGDIR}/.logbu/
	ls  ${CONFIGDIR}/.logbu &>/dev/null ||    mv   ${CONFIGDIR}/log   ${CONFIGDIR}/.logbu
	
	# make sure seedlink will work, with fifo
	seiscomp enable seedlink
	sed -i 's;plugins\.mseedfifo\.fifo.*;plugins.mseedfifo.fifo = '${SEISCOMP_ROOT}'/var/run/seedlink/mseedfifo;' ${CONFIGDIR}/global.cfg
	grep "plugins.mseedfifo.fifo" ${CONFIGDIR}/global.cfg

	# run the playback
	if [ -z "$EVENTID" ] && [ -z "$FILEIN" ]
	then	
		# continuous data 
		MSFILE=`ls "${PBDIR}"/*sorted-mseed|head -1`
        	EVNTFILE=`ls "${PBDIR}"/*_events.xml`
		"$RUNPLAYBACK"  "${PBDIR}/${PBDB}" "${MSFILE}" "${DELAYS}" -c "${CONFIGDIR}" -m ${MODE} -e "${EVNTFILE}"
	else 
		for TMPID in ${evids[@]}
		do
			# event data
			EVTNAME=${TMPID##*/}
			MSFILE=`ls "${PBDIR}/"*${EVTNAME}*.sorted-mseed|head -1`
			EVNTFILE=`ls "${PBDIR}/"*${EVTNAME}*.xml`
			"$RUNPLAYBACK"  "${PBDIR}/${PBDB}" "${MSFILE}" "${DELAYS}" -c "${CONFIGDIR}" -m ${MODE} -e "${EVNTFILE}"
		done
	
	fi
	
	# export the results
	mkdir -p ${PBDIR}/xmldump
	rm ${PBDIR}/xmldump/*.xml
	scevtls --plugins dbsqlite3 -d "sqlite3://${PBDIR}/${PBDB}" |while read E 
	do 
		scxmldump --plugins dbsqlite3 -d "sqlite3://${PBDIR}/${PBDB}" -fPAMF -E $E -o ${PBDIR}/xmldump/${E//\//_}.xml &>> ${CONFIGDIR}/log/scxmldump.logerr
	done

	# save the logs
	rsync -avzl ${CONFIGDIR}/  ${PBDIR}/seiscomp3/ --exclude="*logbu*"  &> ${PBDIR}/rsync.logerr
	ls  ${CONFIGDIR}/log/* &>/dev/null && rm -r ${CONFIGDIR}/log
	ls ${CONFIGDIR}/.logbu &>/dev/null && mv ${CONFIGDIR}/.logbu  ${CONFIGDIR}/log
	
	# print next step
	echo "Examine results with:"
	echo "scolv --offline --debug --plugins dbsqlite3 -d \"sqlite3://${PBDIR}/${PBDB}\" -I \"$MSFILE\"" 	
fi
