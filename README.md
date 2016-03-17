Running SeisComP3 playbacks
===========================
This directory contains all the necessary scripts to
run a playback of a past earthquake with event information 
stored in a SeisComp3 (SC3) database and the corresponding 
waveform files stored in a way that is compatible with SC3's 
waveform input methods.

The following shows an example of how to create the necessary 
files for the playback, how to run the playback and how to analyse 
the results.





the Ml 4.2 event on 2012/2/11 in 
Zug/Switzerland. Please regard the scripts as templates
that you may have to adapt to your network specific settings. 
Also bear in mind that the playback uses the SED specific
SeisComP3 settings under ~/.seiscomp3.


Generating the waveform file
----------------------------
The script vs-mseed.sh downloads waveforms from an arclink
server and generates a multiplexed miniSEED file that can
be used for playbacks. For information on how to use this 
script run:

$ ./vs-mseed.h -h

The included waveform file under ./waveforms was generated with 
the following command:

$ ./vs-mseed.sh -o waveforms/ZUG_11_2_2012.mseed  2012,02,11,22,43,26 2012,02,11,22,48,26 CH "*" "H*" arclink.ethz.ch:18002


Running the playback
--------------------
First make sure that spread and scmaster are running:

$ seiscomp start

An example playback can be run by executing the following command:

$ ./playback.sh --db-disable waveforms/ZUG_11_2_2012.mseed.sorted

This will create the following three files in the current directory:
scvsmag-processing-info.log (VS log file)
smi:ch.ethz.sed_sc3seattle_2012czaasn_report.txt (VS report file)
output.xml (log of all created SC3 objects)

For more information on playback.sh and additional options run:

$ ./playback.sh -h


Analysing the result using scolv
--------------------------------
The file output.xml together with the waveform file can be used to analyse
this event in scolv. First start scolv in offline mode and pass your network
specific inventory file:

$ scolv --offline --inventory-db inventory_seattle.xml

Now load the SC3 objects:
-> File -> Open -> output.xml

...and now the waveforms:
-> Settings -> Configure OriginLocatorView
...under Global Settings enter in Data Source field:
file:///home/vs/playback/waveforms/ZUG_11_2_2012.mseed.sorted

Now you can use the picker to look at the waveforms and triggers.


Showing the alerts in the UserDisplay
-------------------------------------
First start the ActiveMQ broker:

$ cd /home/vs/apache-activemq-5.9.1/bin
$ ./activemq start

Then start the UserDisplay:

$ cd /home/vs/userdisplay-2.4
$ ./runUNIX.sh &

And now start the same playback as before but in 'realtime' mode. 
In 'historic' mode the alerts would be in the past and therefore the
UserDisplay would not show anything.

$ cd /home/vs/playback
$ ./playback.sh --skip 1 --mode 'realtime' --db-disable waveforms/ZUG_11_2_2012.mseed.sorted

To stop the ActiveMQ broker do:

$ cd /home/vs/apache-activemq-5.9.1/bin
$ ./activemq stop


