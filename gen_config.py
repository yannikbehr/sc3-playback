#!/usr/bin/env python
"""
Generate configuration files for Finder playback.
"""
from argparse import ArgumentParser
import os

from jinja2 import Template, Environment, FileSystemLoader


def write_config(templated, configd, configfile, param):
    file_loader = FileSystemLoader(templated)
    env = Environment(loader=file_loader)
    tmpl = env.get_template(configfile)
    with open(os.path.join(configd, configfile), 'w') as fh:
        fh.write(tmpl.render(cfg=param))


def scfinder_cfg(templated, configd):
    finder_cfg_path = os.path.join(configd, 'finder_geonet.config')
    param = {'finder_cfg_path': finder_cfg_path}
    write_config(templated, configd, 'scfinder.cfg', param)


def finder_cfg(templated, configd):
    eventdir = os.path.dirname(os.path.normpath(configd))
    param = {'eventdir': eventdir}
    write_config(templated, configd, 'finder_geonet.config', param)


def scmaster_cfg(templated, configd):
    eventdir = os.path.dirname(os.path.normpath(configd))
    param = {}
    write_config(templated, configd, 'scmaster.cfg', param)


def global_cfg(templated, configd):
    eventdir = os.path.dirname(os.path.normpath(configd))
    param = {}
    write_config(templated, configd, 'global.cfg', param)


if __name__ == '__main__':
    parser = ArgumentParser(prog='gen_config.py',
                            description=__doc__.strip())
    parser.add_argument('templated', type=str,
                        help='Directory with template config files.')
    parser.add_argument('configd', type=str,
                        help='Directory for configuration files.')
    args = parser.parse_args()
    templated = args.templated
    configd = args.configd
    try:
        os.makedirs(configd)
    except FileExistsError:
        pass
    scfinder_cfg(templated, configd)
    finder_cfg(templated, configd)
    scmaster_cfg(templated, configd)
    global_cfg(templated, configd)
    