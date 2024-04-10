#!/usr/bin/env python

import sys, time, traceback
import seiscomp3.Client, seiscomp3.DataModel
import re, math

max_station_distance_km = 300 
stream_whitelist = ["HH", "EH", "SH", "HG", "HN", "EN", "EG","SN"]
component_whitelist = []  # set to ["Z"] for vertical component only
network_blacklist = ["DK"]
network_whitelist = []  # all except blacklist

# seconds before and after origin time
before, after = 60, 120
regex = re.compile('/')
sort = True  # will produce sorted files with ".sorted-mseed" extension

def haversine(lon1, lat1, lon2, lat2):
    # convert decimal degrees to radians
    print([lon1, lat1, lon2, lat2])
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371 # Radius of earth in meters. Use 3956 for miles
    return c * r

def filterStreams(streams):
    # NOTE that the criteria here are quite application dependent:
    # If we have HH and BH streams use only BH etc., but in other
    # contexts HH would have priority over BH

    filtered = []

    for net, sta, loc, cha in streams:
        if cha[:2] in [ "HH", "SH" ] and (net, sta, loc, "BH" + cha[-1]) in streams:
            continue
        filtered.append((net, sta, loc, cha))

    return filtered


def getCurrentStreams(dbr, now=None, org=None, radius=max_station_distance_km):
    if now is None:
        now = seiscomp3.Core.Time.GMT()
    inv = seiscomp3.DataModel.Inventory()
    dbr.loadNetworks(inv)

    result = []

    for inet in xrange(inv.networkCount()):
        network = inv.network(inet)
        if network_blacklist and network.code()     in network_blacklist:
            continue
        if network_whitelist and network.code() not in network_whitelist:
            continue
        dbr.load(network);
        for ista in xrange(network.stationCount()):
            station = network.station(ista)
            try:
                start = station.start()
            except:
                continue

            try:
                end = station.end()
                if not start <= now <= end:
                    continue
            except:
                pass

            if org is not None:
                haversine_inputs=[station.longitude(),
                                  station.latitude(),
                                  org.longitude().value(),
                                  org.latitude().value()]
                ep_dist = haversine(*haversine_inputs)
                if ep_dist > radius:
                    print('skip %s.%s (%s > %s)'%(network.code(), station.code(), ep_dist, radius))
                    continue

            # now we know that this is an operational station

            for iloc in xrange(station.sensorLocationCount()):
                loc = station.sensorLocation(iloc)

                for istr in xrange(loc.streamCount()):
                    stream = loc.stream(istr)
                    if stream.code()[:2] not in stream_whitelist:
                        continue

                    result.append((network.code(), station.code(), loc.code(), stream.code()))

    return filterStreams(result)


class DumperApp(seiscomp3.Client.Application):

    def __init__(self, argc, argv):
        seiscomp3.Client.Application.__init__(self, argc, argv)
        self.setMessagingEnabled(True)
        self.setDatabaseEnabled(True, True)
        self.setLoggingToStdErr(True)
        self.setDaemonEnabled(False)
        self.setRecordStreamEnabled(True)

    def validateParameters(self):
        try:
            if seiscomp3.Client.Application.validateParameters(self) == False:
                return False
            return True

        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return False

    def createCommandLineDescription(self):
        try:
            try:
                self.commandline().addGroup("Dump")
                self.commandline().addStringOption("Dump", "event,E", "ID of event to dump")
                self.commandline().addStringOption("Dump", "radius,R", "Maximum event radius within to dump stations")
                self.commandline().addStringOption("Dump", "start", "Start time")
                self.commandline().addStringOption("Dump", "end", "End time")

                self.commandline().addOption("Dump", "unsorted,U", "produce unsorted output (not suitable for direct playback!)")
            except:
                seiscomp3.Logging.warning("caught unexpected error %s" % sys.exc_info())
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)

    def get_and_write_data(self, t1, t2, out, org=None, radius = max_station_distance_km):
        dbr = seiscomp3.DataModel.DatabaseReader(self.database())
        streams = getCurrentStreams(dbr, t1, org, radius)

        # split all streams into groups of same net
        netsta_streams = {}
        for net, sta, loc, cha in streams:
            netsta = net
            if not netsta in netsta_streams:
                netsta_streams[netsta] = []
            netsta_streams[netsta].append((net, sta, loc, cha))
        print(netsta_streams)
        data = []
        netsta_keys = netsta_streams.keys()
        netsta_keys.sort()
        for netsta in netsta_keys:

            number_of_attempts = 1  # experts only: increase in case of connection problems, normally not needed
            for attempt in xrange(number_of_attempts):
                if self.isExitRequested(): return

                stream = seiscomp3.IO.RecordStream.Open(self.recordStreamURL())
                stream.setTimeout(3600)
                for net, sta, loc, cha in netsta_streams[netsta]:
                    if component_whitelist and cha[-1] not in component_whitelist:
                        continue
                    stream.addStream(net, sta, loc, cha, t1, t2)

                count = 0
                input = seiscomp3.IO.RecordInput(stream, seiscomp3.Core.Array.INT, seiscomp3.Core.Record.SAVE_RAW)
                while 1:
                    try:
                        rec = input.next()
                    except:
                        break
                    if not rec:
                        break

                    count += 1
                    if sort:
                        data.append((rec.endTime(), rec.raw().str()))
                    else:
                        out.write("%s" % rec.raw().str())

                sys.stderr.write("Read %d records for %d streams\n" % (count, len(netsta_streams[netsta])))
                if count > 0 or attempt + 1 == number_of_attempts:
                    break
                if self.isExitRequested(): return
                sys.stderr.write("Trying again\n")
                time.sleep(5)

        if sort:
            data.sort()

        if sort:
            # finally write sorted data and ensure uniqueness
            previous = None
            for endTime, raw in data:
                if previous is not None and raw[6:] == previous[6:]:
                    # unfortunately duplicates do happen sometimes
                    continue
                out.write("%s" % raw)
                previous = raw


    def dump(self, eventID, start=None, end=None, radius = max_station_distance_km):
        if start and end:
            try:
                filename = start.toString("%FT%T")
                if sort:
                    out = "%s-sorted-mseed" % (filename)
                else:
                    out = "%s-unsorted-mseed" % (filename)
                out = file(out, 'w')
                self.get_and_write_data(start, end, out)
                return True
            except:
                info = traceback.format_exception(*sys.exc_info())
                for i in info: sys.stderr.write(i)
                return False

        self._dbq = self.query()
        evt = self._dbq.loadObject(seiscomp3.DataModel.Event.TypeInfo(), eventID)
        evt = seiscomp3.DataModel.Event.Cast(evt)
        if evt is None:
            raise TypeError, "unknown event '" + eventID + "'"

        originID = evt.preferredOriginID()
        org = self._dbq.loadObject(seiscomp3.DataModel.Origin.TypeInfo(), originID)
        org = seiscomp3.DataModel.Origin.Cast(org)

        magID = evt.preferredMagnitudeID()
        mag = self._dbq.loadObject(seiscomp3.DataModel.Magnitude.TypeInfo(), magID)
        mag = seiscomp3.DataModel.Magnitude.Cast(mag)

#        now = seiscomp3.Core.Time.GMT()
        try:
            val = mag.magnitude().value()
            filename = regex.sub('_', eventID)

            if sort:
                out = "%s-M%3.1f.sorted-mseed" % (filename, val)
            else:
                out = "%s-M%3.1f.unsorted-mseed" % (filename, val)
            out = file(out, "w")

            t0 = org.time().value()
            t1, t2 = t0 + seiscomp3.Core.TimeSpan(-before), t0 + seiscomp3.Core.TimeSpan(after)

            self.get_and_write_data(t1, t2, out, org, radius)
            print(t1,t0,t2)
            return True

        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return False

    def run(self):
        try:
            if self.commandline().hasOption("unsorted"):
                sort = False
            radius = max_station_distance_km
            if self.commandline().hasOption("radius"):
                radius = float(self.commandline().optionString("radius"))
            if self.commandline().hasOption('start') and self.commandline().hasOption('end'):
                startstring = self.commandline().optionString('start')
                starttime = seiscomp3.Core.Time.FromString(startstring, "%FT%T")
                endstring = self.commandline().optionString('end')
                endtime = seiscomp3.Core.Time.FromString(endstring, "%FT%T")
                if not self.dump(None, start=starttime, end=endtime):
                    return False
            elif self.commandline().hasOption("event"):
                evid = self.commandline().optionString("event")
                if not self.dump(evid,radius=radius):
                    return False
            else:
                sys.stderr.write("Either --start and --end or --event need to be provided.")
                return False

        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return False

        return True


def main():
    app = DumperApp(len(sys.argv), sys.argv)
    app()

if __name__ == "__main__":
    main()
