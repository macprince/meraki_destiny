#!/usr/local/bin/python3
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
# Custom Imports
import pytds
from meraki import meraki

# Set up argparse
parser = argparse.ArgumentParser()
parser.add_argument("--debug",
                    help="Turns Debug Logging On.",
                    action="store_true")
parser.add_argument("--config",
                    help="Specify path to config.json",
                    default=os.path.join(sys.path[0],"config.json"))

args = parser.parse_args()
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

meraki_config = settings['meraki_dashboard']

def get_serials_from_dashboard():

    serials=[]
    networks = meraki.getnetworklist(meraki_config["api_key"], meraki_config["org_id"],suppressprint=True)
    hw_networks = [net for net in networks if net['type'] != "systems manager"]
    for network in hw_networks:
        devices = meraki.getnetworkdevices(meraki_config["api_key"],network['id'],suppressprint=True)
        for device in devices:
            serials.append(device['serial'])
    return serials

def get_device_data(serials, host, user, password, db):

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

def main():
        serials = get_serials_from_dashboard()

        server_settings = settings["server_info"]
        data = get_device_data(serials,
                               server_settings["server"],
                               server_settings["user"],
                               server_settings["password"],
                               server_settings["database"])

        logging.debug("Got device data from server!\n%s", data)
        if data is None:
            logging.error("No data")

        sys.exit(0)
if __name__ == '__main__':
    main()
