#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cgi
import json
import logging
import logging.handlers
import urllib2
import cgitb
import couchdb
import re
import os

from StringIO import StringIO
from lxml import etree
from lxml.cssselect import CSSSelector
from datetime import datetime

# globals
SERVERS = [('openwifimap.net','openwifimap')]
LOG_FILE = os.path.join('logs', 'mapconvert.log')

# helper methods
_punct_re = re.compile(r'[\t !"#$%&\'()*\/<=>?@\[\\\]^`{|},]+')
def slugify(text, delim=u'-'):
   """Generates an slightly worse ASCII-only slug."""
   result = []
   for word in _punct_re.split(text):
       if word:
           result.append(word)
   return delim.join(result)

# enable debugging
cgitb.enable()

# logger
logging.basicConfig(format='\n%(asctime)s\n%(message)s\n')
logger = logging.getLogger('mapconvert')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.handlers.RotatingFileHandler(LOG_FILE,
                    maxBytes=1024, backupCount=3))

# HTTP-HEADER
print('Content-Type: text/plain;charset=utf-8\n')

# parse parameters
form = cgi.FieldStorage()
data = {
   'script' : 'freifunk-map-proxy',
}

for k in form.keys():
    escaped = cgi.escape(form[k].value)

    if k == "note":
        note = urllib2.unquote(form[k].value)
        if all(s in note for s in ['<a','</a>', '<p>']):
            # we would need beautiful soup but on vm-userpages
            # we only have python2.6.... so let's use lxml :/
            parser = etree.HTMLParser()
            tree = etree.parse(StringIO(note), parser)
            sel_a = CSSSelector('a')
            sel_p = CSSSelector('p')
            data['hostname'] = sel_a(tree)[0].text
            data['freifunk'] = { 'contact' : {'note' : sel_p(tree)[0].text} }
        else:
            data['hostname'] = slugify(unicode(escaped, errors='ignore'))[:20]

    else:
        if k == "update":
            lat_long = escaped.split(',')
            data['latitude']  = float(lat_long[0])
            data['longitude'] = float(lat_long[1])
        elif k == "olsrip":
            try:
                data['interfaces'].append({ 'ipv4Addresses' : escaped })
            except:
                data['interfaces'] = [{ 'ipv4Addresses' : escaped }]
        else:
            data[k] = escaped


# bring the data into the database
saved_to = []
if all(k in data for k in ['hostname', 'longitude','latitude']):
    data['_id'] = data['hostname']

    for server, database in SERVERS:
        couch = couchdb.Server('http://%s' % server)
        db = couch[database]
        entry = db.get(data['_id'])
        if entry != None:
            data['_rev'] = entry['_rev']

            if entry['script'] != data['script']:
              continue

        data['type'] = 'node'
        data['lastupdate'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        if db.save(data):
          saved_to.append("%s/%s" % (server, database))


# log and print them
msg = '\n'.join([
    "REQUEST: " + os.environ['QUERY_STRING'],
    "SAVED IN: " + (','.join(saved_to) or '-'),
    "DATA: " + json.dumps(data, indent = 4),
    ""
])
logger.debug(msg)
