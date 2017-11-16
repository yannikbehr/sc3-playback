# SeisComP3 playbacks

This collection of scripts can be used to run playbacks in SeisComP3 (SC3).

Briefly, the scripts do the following tasks (but it is also possible to run each step independently):

- Connect to an existing seiscomp3 installation (local or remote) and download the stations and binding information
- Then, depending on command line options, download a miniseed containing the stations waveforms for the period of interest or the selected events
- Create an sqlite3 database that will be used for the test (to avoid polluting existing databases or in case there is no database at all) and update stations/bindings configuration in there from the dowloaded one
- Inject the dowloaded miniseed into seedlink (msrtsimul.py) via a system fifo. Optionally simulate historical time using libfaketime

Seiscomp3 configuration requirements:
- Since playback results are stored in an sqlite3 database, sqlite3 support has to be
enabled in SC3.
- bindings and meta data exist
- seedlink has to be configured with the mseedfifo plugin
- the mseedfifo has to exist and it has to be a named pipe

Some of the scripts depend on the SC3 Python api and seiscomp environment variables, so you might prepend
'seiscomp exec' in front of the commands or, even easier, you can open a shell session like the following
and then run commands normally:

    seiscomp exec bash

The playback also depends on the library `libfaketime` which is used to simulate
a different system time.

During the playback all enabled modules (with `seiscomp enable modulename`) will
be tested.

The main script is `playback.sh`:

    $ ./playback.sh -h
    Usage: ./playback.sh [Options] action

    Arguments:
        action          Decide what to do:
                        prep: Prepare playback files
                        pb: run playback (requires a previous 'prep')
                        all: do both in one go
    Options:
        -h              Show this message.
        --configdir     Configuration directory to use. (Default: /home/sysop/.seiscomp3).
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




## Examples
### Example 1: Run playback of a single event

In this example we run a historic playback of an event with event ID
`smi:ch.ethz.sed/sc3a/2016acratl`. Historic playbacks preserve the original
record time and also simulate system time corresponding to the record time:

    $ ./playback.sh --evid "smi:ch.ethz.sed/sc3a/2016acratl" all

This will first prepare the necessary files for the playback in the directory `data/2016acratl`. To do so it will first connect to an operational database (the database connection is defined in `playback.cfg`) to extract the inventory,
configuration, and the event information. Then an sqlite3 database `test_db.sqlite`
is created (the name is defined in `playback.cfg`) and the inventory and configuration are written to that database. A copy of `test_db.sqlite` is also generated called `test_db_no_event.sqlite`. This can be
used to overwrite the results from previous playbacks if repeated playbacks of
the same events are run in 'historic' mode. The event information is stored in an
XML file called `2016acratl.xml` which will be added to the database after the
playback has finished using `scdispatch`. Next the waveforms for the event are
retrieved from an SDS archive (the location of the SDS archive is defined in
`playback.cfg`) and written to the file `smi:ch.ethz.sed_sc3a_2016acratl-M3.1.sorted-mseed`.

Next the playback will be run in realtime so it will take as long as the
waveform window. To only do the preparation step without the playback you can run:

    $ ./playback.sh --evid "smi:ch.ethz.sed/sc3a/2016acratl" prep

To look at the playback results with `scolv` run:

    scolv --offline --plugins dbsqlite3,locnll,mlh -d sqlite3://data/2016acratl/test_db.sqlite

Note that if you ran the same playback again you would create identical event IDs
and so couldn't write to the database. To run multiple playbacks of the same event
either do realtime playbacks or copy the bare database file
(`test_db_no_event.sqlite`) over `test_db.sqlite`. To only do the playback
without the preparation phase run:

    $ ./playback.sh --evid "smi:ch.ethz.sed/sc3a/2016acratl" pb

### Example 2: Run playbacks of multiple events

To do playbacks of several events back-to-back run:

    $ ./playback.sh --fin pb_events.txt all

This will create all the necessary files for the playback in `data/pb_events`.
The file `pb_events.txt` contains one event ID per line and ends with a newline.
You can comment single event IDs with a '#'-character.


### Example 3: Run playback of a timespan


To do playbacks of all available data in a time span run:

    $ ./playback.sh --begin "yyyy-mm-dd HH:MM:SS" --end "yyyy-mm-dd HH:MM:SS" all

This will create all the necessary files for the playback in `data/yyyymmddHHMMSS-yyyymmddHHMMSS_N_events`.

## Setting up and running the playback manually
The `playback.sh` script is only a convenient wrapper around the two Python
scripts `playback.py` and `make-mseed-playback.py`. Below are some notes in case
you don't want to use the `playback.sh` script.

### Setting up the sqlite3 database
Assuming that you have a SeisComP3 compatible inventory in `inventory.xml` and
the corresponding configuration in `configuration.xml` then you can setup an
sqlite3 database as follows:

```
# Initialise a database file called test.db with the SeisComP3 schema
sqlite3 -batch -init ${SEISCOMP_ROOT}/share/db/sqlite3.sql test.db .exit

# Import the inventory
scdb --plugins dbsqlite3 -d sqlite3://test.db -i inventory.xml

# Import the configuration
scdb --plugins dbsqlite3 -d sqlite3://test.db -i configuration.xml

# Make a copy of the empty database; you can then easily erase the results of a
# test run by copying the empty database file over the one containing the test
# results   
cp test.db test_empty.db
```

### Generating the waveform file
Using the script `make-mseed-playback.py` you can use any record source
supported by SeisComP3 to generate a multiplexed MiniSEED file suitable for
playback. To see all supported record sources run:
```
./make-mseed-playback.py --record-driver-list
```

Assuming you have an SDS archive under `/data/sds` you could then, for example,
request an hour long chunk of data including all stations that were active
during that time span by running:

```
./make-mseed-playback.py  --plugins dbsqlite3 -d sqlite3://test.db --start "2017-04-01T14:59:59" --end "2017-04-01T15:59:59"
```
This will produce a file called `2017-04-01T14:59:59.sorted-mseed` in your
current directory. Note that this also requires a database containing the
inventory. Again, you can use any database type supported by SeisComP3. For a
complete list of options run:
```
./make-mseed-playback.py -h
```

### Running the playback
Once you've setup the playback files you can start the playback running:
```
./playback.py test.db 2017-04-01T14:59:59.sorted-mseed
```
For a complete list of options run:
```
./playback.py -h
```

## Notes on the SC3 configuration

Presumably you run the playbacks on a dedicated playback machine. In principle it
should be save to just copy the contents of `~/.seiscomp3` from the production
machine to your playback machine as the database connection is overwritten during
the playback. You can rename the directory to something like `~/.seiscomp3_test`
and then pass this new directory to the playback file using the `--configdir`
command line option. This will backup `~/.seiscomp3` and then create a symlink
`~/.seiscomp3 -> ~/.seiscomp3_test`.

To be able to distinguish between original origins and those created by the playback
you can set `agencyID=PB`. If you are merging events from other agencies with
other tools than `scevent` also consider blacklisting these agencies
(`processing.blacklist.agencies = agency1,agency2`); otherwise not all origins
may be associated to the correct events.

## Notes on testing different SC3 versions

Let's assume you've installed a newer version of SC3 under `~/my_special_sc3`.
If you want to run playbacks with this particular version you have to put a

```
~/my_special_sc3/bin/seiscomp exec
```
in front of every command. See also the [tests](tests/README.md) directory for instructions on
how to use Docker for testing.
