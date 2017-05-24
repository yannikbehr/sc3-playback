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

def event(baseurl='IRIS', 
		starttime=None, 
		endtime=None,
		minmag=3., 
		maxmag=10., 
		maxnumber=10, 
		catalog=None):

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
		starttime = UTCDateTime(starttime)
		endtime = UTCDateTime(endtime)
	except :
		starttime = UTCDateTime()-365*24*60*60
        	endtime = UTCDateTime()
		print('Auto time limit:',file=sys.stderr)
		print(starttime,file=sys.stderr)
		print(endtime,file=sys.stderr) 
		#print("time conversion failed")
                #sys.exit()
	
	if catalog:
		cat = client.get_events(limit=maxnumber, orderby="magnitude",starttime=starttime, endtime=endtime, minmagnitude=minmag, maxmagnitude=maxmag, catalog=catalog)
	else:
		cat = client.get_events(limit=maxnumber, orderby="magnitude",starttime=starttime, endtime=endtime, minmagnitude=minmag, maxmagnitude=maxmag)
	print(cat.__str__(print_all=True),file=sys.stderr)
	for e in cat:
		print(e.resource_id)

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__,
				     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-b', '--baseurl',    help='base URL of any FDSN web service or with a shortcut name which will be mapped to a FDSN URL.', default="IRIS")
	parser.add_argument('-t', '--starttime',    help='end time',          default=str(datetime.now()-timedelta(days=365.)))
	parser.add_argument('-T', '--endtime' , help='start time',        default=str(datetime.now()))
	parser.add_argument('-m', '--minmag',     help='Minimum magnitude', default="2.")
	parser.add_argument('-M', '--maxmag',     help='Maximum magnitude', default="10.")
	parser.add_argument('-N', '--maxnumber',     help='Maximum number of event', default="10")
	parser.add_argument('-c', '--catalog',     help='catalog to request', default=None)

	args = parser.parse_args()
	#try:
	event(baseurl=args.baseurl, starttime=args.starttime, endtime=args.endtime, minmag=args.minmag, maxmag=args.maxmag, maxnumber=args.maxnumber, catalog=args.catalog)
	#except :
	#	print("event failed")
	#	sys.exit()

