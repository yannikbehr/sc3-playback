#!/usr/bin/env python

"""
Select event ID from time and magnitude intervals.
"""
from __future__ import print_function
import sys
from obspy import UTCDateTime	
from obspy.clients.fdsn import Client
import argparse
from datetime import datetime, timedelta

def event(baseurl='IRIS', **kwargs):
#		baseurl='IRIS', 
#		starttime=None, 
#		endtime=None,
#		minmag=3., 
#		maxmag=10., 
#		maxnumber=10, 
#		catalog=None):

	try :
		client = Client(baseurl)
		print("Using "+baseurl+"...",file=sys.stderr)
	except :
		print("fdsn client failed")
		from obspy.clients.fdsn.header import URL_MAPPINGS
		for key in sorted(URL_MAPPINGS.keys()):
			print("{0:<7} {1}".format(key,  URL_MAPPINGS[key]),file=sys.stderr)

                sys.exit()
	
        try :
                kwargs['starttime'] = UTCDateTime(kwargs['starttime'])
                kwargs['endtime'] = UTCDateTime(kwargs['endtime'])
        except :
                kwargs['starttime'] = UTCDateTime()-365*24*60*60
                kwargs['endtime'] = UTCDateTime()
                print('Auto time limit:',file=sys.stderr)
                print(starttime,file=sys.stderr)
                print(endtime,file=sys.stderr)
                #print("time conversion failed")
                #sys.exit()

        cat = client.get_events( **kwargs )
	
	#if catalog:
	#	cat = client.get_events(limit=maxnumber, orderby="magnitude",starttime=starttime, endtime=endtime, minmagnitude=minmag, maxmagnitude=maxmag, catalog=catalog)
	#else:
	#	cat = client.get_events(limit=maxnumber, orderby="magnitude",starttime=starttime, endtime=endtime, minmagnitude=minmag, maxmagnitude=maxmag)

	print(cat.__str__(print_all=True),file=sys.stderr)
	for e in cat:
		print(e.resource_id)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__,
				     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-b', '--baseurl',    help='base URL of any FDSN web service or with a shortcut name which will be mapped to a FDSN URL.', default="IRIS")
	parser.add_argument('-t', '--starttime',    help='start time',          default=str(datetime.now()-timedelta(days=365.)))
	parser.add_argument('-T', '--endtime' , help='end time',        default=str(datetime.now()))
        parser.add_argument('-m', '--minmagnitude', help='Minimum magnitude', default="2.")
        parser.add_argument('-M', '--maxmagnitude', help='Maximum magnitude', default="10.")
	parser.add_argument('-l', '--limit',     help='Maximum number of event', default="10")
	parser.add_argument('-c', '--catalog',     help='catalog to request', default=None)
        parser.add_argument('--minlatitude', help='', default=None)
        parser.add_argument('--maxlatitude', help='', default=None)
        parser.add_argument('--minlongitude', help='', default=None)
        parser.add_argument('--maxlongitude', help='', default=None)
        parser.add_argument('--latitude', help='', default=None)
        parser.add_argument('--longitude', help='', default=None)
        parser.add_argument('--minradius', help='', default=None)
        parser.add_argument('--maxradius', help='', default=None)
        parser.add_argument('--mindepth', help='', default=None)
        parser.add_argument('--maxdepth', help='', default=None)
        parser.add_argument('--magnitudetype', help='', default=None)
        parser.add_argument('--offset', help='', default=None)
        parser.add_argument('--orderby', help='', default='magnitude')
        parser.add_argument('--contributor', help='', default=None)
        parser.add_argument('--updatedafter', help='', default=None)
	args = parser.parse_args()
	#try:
	event(baseurl=args.baseurl, 
		starttime=args.starttime, 
		endtime=args.endtime, 
		minmag=args.minmagnitude, 
		maxmag=args.maxmagnitude, 
		limit=args.limit, 
		catalog=args.catalog,
		minlatitude=args.minlatitude,
		maxlatitude=args.maxlatitude,
		minlongitude=args.minlongitude,
		maxlongitude=args.maxlongitude,
		latitude=args.latitude,
		longitude=args.longitude,
		minradius=args.minradius,
		maxradius=args.maxradius,
		mindepth=args.mindepth,
		maxdepth=args.maxdepth,
		magnitudetype=args.magnitudetype,
		offset=args.offset,
		orderby=args.orderby,
		contributor=args.contributor,
		updatedafter=args.updatedafter)
	#except :
	#	print("event failed")
	#	sys.exit()

