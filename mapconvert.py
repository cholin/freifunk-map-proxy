#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cgi
import json
import logging
import logging.handlers
import urllib2
import cgitb
import sys
import os

from StringIO import StringIO
from lxml import etree
from lxml.cssselect import CSSSelector
from datetime import datetime

# globals
MAP_URL = 'http://openwifimap.net/map.html'
API_URLS = ['http://api.openwifimap.net/']
LOG_FILE = os.path.join('logs', 'mapconvert.log')

# enable debugging
cgitb.enable()

# logger
logging.basicConfig(format='\n%(asctime)s\n%(message)s\n')
logger = logging.getLogger('mapconvert')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.handlers.RotatingFileHandler(LOG_FILE,
                    maxBytes=100*1024, backupCount=3))
logger.addHandler(logging.StreamHandler(sys.stdout))

# parse parameters
form = cgi.FieldStorage()
data = {
   'script' : 'freifunk-map-proxy',
}

for k in form.keys():
    value = form[k].value.decode('utf-8', 'ignore')
    escaped = cgi.escape(value)

    if k == "note":
        note = urllib2.unquote(value)
        # official freifunk-mapupdate script
        if all(s in note for s in ['<a','</a>', '<p>']):
            # we would need beautiful soup but on vm-userpages
            # we only have python2.6.... so let's use lxml :/
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(note), parser)
            sel_a = CSSSelector('a')
            sel_p = CSSSelector('p')
            data['hostname'] = sel_a(tree)[0].text
            data['freifunk'] = { 'contact' : {'note' : sel_p(tree)[0].text} }

        # old mapupdate scripts with only hostname in 'note'
        elif len(escaped) <= 32:
            data['hostname'] = escaped

        # all other horrible requests...
        else:
            data['freifunk'] = { 'contact' : {'note' : escaped } }

    elif k == "update" and "," in escaped:
        lat_long = escaped.split(',')
        data['latitude']  = float(lat_long[0])
        data['longitude'] = float(lat_long[1])

    elif any (k == x for x in ["olsrip", "batmanip"]):
        try:
            data['interfaces'].append({ 'ipv4Addresses' : escaped })
        except:
            data['interfaces'] = [{ 'ipv4Addresses' : escaped }]

    elif k == 'updateiv':
        data['updateInterval'] = int(escaped)

    else:
        data[k] = escaped

# if we did not get a hostname we try to use ipv4-Address instead
if 'hostname' not in data:
    try:
        data['hostname'] = data['interfaces'][0]['ipv4Addresses']
    except:
        pass

# bring the data into the database
saved_to = []
if all(k in data for k in ['hostname', 'longitude', 'latitude']):
    data['type'] = 'node'
    data['updateInterval'] = 86400 # one day

    for api_url in API_URLS:

        # only update if present doc was also sent by freifunk-map-proxy
        try:
            oldreq = urllib2.urlopen(api_url+'/db/'+data['hostname'])
            if oldreq.getcode()==200:
                olddata = json.loads(oldreq.read())
                if olddata['script'] != data['script']:
                    continue
        except urllib2.HTTPError:
            pass

        req = urllib2.urlopen(api_url+'/update_node/'+data['hostname'], json.dumps(data))
        if req.getcode()==201:
            saved_to.append(api_url)

if len(saved_to) > 0:
    print('Content-Type: text/plain;charset=utf-8\n')

    # log and print them
    msg = '\n'.join([
        "REQUEST: " + os.environ['QUERY_STRING'],
        "SAVED IN: " + (','.join(saved_to) or '-'),
        "DATA: " + json.dumps(data, indent = 4),
        ""
    ])
    logger.debug(msg)

else:
    print('Location: %s\n' % MAP_URL)
