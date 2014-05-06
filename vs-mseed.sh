#!/bin/bash
###############################################################################
# Generate a multiplexed MiniSEED file for direct playback from records       #
# downloaded from an arclink server.                                          #
# This script depends on the programs 'arclink_fetch', 'msrepack' and         #
# 'scmssort' of which the two latter ones are not part of SeisComp3's         #
# Zurich release.                                                             #
# For msrepack you need to download the libmseed package from IRIS,           #
# unpack it and compile the programs in the 'example' subdirectory. Then you  #
# need to make sure that 'msrepack' is on your PATH or change this script     #
# accordingly.                                                                #
# The program 'scmssort' is part of SeisComp3's Seattle release. If you       #
# haven't installed Seattle yet, we are happy to send you a version of        #
# 'scmssort', however without any further support.                            #
#                                                                             #
# Y. Behr 2/2013                                                              #
# updated: Y. Behr 5/2014
###############################################################################

#################### PARAMETERS ##########################
REQUEST=request.txt
MSEEDFILE=${HOME}/out.mseed
TMP=tmp.mseed
USER='user@provider.com'
TIMEOUT=3600
##########################################################

function usage(){
cat <<EOF
Usage: $0 [Options] tstart tend network station channel arclink-server

Arguments:
     tstart           Start time of the request of the form: year,month,day,hour,minute,second
                      e.g. 2012,02,11,22,43,26
     tend             End time of the request in the same format as tstart
     network          Network ID (wildcards allowed)
     station          Station ID (wildcards allowed)
     channel          Channel ID (wildcards allowed)
     arclink-server   URL and port of the arclink server, e.g. arclink.ethz.ch:18002

Options:
     -o               Output filename
     --user           Username used to connect to the arclink server.
     --timeout        Timeout for the arclink request. Default is set to 3600

Example: Getting all HHZ channel data for the Ml 4.2 event in Zug/Switzerland 2012

$0 --user user@provider.com -o test.mseed  2012,02,11,22,43,26 2012,02,11,22,48,26 CH "*" "HHZ" arclink.ethz.ch:18002

EOF
}

function finalmessage(){
cat <<EOF

You can verify your waveform file by running the following command:

msrtsimul -c -m 'realtime' $1 |scrttv --inventory-db=./your-sc3-inventory.xml --config-db=./your-sc3-config.xml -I -

EOF
}

if [ "$#" -lt 6 ]; then
    usage
    exit 0
fi

# Processing command line options
while [ $# -gt 0 ]
do
	case "$1" in 
		--user) USER="$2";shift;;
		-o) MSEEDFILE="$2";shift;;
		--timeout) TIMEOUT="$2";shift;;
		-h) usage; exit 0;;
		-*) usage; exit 1;;
		*) break;;
	esac
	shift	
done

if [ "$#" -ne 6 ]; then
    usage
    exit 0
fi

TSTART=$1
TEND=$2
NETWORK=$3
STATION=$4
CHANNEL=$5
ARCLINK=$6

# This example requests all channels starting with H 
# from all stations in the network CH
# see arclink_fetch -h for more help
cat << EOF > $REQUEST
${TSTART} ${TEND} ${NETWORK} ${STATION} ${CHANNEL}
EOF

if [ -e $MSEEDFILE ]; then rm -v $MSEEDFILE; fi

arclink_fetch -q -a $ARCLINK -t $TIMEOUT -u $USER -o $MSEEDFILE $REQUEST
if [ ! -e $MSEEDFILE ]; then
	echo "arclink_fetch did not generate any output"
	exit 1
fi

NEWMSEEDFILE=${MSEEDFILE}.sorted
if [ -e $NEWMSEEDFILE ]; then rm -v  $NEWMSEEDFILE; fi

# If your arclink server stores MiniSEED records with a
# record length of 4096 Byte they need to be repacked
# to a record length of 512 Byte
msrepack -a -R 512 -o $TMP $MSEEDFILE

# Sort records with respect to their end-time.
scmssort -E $TMP > ${NEWMSEEDFILE}

finalmessage ${NEWMSEEDFILE}

# cleanup temporary file and request file	
if [ -e $REQUEST ]; then rm -v $REQUEST; fi
if [ -e $TMP ]; then rm -v $TMP; fi
