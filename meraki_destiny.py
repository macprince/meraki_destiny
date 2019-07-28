#!/usr/local/bin/python3

#import argparse
#import subprocess
#import logging
#import os.path
#import sys
#import pytds
import pprint
from meraki import meraki

import config
pp = pprint.PrettyPrinter(indent=4)

networks = meraki.getnetworklist(config.api_key, config.org_id)
hw_networks = [net for net in networks if net['type'] != "systems manager"]

for network in hw_networks:
    print(network['type'])
    #devices = meraki.getnetworkdevices(config.api_key,network['id'])