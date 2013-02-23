#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cgi
import json
import logging
import urllib2
import cgitb

from datetime import datetime
#from bs4 import BeautifulSoup

# enable debugging
cgitb.enable()

# logger
logging.basicConfig(filename='logs.txt', format='\n%(asctime)s\n%(message)s\n', level=logging.DEBUG)

# HTTP-HEADER
print('Content-Type: text/plain;charset=utf-8\n')

# parse parameters
form = cgi.FieldStorage()
data = {
  'type': 'node',
  'lastupdate' : datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
  'interfaces' : [],
}

for k in form.keys():
	escaped = cgi.escape(form[k].value)

  if k == "note":
    note = urllib2.unquote(form[k].value)
    if 'href' in note:
      # we would need beautiful soup but on vm-userpages
      # we only have python2.6.... :/
      #
      # b = BeautifulSoup(note)
      # data['hostname'] = b.find('a').text
      # data['freifunk'] = { 'contact' : {'note' : b.find('p').text } }
      data['freifunk'] = { 'contact' : {'note' : cgi.escape(note)} }
    else:
      data['hostname'] = escaped

  else:
    if k == "update":
      lat_long = escaped.split(',')
      data['latitude']  = lat_long[0]
      data['longitude'] = lat_long[0]
    elif k == "olsrip":
      data['interfaces'].append({ 'ipv4Addresses' : escaped })
    else:
      data[k] = escaped

# log and print them
s = json.dumps(data, indent = 4)
logging.debug(s)
print(s)