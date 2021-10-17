#!/usr/bin/env python
"""
Plot the mask generated and used by FinDer
"""
from argparse import ArgumentParser
import os

import cartopy
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from obspy import read_inventory
import xarray as xr


def main(fnmask, inv, outdir):
    xdf = xr.open_dataarray(fnmask)
    x = xdf.x.values
    y = xdf.y.values
    z = xdf.values
    xx, yy = np.meshgrid(x, y)

    fig = plt.figure(figsize=(12,12))
    ax = fig.add_axes()
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([165, 180, -47, -40])
    ax.coastlines()
    ax.scatter(xx.ravel(), yy.ravel(),
             c=z.ravel(), s=.01, marker='.',
             transform=ccrs.PlateCarree())

    station_coords = {}
    for st in inv.networks[0]:
        invst = inv.select(network='NZ', station=st.code, location='*', channel='*').networks[0].stations[0]
        lat = invst.latitude
        lon = invst.longitude
        label = invst.code
        station_coords[st.code] = (lon, lat)
        
    for _, coord in station_coords.items():
        ax.plot(*coord, marker='^', color='black')
        
    plt.savefig(os.path.join(outdir, 'finder_mask.png'), dpi=300)
    

if __name__ == '__main__':
    parser = ArgumentParser(prog='gen_config.py',
                            description=__doc__.strip())
    parser.add_argument('maskfile', type=str,
                        help='Path to FinDer mask file.')
    parser.add_argument('inventory', type=str,
                        help='Inventory file.')
    parser.add_argument('outdir', type=str,
                        help='Directory to write plot to.')
    args = parser.parse_args()
    maskfile = args.maskfile
    outdir = args.outdir
    inv = read_inventory(args.inventory)
    try:
        os.makedirs(outdir)
    except FileExistsError:
        pass
    main(maskfile, inv, outdir)