#!/usr/local/bin/python3

import argparse
import subprocess
import logging
import os.path
import sys
import pytds
import pprint
from meraki import meraki

import config
pp = pprint.PrettyPrinter(indent=4)

myNetworks = meraki.getnetworklist(config.api_key, config.org_id)
network_id = ([d for d in myNetworks if d['name'] == config.network_name][0]['id'])

devices = meraki.getnetworkdevices(config.api_key,network_id)
