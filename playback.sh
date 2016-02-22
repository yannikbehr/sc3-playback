#!/bin/bash

seiscomp stop

sudo service postgresql stop
sudo cp -a /var/lib/postgresql_empty_configured /var/lib/postgresql
sudo service postgresql start

rm -r /usr/local/var/lib/seedlink/buffer/*
seiscomp start spread scmaster NLoB_amp NLoB_mag NLoB_reloc NTeT_amp \
NTeT_mag NTeT_reloc scamp scenvelope scevent scmag \
scvsmag scvsmaglog seedlink scautoloc NLoB_auloc NTeT_auloc

#scautoloc --playback &
#NLoB_auloc --playback &
#NTeT_auloc --playback &
#scvsmag --playback &
msrtsimul -j 1 -c -m realtime $0| \
tee >(scautopick -I -) >(NLoB_apick -I -) >(NTeT_apick -I -) > /usr/local/var/run/seedlink/mseedfifo

