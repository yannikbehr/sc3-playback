#!/bin/bash
#######################################################
# Setup an SeisComP3 SQLite database for playback.    #
# This will only setup bindings and station meta data #
# for the stations in the playback file               #
#######################################################


IMAGE=finder_rcet
TAG=0.0.1
DATADIR='/home/sysop/data'
VERBOSITY=2

function usage(){
cat <<EOF
Usage: $0 [Options] 
Setup an SeisComP3 SQLite database for playback.

Arguments:
    Eventname
    InventoryFile
    BindingsDir
Optional Arguments:
    -h, --help              Show this message.
    --image                 Provide alternative image name.
    --tag                   Provide alternative image tag.
    --datadir               Provided alternative data directory.
EOF
}


POSITIONAL=()
# Processing command line options
while [ $# -gt 0 ]
do
    case "$1" in
        --image) IMAGE="$2";shift;;
        --tag) TAG="$2";shift;;
        --datadir) DATADIR="$2";shift;;
        -h) usage; exit 0;;
        -*) usage; exit 1;;
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
EVENT=$1 
INVENTORYXML=$2
BINDINGSDIR=$3
INVENTORYSC3="${DATADIR}/${EVENT}/${EVENT}_inventory.sc3ml"
CONFIG="${DATADIR}/${EVENT}/${EVENT}_config.sc3ml"
DBNAME="${DATADIR}/${EVENT}/${EVENT}.sqlite3"

alias DOCKERCMD='docker run --rm -v $PWD/data:/home/sysop/data \
    -v $PWD/dot_seiscomp3:/home/sysop/.seiscomp3 \
    --log-driver=none -a stdout \
    ${IMAGE}:${TAG} bash -c'

fdsnxml2inv --verbosity ${VERBOSITY} -f ${INVENTORYXML} > ${INVENTORYSC3}
bindings2cfg --verbosity ${VERBOSITY} --key-dir ${BINDINGSDIR} -o $CONFIG
echo "Initializing sqlite database ..."
sqlite3 -batch -init /opt/seiscomp3/share/db/sqlite3.sql ${DBNAME} ".exit"
echo "Populating sqlite database ..."
scdb --verbosity 4 --plugins dbsqlite3 -d sqlite3://${DBNAME} -i $INVENTORYSC3
scdb --verbosity ${VERBOSITY} --plugins dbsqlite3 -d sqlite3://${DBNAME} -i $CONFIG
