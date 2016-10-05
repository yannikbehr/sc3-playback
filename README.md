# SeisComP3 playbacks

This collection of scripts can be used to run playbacks in SeisComP3 (SC3).
Since playback results are stored in an sqlite3 database, sqlite3 support has to be
enabled in SC3.

Some of the scripts depend on the SC3 Python api so you have to make sure
it is on `PYTHONPATH`. The api is typically located under `$ROOTDIR/lib/python`.

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
in front of every command.
