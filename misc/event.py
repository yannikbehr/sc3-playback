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
import geocoder

def event(baseurl='IRIS', 
          playback=None, 
          days=1, 
          qml=None,
	  fin=None,
	  tin=None,
	  country=None,
          **kwargs):

	try :
		client = Client(baseurl)
		print("Using "+baseurl+"...",file=sys.stderr)
	except :
		print("fdsn client failed",file=sys.stderr)
		from obspy.clients.fdsn.header import URL_MAPPINGS
		for key in sorted(URL_MAPPINGS.keys()):
			print("{0:<7} {1}".format(key,  URL_MAPPINGS[key]),file=sys.stderr)

                sys.exit()
	
        try :
                kwargs['starttime'] = UTCDateTime(kwargs['starttime'])
                kwargs['endtime'] = UTCDateTime(kwargs['endtime'])
        except :
                kwargs['starttime'] = UTCDateTime()-float(days)*24*60*60
                kwargs['endtime'] = UTCDateTime()

	print('kwargs:',kwargs,file=sys.stderr)
	try :
		cat = client.get_events(**kwargs)
	except : 
		print('No response.',file=sys.stderr)
		sys.exit()
	
	if country is not None:
		ok=False
		limit=len(cat.events)
		kwargs['offset']=len(cat.events)
		while not ok:
			ok=True
			remove=[]
			kwargs['limit']=0
			for i,e in enumerate(cat.events):
				lalo=[e.preferred_origin().latitude,
				     e.preferred_origin().longitude]
				gcode = geocoder.osm(lalo,method='reverse').json
				if gcode['country_code'].lower() not in country.lower():
					kwargs['limit']+=1
					ok=False
					remove+=[e]
					print('removing %d (%s, %s): %s (requesting %d after %d)'%(i,lalo[0],lalo[1],gcode['country_code'], kwargs['limit'],kwargs['offset']),file=sys.stderr)
			if not ok:
				for e in remove:
					cat.events.remove(e)
				if len(cat.events) >= limit:
					print('Clean stable catalog of %d events'%len(cat.events),file=sys.stderr)
					break
				print('kwargs:',kwargs,file=sys.stderr)
				try : 
					tmp = client.get_events(**kwargs)
				except : 
					print('No more events than %d'%len(cat.events),file=sys.stderr)
					break
				cat += tmp
				kwargs['offset']+=len(tmp.events)
	for e in cat.events:
		print( "Event \"%s\":\t%s" % (str(e.resource_id), e.short_str()), file=sys.stderr )
	
	if qml is not None:
		cat.write(qml,format='SC3ML')

	if fin is not None:
		with open(fin,'w') as f:
			f.write('\n'.join([str(e.resource_id) for e in cat.events])+'\n')
	if tin is not None:
		with open(tin,'w') as f:
			for e in cat.events:
				o=e.preferred_origin_id.get_referred_object()
				f.write('%s %s\n'%((o.time-60*3/9).strftime("%Y-%m-%dT%H:%M:%S"), (o.time+60*6/9).strftime("%Y-%m-%dT%H:%M:%S")))


	if playback is not None:
		if 'evid' in playback :
			for e in cat.events:
				print(playback %("\""+str(e.resource_id)+"\""))
		else:
			for e in cat.events:
				o=e.preferred_origin_id.get_referred_object()
				print(playback %((o.time-60*3/9).strftime("\"%Y-%m-%d %H:%M:%S\""), (o.time+60*6/9).strftime("\"%Y-%m-%d %H:%M:%S\"")))

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=__doc__,
				     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-b', '--baseurl',    help='base URL of any FDSN web service or with a shortcut name which will be mapped to a FDSN URL.', default="IRIS")
	parser.add_argument('-d', '--days',    help='How much days we look back in time.', default=365)
	parser.add_argument('-t', '--starttime',
				help='start time')
	parser.add_argument('-T', '--endtime' , 
				help='end time',
				default=str(datetime.now()))
        parser.add_argument('-m', '--minmagnitude', help='Minimum magnitude', default="2.")
        parser.add_argument('-M', '--maxmagnitude', help='Maximum magnitude', default="10.")
	parser.add_argument('-l', '--limit',     help='Maximum number of event', default="10")
	parser.add_argument('-f', '--fin',     help='file for evids', default=None)
	parser.add_argument('--tin',     help='file for time intervals', default=None)
	parser.add_argument('-q', '--qml',     help='file for quakeml', default=None)
	parser.add_argument('-c', '--catalog',     help='catalog to request', default=None)
        parser.add_argument('-C','--contributor', help='Contributor (agency) to request', default=None)
        parser.add_argument('--minlongitude', help='', default=None)
        parser.add_argument('--maxlatitude', help='', default=None)
        parser.add_argument('--minlatitude', help='', default=None)
        parser.add_argument('--maxlongitude', help='', default=None)
        parser.add_argument('--latitude', help='', default=None)
        parser.add_argument('--longitude', help='', default=None)
        parser.add_argument('--minradius', help='', default=None)
        parser.add_argument('--maxradius', help='', default=None)
        parser.add_argument('--mindepth', help='', default=None)
        parser.add_argument('--maxdepth', help='', default=None)
	parser.add_argument('--country', help='', default=None)
        parser.add_argument('--magnitudetype', help='', default=None)
        parser.add_argument('--eventtype', help='', default=None)
	parser.add_argument('--offset', help='', default=None)
        parser.add_argument('--orderby', help='', default='magnitude')
        parser.add_argument('--updatedafter', help='', default=None)
	parser.add_argument('--playback', 
				help='The call to playback.sh, replace argument of options evid or begin and end by %s, e.g., "playback.sh --begin %s --end %s all"', 
				default=None)
	args = parser.parse_args()
	#try:
	event(baseurl=args.baseurl,
		playback=args.playback, 
		days=args.days,
                fin=args.fin,
                tin=args.tin,
                qml=args.qml,
		country=args.country,
		starttime=args.starttime, 
		endtime=args.endtime, 
		minmag=args.minmagnitude, 
		maxmag=args.maxmagnitude, 
		limit=args.limit, 
		contributor=args.contributor,
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
		eventtype=args.eventtype,
		offset=args.offset,
		orderby=args.orderby,
		updatedafter=args.updatedafter)
	#except :
	#	print("event failed")
	#	sys.exit()

