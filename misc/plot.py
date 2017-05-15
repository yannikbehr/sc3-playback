#!/usr/bin/env python
"""
Plots playback.
Created on Dec 11, 2016

@author: fmassin
"""
import matplotlib.pyplot as plt
from obspy import UTCDateTime


def plot_vsreports(vsreport_pb=None,
                    vsreport_rt=None,
                    vsreport=None,
                    mag=None,
                    lon=None,
                    lat=None,
                    dep=None,
                    to=None):
    separator = '|'
    figsizes=[(14,6),(16,6)]
    colors = ['b', 'g', 'r','c', 'm', 'y', 'k']
    code = ['', 'RT', 'Pb']
    fig, (ax1, ax2, ax3) = plt.subplots(3,1, sharex=True)#, figsize=figsizes[0])
    f=-1
    for f,file in enumerate([vsreport, vsreport_rt, vsreport_pb]):
        if file:
            print(file)
            m=f
            vsfile = [x.split(separator) for x in open(file).readlines()]
            vsfile.append(vsfile[-1])#.copy())
            if mag:
                vsfile[-1][0]=mag
            if lat:
                vsfile[-1][1]=lat
            if lon:
                vsfile[-1][2]=lon
            if dep:
                vsfile[-1][4]=dep
            if to:
                 vsfile[-1][6]=to
            lab1 = 'Mvs'
            for o,origin in enumerate(vsfile):
                if o>1:
                    for v,val in enumerate(origin):
                        if 'Z' in str(val):
                            pass
                        else:
                            vsfile[o][v]=float(val)

            for o,origin in enumerate(vsfile):
                if o>1 :#and o<len(vsfile)-1:
                    if o>2:
                        lab1 = None
                        lab2 = None
                        lab3 = None
                        lab4 = None
                    else:
                        lab1 = code[f]+' Mvs'
                        lab2 = code[f]+' locsat'
                        lab3 = code[f]+' arrivals'
                        lab4 = code[f]+' amplitudes'
                    origin[5] = UTCDateTime(origin[5])
                    origin[6] = UTCDateTime(origin[6])
                    delays = origin[5] - UTCDateTime(vsfile[-1][6]) # origin[6]
                    ax1.plot(delays, origin[0], marker='o', label=lab1, color=colors[f])
                    ax2.plot(delays,
                        (((origin[1]-vsfile[-1][1])*110.)**2+((origin[2]-vsfile[-1][2])*110.)**2+(origin[4]-vsfile[-1][4])**2)**.5,
                        label=lab2, marker='o', color=colors[f])
                    ax3.plot(delays, origin[-2], marker='o', label=lab3, color=colors[f])
                    ax3.plot(delays, origin[-1], marker='d', label=lab4, color=colors[f])

                if o==len(vsfile)-1:
                    ax1.plot([UTCDateTime(vsfile[2][5]) - UTCDateTime(vsfile[-1][6])  , UTCDateTime(origin[5])-UTCDateTime(vsfile[-1][6])], [origin[0],origin[0]], color='g')
                    #ax2.plot([vsfile[2][5]-vsfile[2][6] ,origin[5] - origin[6]],
                    #    [(((origin[1]-vsfile[-1][1])*110.)**2+((origin[2]-vsfile[-1][2])*110.)**2+(origin[4]-vsfile[-1][4])**2)**.5,
                    #    (((origin[1]-vsfile[-1][1])*110.)**2+((origin[2]-vsfile[-1][2])*110.)**2+(origin[4]-vsfile[-1][4])**2)**.5],
                    #    color='g')
                    #ax3.plot(delays, origin[-2], marker='o', label=lab3, color=colors[f])
                    #ax3.plot(delays, origin[-1], marker='d', label=lab4, color=colors[f])

    ax1.set_title('M'+str(vsfile[-1][0])+' on '+str(vsfile[-1][6]))
    ax1.grid()
    ax2.grid()
    ax3.grid()
    ax1.set_xscale('log')
    ax2.set_xscale('log')
    ax3.set_xscale('log')
    ax1.set_ylim(top=ax1.get_ylim()[1]+0.1)
    ax2.set_ylim(bottom=ax2.get_ylim()[0]-1)
    ax1.set_ylabel('Magnitude')
    ax2.set_ylabel('Location error (km)')
    ax3.set_ylabel('Observations')
    ax3.set_xlabel('Alert time since origin [s]')

    ax1.legend(loc=4, fancybox=True, framealpha=0.5)
    ax2.legend(loc=3, fancybox=True, framealpha=0.5)
    ax3.legend(loc=5, fancybox=True, framealpha=0.5)
    print(file[:-3]+'pdf')
    plt.savefig(file[:-3]+'pdf', bbox_inches='tight')
    plt.show()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument("-v", "--vsreport", help="VS report file.", type=str)
    parser.add_argument("-r", "--vsreport_rt", help="RT VS report file.", type=str)
    parser.add_argument("-p", "--vsreport_pb", help="Pb VS report file.", type=str)
    parser.add_argument("-x", "--xml", help="xml file.", type=str)
    parser.add_argument("-m", "--mag", help="final magnitude.", type=str)
    parser.add_argument("-l", "--lon", help="final longitude.", type=str)
    parser.add_argument("-L", "--lat", help="final latitude.", type=str)
    parser.add_argument("-d", "--dep", help="final depth.", type=str)
    parser.add_argument("-t", "--to", help="final origin time.", type=str)

    args = parser.parse_args()

    plot_vsreports(vsreport=args.vsreport,
        vsreport_pb=args.vsreport_pb,
        vsreport_rt=args.vsreport_rt,
        mag=args.mag,
        lon=args.lon,
        lat=args.lat,
        dep=args.dep,
        to=args.to)
