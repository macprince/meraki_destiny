#!/usr/bin/env python3
'''
Set Notes field of Meraki devices for a given Dashboard organization to asset tag as pulled from Follett Destiny
'''
# Standard Imports
import json
import argparse
import subprocess
import logging
import os.path
import sys
import re
# Custom Imports
import pytds
import meraki

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument("--debug",
                    help="Turns Debug Logging On.",
                    action="store_true")
parser.add_argument("--config",
                    help="Specify path to config.json",
                    default=os.path.join(sys.path[0],"config.json"))

args = parser.parse_args()

# Set up logging
level = logging.INFO
if args.debug:
    level = logging.DEBUG
logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %I:%M:%S %p',
                    level=level,
                    filename=os.path.join(sys.path[0],'meraki_destiny.log'))
stdout_logging = logging.StreamHandler()
stdout_logging.setFormatter(logging.Formatter())
logging.getLogger().addHandler(stdout_logging)
config = os.path.abspath(args.config)
try:
    with open(config) as config_file:
        settings = json.load(config_file)
except IOError:
    logging.error("No config.json file found! Please create one!")
    sys.exit(2)

# Read in config
meraki_config = settings['meraki_dashboard']
destiny_config = settings['server_info']

# Set up regular expression for asset tag
re_tag = re.compile('Asset: \d{6}')

def get_dashboard_network_ids():
    network_ids=[]
    networks = meraki.getnetworklist(meraki_config["api_key"], meraki_config["org_id"],suppressprint=True)
    hw_networks = [net for net in networks if net['type'] != "systems manager"]
    for network in hw_networks:
        network_ids.append(network['id'])
    return network_ids

def get_serials_from_dashboard(network_id):
    serials=[]
    devices = meraki.getnetworkdevices(meraki_config["api_key"],network_id,suppressprint=True)
    for device in devices:
        if not 'notes' in device:
            serials.append(device['serial'])
        elif not re_tag.match(device['notes']):
            serials.append(device['serial'])
    return serials

def get_device_data(serials, host, user, password, db):
    if len(serials) == 1:
        barcode_cmd = "SELECT SerialNumber, CopyBarcode FROM CircCatAdmin.CopyAssetView WHERE SerialNumber = '{0}'".format(serials[0])
    else:
        barcode_cmd = "SELECT SerialNumber, CopyBarcode FROM CircCatAdmin.CopyAssetView WHERE SerialNumber IN {}".format(tuple(serials))

    db_host = host
    db_user = user
    db_password = password
    db_name = db
    try:
        with pytds.connect(db_host, database=db_name, user=db_user,
                           password=db_password, as_dict=True) as conn:
            logging.debug("Server Connection Success")
            with conn.cursor() as cur:
                cur.execute(barcode_cmd)
                logging.debug("Lookup Command Executed")
                devicedata = (cur.fetchall())
                logging.debug("Date retrieved, closing connection")

    except pytds.tds.LoginError:
        logging.error("Unable to connect to server! Connection may have timed out!")
        sys.exit(2)
    cur.close()
    conn.close()

    return devicedata

def write_to_meraki(network_id, data):
    if data:
        for device in data:
            serial = device['SerialNumber'].upper()
            asset_tag = device['CopyBarcode']
            meraki.updatedevice(meraki_config["api_key"],network_id,serial,notes=f"Asset: {asset_tag}",suppressprint=True)
            logging.info(f"Device updated: {serial} – {asset_tag} ")
def main():
    network_ids = get_dashboard_network_ids()
    for network_id in network_ids:
        data = {}
        serials = get_serials_from_dashboard(network_id)

        if serials != []:
            data = get_device_data(serials,
                                   destiny_config["server"],
                                   destiny_config["user"],
                                   destiny_config["password"],
                                   destiny_config["database"])

            logging.debug("Got device data from server!\n%s", data)
            if data is None:
                logging.error("No data")
        write_to_meraki(network_id,data)

    sys.exit(0)
if __name__ == '__main__':
    main()
