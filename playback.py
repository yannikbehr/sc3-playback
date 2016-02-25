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
import time
import traceback

from seiscomp3 import Config, System
import seiscomp3.Kernel
import seiscomp3.IO

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


def load_module(path):
    """
    Returns a seiscomp3.Kernel.Module instance from a given path with
    a given name
    """
    modname = os.path.splitext(os.path.basename(path))[0].replace('.', '_')
    f = open(path, 'r')
    modname = '__seiscomp_modules_' + modname
    if sys.modules.has_key(modname):
        mod = sys.modules[modname]
    else:
        # create a module
        mod = imp.new_module(modname)
        mod.__file__ = path

    # store it in sys.modules
    sys.modules[modname] = mod

    # our namespace is the module dictionary
    namespace = mod.__dict__

    # test whether this has been done already
    if not hasattr(mod, 'Module'):
        code = f.read()
        # compile and exec dynamic code in the module
        exec compile(code, '', 'exec') in namespace
    module = namespace.get('Module')
    return module


def module_compare(a, b):
    if a.order < b.order: return -1
    if a.order > b.order: return 1
    if a.name < b.name: return -1
    if a.name > b.name: return 1
    return 0


def load_init_modules(path):
    mods = []

    files = glob.glob(os.path.join(path, "*.py"))
    for f in files:
        try: pmod = load_module(f)  # imp.load_source(mod_name, f)
        except Exception, exc:
            error(("%s: " % f) + str(exc))
            continue

        try: mod = pmod(env)  # .Module(env)
        except Exception, exc:
            error(("%s: " % f) + str(exc))
            continue

        mods.append(mod)
    # mods = sorted(mods, key=lambda mod: mod.order)
    mods = sorted(mods, cmp=module_compare)
    return mods


def get_enabled_modules():
    """
    Return a list of enabled modules in the order in which they would be
    called by 'seiscomp start'.
    """
    INIT_PATH = os.path.join(ei.installDir(), "etc", "init")
    mods = load_init_modules(INIT_PATH)
    startup_modules = []
    for _m in mods:
        if isinstance(_m, seiscomp3.Kernel.CoreModule):
            startup_modules.append(_m.name)
        elif env.isModuleEnabled(_m.name):
            startup_modules.append(_m.name)
        else:
            continue
    return startup_modules


def get_start_time(fn):
    """
    Find the earliest end-time of all records in the waveform file.
    """
    stream = seiscomp3.IO.RecordStream.Open('file://%s' % fn)
    input = seiscomp3.IO.RecordInput(stream, seiscomp3.Core.Array.INT,
                                     seiscomp3.Core.Record.SAVE_RAW)
    tmin = datetime.datetime.utcnow()
    while True:
        try:
            rec = input.next()
        except:
            break
        if not rec:
            break
        te = rec.endTime().toString("%FT%T.%4fZ")
        ts = rec.startTime().toString("%FT%T.%4fZ")
        dts = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        dte = datetime.datetime.strptime(te, "%Y-%m-%dT%H:%M:%S.%fZ")
        if dte < tmin:
            tmin = dte
            Id = rec.streamID()
    return tmin


def run(wf, speed=None, jump=None, delays=None, mode='realtime',
        startupdelay=7, args=''):
    """
    Start SeisComP3 modules and the waveform playback.
    """
    system(['seiscomp', 'stop'])
    mods = get_enabled_modules()
    if not os.path.isfile(wf):
        raise PBError('%s does not exist.' % wf)
    command = ["msrtsimul"]
    if speed is not None:
        command += ["-s", speed]
    if jump is not None:
        command += ["-j", jump]
    if delays is not None:
        command += ["-d", delays]

    if mode != 'realtime':
        command += ['-m', 'historic']
        command.append(wf)
        t0 = get_start_time(wf)
        t0 -= datetime.timedelta(seconds=startupdelay)
        os.environ['LD_PRELOAD'] = '/usr/lib/faketime/libfaketime.so.1'
        os.environ['FAKETIME'] = "@%s" % t0
        ts = time.time()
        system(['seiscomp', 'start'])
        while (time.time() - ts) < startupdelay:
            time.sleep(0.1)
        system(command)
        system(['seiscomp', 'stop'])
    else:
        system(['seiscomp', 'start'])
        while (time.time() - ts) < startupdelay:
            time.sleep(0.1)
        system(command)
        system(['seiscomp', 'stop'])


if __name__ == '__main__':
    import argparse
    ei = System.Environment.Instance()
    # Create environment which supports queries for various SeisComP
    # directoris and sets PATH, LD_LIBRARY_PATH and PYTHONPATH
    env = seiscomp3.Kernel.Environment(ei.installDir())
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
        # setup_config(args.config_dir)
        # setup_seedlink(args.fifo)
        # run(args.waveforms, speed=args.speed, jump=args.jump,
        #    delays=args.delays, mode=args.mode)
        print get_enabled_modules()
    except PBError, e:
        print e
        sys.exit()
