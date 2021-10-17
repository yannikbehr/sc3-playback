#!/usr/bin/env python
"""
Generate configuration files for Finder playback.
"""
from argparse import ArgumentParser
import os

from jinja2 import Template, Environment, FileSystemLoader
from obspy import read_inventory


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
    write_config(templated, configd, 'finder_geonet_calcmask.config', param)


def scmaster_cfg(templated, configd):
    eventdir = os.path.dirname(os.path.normpath(configd))
    param = {}
    write_config(templated, configd, 'scmaster.cfg', param)


def global_cfg(templated, configd):
    eventdir = os.path.dirname(os.path.normpath(configd))
    param = {}
    write_config(templated, configd, 'global.cfg', param)


def seedlink_cfg(inv, templated, configd):
    net = inv.networks[0]
    with open(os.path.join(templated, 'seedlink_template')) as fh:
        lines = fh.readlines()
        slstub = lines[:122]
    for st in net:
        stat_entry = 'station {}.{}  description = "{}"\n'.format(net.code, st.code, st.site.name)
        stat_entry += '{:>20} = "{}"\n'.format('name', st.code)
        stat_entry += '{:>23} = "{}"\n\n'.format('network', net.code)
        slstub.append(stat_entry)
    with open(os.path.join(configd, 'seedlink.ini'), 'w') as fh:
        fh.writelines(slstub)


def finder_mask(inv, configd):
    finderfn = 'data_0'
    with open(os.path.join(configd, finderfn), 'w') as fh:
        for net in inv:
            for st in net:
                fh.write('{} {} {}\n'.format(st.latitude, st.longitude, 2.0))


if __name__ == '__main__':
    parser = ArgumentParser(prog='gen_config.py',
                            description=__doc__.strip())
    parser.add_argument('inventory', type=str,
                        help='Inventory file.')
    parser.add_argument('templated', type=str,
                        help='Directory with template config files.')
    parser.add_argument('configd', type=str,
                        help='Directory for configuration files.')
    args = parser.parse_args()
    templated = args.templated
    configd = args.configd
    inv = read_inventory(args.inventory)
    try:
        os.makedirs(configd)
    except FileExistsError:
        pass
    scfinder_cfg(templated, configd)
    finder_cfg(templated, configd)
    scmaster_cfg(templated, configd)
    global_cfg(templated, configd)
    seedlink_cfg(inv, templated, configd)
    finder_mask(inv, configd)
