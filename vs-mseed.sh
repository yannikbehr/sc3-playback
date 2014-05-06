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
# You will also need to adapt the parameters in the next section to your own  #
# environment/liking.                                                         #
# With SeisComp3's tools 'msrtsimul' and 'scrttv' you can ensure that the     #
# generated file has the correct format.                                      #
# 1.) replay the file with 'msrtsimul -v your_sorted.mseed'                   #
# 2.) check in scrttv that records are coming in                              #
# Note: Using scrttv with msrtsimul requires a seedlink server running with   #
# the mseed_fifo plugin.                                                      #
#                                                                             #
# Y. Behr 2/2013                                                              #
###############################################################################

#################### PARAMETERS ##########################
REQUEST=request.txt
MSEEDFILE=${HOME}/VS_test_data/Zug.mseed
TMP=tmp.mseed
USER='behry@sed.ethz.ch'
ARCLINK=arclink.ethz.ch:18002
TIMEOUT=3600
##########################################################

# This example requests all channels starting with H 
# from all stations in the network CH
# see arclink_fetch -h for more help
cat << EOF > $REQUEST
2012,02,11,22,43,26 2012,02,11,22,48,26 CH * H*
EOF

if [ -e $MSEEDFILE ]; then rm -v $MSEEDFILE; fi

arclink_fetch -a $ARCLINK -t $TIMEOUT -u $USER -o $MSEEDFILE $REQUEST
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
./scmssort -E $TMP > ${NEWMSEEDFILE}

# cleanup temporary file and request file	
if [ -e $REQUEST ]; then rm -v $REQUEST; fi
if [ -e $TMP ]; then rm -v $TMP; fi
