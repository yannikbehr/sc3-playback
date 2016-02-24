#!/usr/bin/env python

"""
Run real-time or fast playbacks to test new configuration settings and debug
problems observed during real-time operations. By default all enabled modules
are included in the playback.
"""

import datetime
import glob
import imp
import os
import pipes
import shutil
import signal
import subprocess as sp
import sys
import traceback

from seiscomp3 import Config, System

class PBError(Exception): pass

def system(args):
    proc = sp.Popen(args, shell=False, env=os.environ)
    while True:
        try:
            return proc.wait()
        except KeyboardInterrupt:
            continue
        except Exception, e:
            # Terminate was introduced in Python 2.6
            try: proc.terminate()
            except: pass
            sys.stderr.write("Exception: %s\n" % str(e))
            continue

def setup_seedlink(fifofn):
    bufferdir = os.path.join(ei.installDir(), 'var', 'lib', 'seedlink', 'buffer')
    if os.path.isdir(bufferdir):
        names = os.listdir(bufferdir)
        # Clear the buffer, otherwise seedlink will reject waveforms identical to
        # previous playbacks, e.g. during historic playbacks
        for _e in names:
            dname = os.path.join(bufferdir, _e)
            if os.path.isdir(dname):
                shutil.rmtree(dname)
    # check whether the fifo file exists
    if not os.path.exists(fifofn):
        raise PBError('%s does not exist.' % fifofn)
    if not os.path.stat.S_ISFIFO(os.stat(fifofn).st_mode):
        raise PBError('%s is not a fifo file.' % fifofn)


def setup_config(configdir):
    default = ei.configDir()
    if configdir == default:
        return
    if os.path.islink(default):
        # default configuration directory is already a link so it's
        # save to remove it without backup
        os.unlink(default)
    elif os.path.isdir(default):
        # default configuration directory is a regular directory so we
        # back it up
        d = datetime.datetime.now().strftime("%Y%j%H%M%S")
        newdir = '_'.join((default, d, 'backup'))
        if os.path.isdir(newdir):
            raise PBError('Cannot backup %s: %s already exists.' % \
                          (default, newdir))
        os.rename(default, newdir)
    os.symlink(configdir, default)


def run(wf, speed=None, jump=None, delays=None):
    if not os.path.isfile(wf):
        raise PBError('%s does not exist.' % wf)
    command = ["msrtsimul"]
    if speed is not None:
        command += ["-s", speed]
    if jump is not None:
        command += ["-j", jump]
    if delays is not None:
        command += ["-d", delays]
    command.append(wf)
    os.environ['LD_PRELOAD'] = '/usr/lib/faketime/libfaketime.so.1'
    os.environ['FAKETIME'] = "@2012-02-11 22:42:39.241600"
    proc = sp.Popen(command, shell=False, env=os.environ)
    proc1 = sp.call(['seiscomp', 'start'], shell=False, env=os.environ)
    proc.wait()
    # system(['seiscomp', 'restart'])
    system(['seiscomp', 'stop'])


if __name__ == '__main__':
    import argparse
    ei = System.Environment.Instance()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('database', help='Absolute path to an sqlite3 \
    database filename containing inventory and station bindings.')
    parser.add_argument('waveforms' , help="Absolute path to a \
    multiplexed MiniSEED file containing the waveform data.")
    parser.add_argument('-e', '--events', help='Absolute path to an SeisComP3ML \
    file containing event information that will be merged with the playback \
    results.', default=None)
    parser.add_argument('-c', '--config-dir', help='Directory containing \
    configuration files.',
    default=ei.configDir())
    parser.add_argument('-f', '--fifo', help='Absolute path to seedlink fifo \
    file', default=os.path.join(ei.installDir(), 'var', 'run', 'seedlink', 'mseedfifo'))
    parser.add_argument('-d', '--delays', help="""Absolute path to a file
    defining median delays for stations. These delays will be added to have
    playback results that are closer to the real-time behaviour. The delays
    file has one entry per station and per line following the pattern XX.ABC: d
    (XX: network code, ABC: station code, d: delay in seconds as a decimal
    number). The special entry 'default: d' defines the delay for all stations
    not listed explicitely.""", default=None)
    parser.add_argument('-s', '--speed', help='Speed factor.', default=None)
    parser.add_argument('-j', '--jump', help='Number of minutes to skip.',
                        default=None)
    parser.add_argument('-m', '--mode', help="""Choose between 'realtime' and
    'historic'. For 'realtime' the records in the input file will get a new
    timestamp relative to the current system time at startup. For 'historic'
    the input records will keep their original timestamp.""",
    default='historic')

    args = parser.parse_args()
    try:
        setup_config(args.config_dir)
        setup_seedlink(args.fifo)
        run(args.waveforms, speed=args.speed, jump=args.jump,
            delays=args.delays)
    except PBError, e:
        print e
        sys.exit()


#####################################################
# # Playback script to test
#
# seiscomp stop
#
# sudo service postgresql stop
# sudo cp -a /var/lib/postgresql_empty_configured /var/lib/postgresql
# sudo service postgresql start
#
# rm -r /usr/local/var/lib/seedlink/buffer/*
# seiscomp start spread scmaster NLoB_amp NLoB_mag NLoB_reloc NTeT_amp \
# NTeT_mag NTeT_reloc scamp scenvelope scevent scmag \
# scvsmag scvsmaglog seedlink scautoloc NLoB_auloc NTeT_auloc
#
# #scautoloc --playback &
# #NLoB_auloc --playback &
# #NTeT_auloc --playback &
# #scvsmag --playback &
# msrtsimul -j 1 -c -m realtime $0| \
# tee >(scautopick -I -) >(NLoB_apick -I -) >(NTeT_apick -I -) > /usr/local/var/run/seedlink/mseedfifo

