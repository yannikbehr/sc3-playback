#!/usr/bin/env python

"""
Run real-time or historic playbacks to test new configuration settings and debug
problems observed during real-time operations. All core modules, seedlink, and
all modules that were enabled using 'seiscomp enable modulename' are included
in the playback.
"""

import calendar
import datetime
import glob
import imp
import os
import pipes
import shutil
import signal
import subprocess as sp
import subprocess
import shutil
import sys
import tempfile
import time
import traceback
import uuid
from seiscomp3 import Config, System
import seiscomp3.Kernel
import seiscomp3.IO


class PBError(Exception):
    pass


def error(msg):
    sys.stderr.write("error: %s\n" % msg)
    sys.stderr.flush()


def start_module(mod, params=''):
    """
    Monkey patch the start parameter routine to pass in additional command line
    arguments.
    """
    touch(env.runFile(mod.name))
    old_params = mod._get_start_params()
    new_params = lambda: old_params + ' ' + params
    mod._get_start_params = new_params
    return mod.start()


##### The following functions were copied from the seiscomp startup script ####
def touch(filename):
    try:
        open(filename, 'w').close()
    except Exception, exc:
        PBError(str(exc))


def system(args):
    proc = sp.Popen(args, shell=False, env=os.environ)
    while True:
        try:
            return proc.wait()
        except KeyboardInterrupt:
            continue
        except Exception, e:
            # Terminate was introduced in Python 2.6
            tb = traceback.format_exc()
            sys.stderr.write("Exception: %s" % tb)
            try:
                proc.terminate()
            except:
                pass
            sys.stderr.write("Exception: %s\n" % str(e))
            continue


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
    if a.order < b.order:
        return -1
    if a.order > b.order:
        return 1
    if a.name < b.name:
        return -1
    if a.name > b.name:
        return 1
    return 0


def load_init_modules(path):
    mods = []

    files = glob.glob(os.path.join(path, "*.py"))
    for f in files:
        try:
            pmod = load_module(f)
        except Exception, exc:
            error(("%s: " % f) + str(exc))
            continue

        try:
            mod = pmod(env)
        except Exception, exc:
            error(("%s: " % f) + str(exc))
            continue

        mods.append(mod)
    mods = sorted(mods, cmp=module_compare)
    return mods
###############################################################################


def setup_seedlink(fifofn):
    """
    Make sure the fifo file exists and that the seedlink buffer is empty
    otherwise seedlink will reject waveforms identical to previous playbacks,
    e.g. during historic playbacks
    """
    bufferdir = os.path.join(
        ei.installDir(), 'var', 'lib', 'seedlink', 'buffer')
    if os.path.isdir(bufferdir):
        names = os.listdir(bufferdir)
        for _e in names:
            dname = os.path.join(bufferdir, _e)
            if os.path.isdir(dname):
                shutil.rmtree(dname)
    # check whether the fifo file exists
    if not os.path.exists(fifofn):
        raise PBError('fifo %s does not exist.' % fifofn)
    if not os.path.stat.S_ISFIFO(os.stat(fifofn).st_mode):
        raise PBError('%s is not a fifo file.' % fifofn)


def setup_config(configdir, db):
    default = ei.configDir()
    print(default)
    if configdir == default:
        print('default conf dir')
        pass
    elif os.path.islink(default):
        # default configuration directory is already a link so it's
        # save to remove it without backup
        print('linked default conf dir')
        os.unlink(default)
        os.symlink(configdir, default)
    elif os.path.isdir(default):
        # default configuration directory is a regular directory so we
        # back it up
        print('spec conf dir')
        d = datetime.datetime.now().strftime("%Y%j%H%M%S")
        newdir = '_'.join((default, d, 'backup'))
        if os.path.isdir(newdir):
            raise PBError('Cannot backup %s: %s already exists.' %
                          (default, newdir))
        os.rename(default, newdir)
        os.symlink(configdir, default)

    # scmaster's database connection can't be set on the command line so we
    # have to generate a temporary config file that sets the database
    # connection
    # tmp_config = tempfile.NamedTemporaryFile()
    # tmp_config.close()
    tmp_config = '/tmp/scmaster_tmp.cfg'
    cfg_tmp = Config.Config()
    cfg = Config.Config()
    ei.initConfig(cfg, 'scmaster')
    for cfg_entry in ['msgGroups']:
        cfg_tmp.setStrings(cfg_entry, cfg.getStrings(cfg_entry))
    try:
        s = cfg.getStrings('plugins')
    except:
        # no plugins set
        cfg_tmp.setString('plugins', 'dbplugin')
    else:
        it = s.begin()
        found = False
        while it != s.end():
            pi = it.next()
            if pi == 'dbplugin':
                found = True
        if not found:
            s.append('dbplugin')
        cfg_tmp.setStrings('plugins', s)
    cfg_tmp.setString('core.plugins', 'dbsqlite3')
    cfg_tmp.setString('plugins.dbPlugin.dbDriver', 'sqlite3')
    cfg_tmp.setString('plugins.dbPlugin.readConnection', db)
    cfg_tmp.setString('plugins.dbPlugin.writeConnection', db)
    cfg_tmp.setString('admin.adminname', '')
    cfg_tmp.setString('admin.password', '')
    cfg_tmp.writeConfig(tmp_config)
    return tmp_config


def get_enabled_modules(exclude=[]):
    """
    Return a list of enabled modules in the order in which they would be
    called by 'seiscomp start'.
    """
    INIT_PATH = os.path.join(ei.installDir(), "etc", "init")
    mods = load_init_modules(INIT_PATH)
    startup_modules = {}
    for _m in mods:
        if _m.name in exclude:
            continue
        if isinstance(_m, seiscomp3.Kernel.CoreModule):
            startup_modules[_m.name] = _m
        elif env.isModuleEnabled(_m.name):
            startup_modules[_m.name] = _m
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


def run(wf, database, config_dir, fifo, speed=None, jump=None, delays=None,
        mode='realtime', startupdelay=15, args='', eventfile=None):
    """
    Start SeisComP3 modules and the waveform playback.
    """
    if not os.path.isfile(wf):
        raise PBError('Data %s does not exist.' % wf)
    if not os.path.isdir(config_dir):
        raise PBError('Config %s does not exist.' % config_dir)
    system(['seiscomp', 'stop'])
#    tmpfile = "/tmp/%s" % uuid.uuid4()
#    print("/usr/local/bin/qmerge -b 512 -o %s %s" %(tmpfile,wf))
#    subprocess.call(["/usr/local/bin/qmerge", "-b", "512", "-o",tmpfile,wf])
#    shutil.copyfile(tmpfile,wf)
#    os.remove(tmpfile)

    scmaster_cfg = setup_config(config_dir, database)
    setup_seedlink(fifo)

    # construct msrtsimul command
    command = ["seiscomp", "exec", 
    os.path.dirname(os.path.realpath(__file__))+"/msrtsimul.py"]
    if speed is not None:
        command += ["-s", speed]
    if jump is not None:
        command += ["-j", jump]
    if delays is not None:
        command += ["-d", delays]

    # Construct scdispatch command
    if eventfile is not None:
        if not os.path.isfile(eventfile):
            raise PBError('Eventxml %s does not exist' % eventfile)
        dispatch_cmd = ['seiscomp', 'exec', 'scdispatch']
        dispatch_cmd += ['-i', eventfile, '-O', 'add']
        # if we run in historic mode merge origins
        if mode != 'realtime':
            routingtable = 'Pick:PICK,Amplitude:AMPLITUDE,Origin:LOCATION,'
            routingtable += 'Magnitude:MAGNITUDE,StationMagnitude:MAGNITUDE,'
            routingtable += 'FocalMechanism:FOCMECH'
            dispatch_cmd += ['--routingtable', routingtable]

    # start SC3 modules
    mods = get_enabled_modules()
    processes = []
    try:
        if mode != 'realtime':
            command += ['-m', 'historic']
            t0 = get_start_time(wf)
            command += ['-t', str(t0)]
            t0 -= datetime.timedelta(seconds=startupdelay)
            print "Start time %s" % t0
            # /usr/lib/faketime/libfaketime.so.1'
            os.environ[
                'LD_PRELOAD'] = '/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1'
            ts = time.time()
            # Set system time in seconds relative to UTC now
            os.environ['FAKETIME'] = "%f" % (
                calendar.timegm(t0.utctimetuple()) - ts)
        else:
            ts = time.time()
            startupdelay = 0
        start_module(mods.pop('kernel'))
        start_module(mods.pop('spread'))
        start_module(mods.pop('seedlink'))
        start_module(mods.pop('scmaster'), '--start-stop-msg=1 --config %s' % scmaster_cfg)
        for _n, _m in mods.iteritems():
		start_module(mods[_n],'-d "sqlite3://%s"' % database)
		#start_module(mods[_n],'--plugins dbsqlite3,evscore,dmvs,dmsm,locnll,mlh -d "sqlite3://%s"' % database)
	# manual starts a module in debug interactive mode
	#os.system("scfdalpine --trace --plugins dbsqlite3,dmvs,dmsm,mlh -d sqlite3://%s > /home/sysop/.seiscomp3/log/scfdalpine.log 2>&1 &" % database)
	#os.system("scfdforela --trace --plugins dbsqlite3,dmvs,dmsm,mlh -d sqlite3://%s > /home/sysop/.seiscomp3/log/scfdforela.log 2>&1 &" % database)
	#os.system('scfinder --trace --plugins dbsqlite3,dmvs,dmsm,mlh -d sqlite3://%s &> /home/sysop/.seiscomp3/log/scfinder.log &' % database)
	#os.system('scm --plugins dbsqlite3,dmvs,dmsm,mlh -d "sqlite3://%s" &' % database)
	#os.system('scmm --plugins dbsqlite3,dmvs,dmsm,mlh -d "sqlite3://%s" &' % database)
        #os.system('scrttv --plugins dbsqlite3,dmvs,dmsm,mlh -d "sqlite3://%s" &' % database)
        #os.system('scolv --plugins dbsqlite3,dmvs,dmsm,mlh -d "sqlite3://%s" &' % database)

        command.append(wf)

        #print('Executing: %s', command)
        system(command)
        if eventfile is not None:
            system(dispatch_cmd)
        system(['seiscomp', 'stop'])
    except KeyboardInterrupt:
        if eventfile is not None:
            system(dispatch_cmd)
        system(['seiscomp', 'stop'])
    except Exception, e:
        tb = traceback.format_exc()
        sys.stderr.write("Exception: %s" % tb)
        sys.stderr.write("Exception: %s\n" % str(e))
        system(['seiscomp', 'stop'])


if __name__ == '__main__':
    import argparse
    ei = System.Environment.Instance()
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
        run(args.waveforms, args.database, args.config_dir, args.fifo,
            speed=args.speed, jump=args.jump, delays=args.delays,
            mode=args.mode, eventfile=args.events)
    except PBError, e:
        print e
        sys.exit()
