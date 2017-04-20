# Testing
## Setting up the docker container

This directory contains a Dockerfile to generate a fully configured SeisComP3
installation using a setup similar to the real-time system operated by the
Swiss Seismological Service. To generate the docker image using the Dockerfile
run:

```
docker build -t seiscomp3-ch .
```

The resulting image has two mount points, one for the directory containing the
playback scripts and one for the waveform data and the database for the
playback. The directory [data](data/) contains a test database file with a
SeisComP3 configuration, inventory, and a multiplexed MiniSEED file for one
event.

Assuming that the playback script is in the directory
`${HOME}/sc3-playback` and the playback data is under `${PWD}/data` you can
start the container as follows:

```
docker run -d --name sc3-ch -p 9999:22 -v ${PWD}/data:/home/sysop/data -v ${HOME}/sc3-playback/:/home/sysop/sc3-playback seiscomp3-ch
```

This will also start an ssh server that you can connect to with (password the
same as the user name):

```
ssh -p 9999 sysop@localhost
```

## Running the playback
First get a shell in your container by running:
```
docker exec -it --user sysop seiscomp3-ch /bin/bash
```

Once you have a shell in your container and assuming your waveform file is
called `test-event.sorted-mseed` and your sqlite3 database `test.db` you can
start a playback as follows:
```
cd sc3-playback
./playback.py ../data/test.db ../data/test-event.sorted-mseed
```
You can then use `scolv` to analyse the results from the playback. Note that you
have to start `scolv` on your host machine as no guis are installed in the
container.

```
scolv --offline --plugins dbsqlite3 -d sqlite3://${PWD}/data/test.db
```
By default the user `sysop` inside the container has `USER_ID=1000` and
`GROUP_ID=1000`. If this doesn't match with the permissions of the playback
files on your host machine add the following options to your `docker run`
command:
```
-e USER_ID=`id -u` -e GROUP_ID=`id -g`
```
