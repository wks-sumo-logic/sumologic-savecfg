#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exaplanation: sumologic_savecfg is a general object retrieval script

Usage:
   $ python  sumologic_savecfg [ options ]

Style:
   Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

    @name           sumocli_list_objects
    @version        1.00
    @author-name    Wayne Schmidt
    @author-email   wschmidt@sumologic.com
    @license-name   Apache 2.0
    @license-url    http://www.gnu.org/licenses/gpl.html
"""

__version__ = 1.00
__author__ = "Wayne Schmidt (wschmidt@sumologic.com)"

### beginning ###
import os
import sys
import time
import datetime
import argparse
import configparser
import importlib
import json
import http
import requests

sys.dont_write_bytecode = 1

MY_SLEEP = .5

CATEGORYBASE = 'sumologic/config'

CACHEDIR = os.path.join('/tmp', CATEGORYBASE )

os.makedirs(CACHEDIR, exist_ok=True)

RIGHTNOW = datetime.datetime.now()

DATESTAMP = RIGHTNOW.strftime('%Y%m%d')

TIMESTAMP = RIGHTNOW.strftime('%H%M%S')

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BINDIR = os.path.abspath(os.path.join(BASEDIR, 'bin'))

ETCDIR = os.path.abspath(os.path.join(BASEDIR, 'etc'))

LIBDIR = os.path.abspath(os.path.join(BASEDIR, 'lib'))

sys.path.append(LIBDIR)

JSONCFGTAG = 'sumologic_savecfg.json'

MY_CFG = 'undefined'

PARSER = argparse.ArgumentParser(description="""
sumologic_savecfg is a general object retrieval script
""")

PARSER.add_argument("-a", metavar='<secret>', dest='MY_SECRET', \
                    help="set api (format: <key>:<secret>) ")

PARSER.add_argument("-c", metavar='<configfile>', dest='CONFIG', \
                    help="Specify config file")

PARSER.add_argument("-q", metavar='<modulelist>', dest='QUERYNAME', \
                    default='all', help="Specify query to run")

PARSER.add_argument("-l", action='store_true', dest='LISTQUERY', \
                    default=False, help="List all supported Sumo Logic Queries")

PARSER.add_argument("-u", metavar='<sumourl>', dest='SUMOURL', \
                    help="Specify Sumo Logic Source URL")

PARSER.add_argument("-v", type=int, default=0, metavar='<verbose>', \
                    dest='verbose', help="increase verbosity")

ARGS = PARSER.parse_args()

def list_queries():
    """
    List all of the registered Sumo Logic Queries
    """

    jsoncfgfile = os.path.join(ETCDIR, JSONCFGTAG)

    padwidth = 60
    padchar = ' '

    with open(jsoncfgfile, "r", encoding='utf8' ) as fileobject:
        cfgobject = json.load(fileobject)

        for qkey,qpath in cfgobject.items():
            print(f'Query: {qkey :{padchar}<{padwidth}} URLPath: {qpath}')

    sys.exit()

if ARGS.LISTQUERY is True:
    list_queries()

def publish_data(payload_file,publishurl,publishcategory):
    """
    This publishes a file or string into Sumo Logic
    """

    session = requests.Session()

    headers = {}

    headers['Content-Type'] = 'text/csv'
    headers['Accept'] = 'text/csv'
    headers['X-Sumo-Category'] = publishcategory
    mimetype = 'text/csv'

    with open(payload_file, "r", encoding='utf8' ) as payload_object:
        payload = payload_object.read()

    postresponse = session.post(publishurl, data=payload, headers=headers).status_code

    if ARGS.verbose > 4:
        print(f'SUMOLOGIC_ENDPOINT: {publishurl}')
        print(f'SUMOLOGIC_CATEGORY: {publishcategory}')
        print(f'SUMOLOGIC_RESPONSE: {postresponse}')

    if ARGS.verbose > 6:
        print(f'HTTPS_APPTYPE: {mimetype}')
        print(f'HTTPS_HEADERS: {headers}')

    if ARGS.verbose > 8:
        print(f'HTTPS_PAYLOAD: {payload}')

def resolve_option_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    if ARGS.MY_SECRET:
        (keyname, keysecret) = ARGS.MY_SECRET.split(':')
        os.environ['SUMO_UID'] = keyname
        os.environ['SUMO_KEY'] = keysecret

    if ARGS.SUMOURL:
        os.environ['SUMO_URL'] = ARGS.SUMOURL

def resolve_config_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    if ARGS.CONFIG:
        cfgfile = os.path.abspath(ARGS.CONFIG)
        configobj = configparser.ConfigParser()
        configobj.optionxform = str
        configobj.read(cfgfile)

        if ARGS.verbose > 8:
            print('Displaying Config Contents:')
            print(dict(configobj.items('Default')))

        if configobj.has_option("Default", "SUMO_UID"):
            os.environ['SUMO_UID'] = configobj.get("Default", "SUMO_UID")

        if configobj.has_option("Default", "SUMO_KEY"):
            os.environ['SUMO_KEY'] = configobj.get("Default", "SUMO_KEY")

        if configobj.has_option("Default", "SUMO_URL"):
            os.environ['SUMO_URL'] = configobj.get("Default", "SUMO_URL")

def initialize_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    resolve_option_variables()

    resolve_config_variables()

    try:
        my_uid = os.environ['SUMO_UID']
        my_key = os.environ['SUMO_KEY']

    except KeyError as myerror:
        print(f'Environment Variable Not Set :: {myerror.args[0]}')

    return my_uid, my_key

### script logic  ###

( sumo_uid, sumo_key ) = initialize_variables()

def main():
    """
    Setup the Sumo API connection, using the required tuple of region, id, and key.
    Once done, then issue the command required
    """
    source = SumoApiClient(sumo_uid, sumo_key)

    jsoncfgfile = os.path.join(ETCDIR, JSONCFGTAG)

    querylist = []

    with open(jsoncfgfile, "r", encoding='utf8' ) as fileobject:
        cfgobject = json.load(fileobject)

    if ARGS.QUERYNAME == 'all':
        querylist = cfgobject.keys()
    else:
        if ARGS.QUERYNAME in cfgobject:
            querylist.append(ARGS.QUERYNAME)

    for queryname in querylist:

        module = importlib.import_module(queryname, package=None)

        output = module.get_and_format_output(source)

        output_file = os.path.join(CACHEDIR, f'{queryname}.csv')

        with open (output_file, "w", encoding='utf8') as output_object:
            output_object.write(output)

        source_category = os.path.join(CATEGORYBASE,queryname)

        if ARGS.verbose > 4:
            print(f'SOURCE_CATEGORY: {source_category}\n')

        if ARGS.verbose > 8:
            print(f'QUERY_OUTPUT:\n{output}')

        if os.environ['SUMO_URL']:
            publish_data(output_file,os.environ['SUMO_URL'],source_category)

        time.sleep(MY_SLEEP)

### script logic  ###
### class ###
class SumoApiClient():
    """
    This is defined SumoLogic API Client
    The class includes the HTTP methods, cmdlets, and init methods
    """

    def __init__(self, access_id, access_key, endpoint=None, cookie_file='cookies.txt'):
        """
        Initializes the Sumo Logic object
        """
        self.session = requests.Session()
        self.session.auth = (access_id, access_key)
        self.session.headers = {'content-type': 'application/json', \
            'accept': 'application/json'}
        cookiejar = http.cookiejar.FileCookieJar(cookie_file)
        self.session.cookies = cookiejar
        if endpoint is None:
            self.apipoint = self._get_endpoint()
        elif len(endpoint) < 3:
            self.apipoint = 'https://api.' + endpoint + '.sumologic.com/api'
        else:
            self.apipoint = endpoint
        if self.apipoint[-1:] == "/":
            raise Exception("Endpoint should not end with a slash character")

    def _get_endpoint(self):
        """
        SumoLogic REST API endpoint changes based on the geo location of the client.
        It contacts the default REST endpoint and resolves the 401 to get the right endpoint.
        """
        self.endpoint = 'https://api.sumologic.com/api'
        self.response = self.session.get('https://api.sumologic.com/api/v1/collectors')
        endpoint = self.response.url.replace('/v1/collectors', '')
        return endpoint

    def delete(self, method, params=None, headers=None, data=None):
        """
        Defines a Sumo Logic Delete operation
        """
        response = self.session.delete(self.apipoint + method, \
            params=params, headers=headers, data=data)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def get(self, method, params=None, headers=None):
        """
        Defines a Sumo Logic Get operation
        """
        response = self.session.get(self.apipoint + method, \
            params=params, headers=headers)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def post(self, method, data, headers=None, params=None):
        """
        Defines a Sumo Logic Post operation
        """
        response = self.session.post(self.apipoint + method, \
            data=json.dumps(data), headers=headers, params=params)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def put(self, method, data, headers=None, params=None):
        """
        Defines a Sumo Logic Put operation
        """
        response = self.session.put(self.apipoint + method, \
            data=json.dumps(data), headers=headers, params=params)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

### class ###
### methods ###

    def get_object(self,objectpath):
        """
        Using an HTTP client, this uses a GET to retrieve information.
        """
        url = str(objectpath)
        body = self.get(url).text
        results = json.loads(body)
        return results

### methods ###
if __name__ == '__main__':
    main()
