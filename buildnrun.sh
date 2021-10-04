#!/bin/bash

#########################################
# Build and run docker image            #
# 09/20 Y. Behr <y.behr@gns.cri.nz>     #
#########################################

# Make alias
shopt -s expand_aliases

IMAGE=finder_rcet
CONTAINER=finder_test
TAG=0.0.1
BUILD=false
PUSH=false
INTERACTIVE=false
SSHD=false
SETUP=false

function usage(){
cat <<EOF
Usage: $0 [Options] 
Build and run docker for ashfall visualisation.

Optional Arguments:
    -h, --help              Show this message.
    -b, --build             Rebuild the image.
    -i, --interactive       Start the container with a bash prompt.
    --setup                 Setup sqlite database.
    --sshd                  Start the container with an ssh server.
    --image                 Provide alternative image name.
    --tag                   Provide alternative tag
    --push                  Push to registry. Note: the registry
                            has to be part of the image name
EOF
}

# Processing command line options
while [ $# -gt 0 ]
do
    case "$1" in
        -b | --build) BUILD=true;;
        -i | --interactive) INTERACTIVE=true;;
        --setup) SETUP=true;;
        --sshd) SSHD=true;;
        --image) IMAGE="$2";shift;;
        --tag) TAG="$2";shift;;
        --push) PUSH=true;;
        -h) usage; exit 0;;
        -*) usage; exit 1;;
esac
shift
done

if [ "${BUILD}" == "true" ]; then
    docker rmi "${IMAGE}:${TAG}"
    docker build -t "${IMAGE}:${TAG}" .
fi

if [ "${PUSH}" != "false" ]; then
    docker tag ${IMAGE}:${TAG} huta17-d.gns.cri.nz:5000/yannik/${IMAGE}:${TAG}
    docker push huta17-d.gns.cri.nz:5000/yannik/${IMAGE}:${TAG}
fi

if [ "${INTERACTIVE}" == "true" ]; then
    docker run -it --rm \
      -v $RCET_DATA:/home/sysop/data \
      -v $PWD:/home/sysop/sc3-playback \
    ${IMAGE}:${TAG} bash
      #--link seiscomp3:postgres_db
      #-v $PWD/dot_seiscomp3:/home/sysop/.seiscomp3 \
fi

if [ "${SSHD}" == "true" ]; then
    docker stop $CONTAINER
    docker rm $CONTAINER
    docker run -it --name $CONTAINER -u root -p 8022:22 \
    # --link seiscomp3:postgres_db \
    -v /geonet/seismic:/home/sysop/sds \
    -v $PWD/dot_seiscomp3:/home/sysop/.seiscomp3 \
    -v $PWD/data:/home/sysop/data \
    -v $PWD/sc3-playback:/home/sysop/sc3-playback \
    $IMAGE
fi


