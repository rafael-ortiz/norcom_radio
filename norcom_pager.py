#!/usr/bin/env python3

import os
import sys
import random
import logging
import argparse
import json
import time
# import re
# import ssl

import paho.mqtt.client as mqtt

import settings
from PageParser import PageParser
from PageParser import PageAgency

logger = logging.getLogger(__name__)

def mqtt_on_publish(client, userdata, mid):
    """ Callback for mqtt client publish() """
    logger.debug("[MQTT] Published message id %d", mid)

def mqtt_on_log(client, userdata, level, buf):
    """ Callback for mqtt client logging """
    logger.debug(buf)

def mqtt_on_disconnect(client, userdata, rc):
    """ Client for mqtt dicsconnects """
    logger.info("MQTT client disconnected")

def publish_page(data, mqtt_client):
    """ Publish unparsed page text to mqtt broker """

    topic = "page/text/{}".format(data['agency'].lower())

    logger.info("Publishing page to MQTT topic %s", topic)

    message = json.dumps(data)

    res = mqtt_client.publish(
        topic=topic,
        payload=message.encode('utf-8')
    )
    logger.debug("Message %d queued for publishing", res.mid)


def publish_incident(page, mqtt_client):
    """ Publish the parsed page to mqtt broker """

    if page.keepalive:
        topic = "page/pagegate_keepalive"
    else:
        topic = "page/{}/{}".format(
            str(page.agency).lower(),
            str(page.call_type).replace(" ", "_").replace("/", "_").lower()
        )

    logger.info("Publishing incident to MQTT topic %s", topic)

    message = page.to_json()

    res = mqtt_client.publish(
        topic=topic,
        payload=message.encode('utf-8')
    )
    logger.debug("Message %d queued for publishing", res.mid)
    # res.wait_for_publish()

def write_incident(page, fh, format="json"):
    """ Write contents of a page to file """
    logger.info("Writing page to file")

    try:
        fh.write("{},\n".format(page.to_json()))
    except OSError as err:
        logger.error("Failed to write to file: %s", err)
        return False
    
    return True

def init_args():
    """ Create argument parser and add arguments. """
    argparser = argparse.ArgumentParser(
        description="NORCOM Page Collector"
    )

    argparser.add_argument('-d', '--debug', action='store_true', help="Enable Debug Output")
    argparser.add_argument('-o', '--output', help='Output file')
    argparser.add_argument('-f', '--format', help='Output format (json, csv)')
    argparser.add_argument('-m', '--mqtt', help='MQTT host')
    argparser.add_argument('-p', '--port', help='MQTT Port')
    argparser.add_argument('-t', '--topic', help='MQTT subscribe topic')
    return argparser

def init_settings(cli_args):
    """ Update global settings based on cli arguments """

    if cli_args.debug:
        settings.DEBUG = True

    if cli_args.output:
        settings.OUTPUT_FILE_PATH = os.path.expanduser(cli_args.output)
        settings.OUTPUT_FORMAT = cli_args.format or "json"
        settings.OUTPUT_FILE = True

    if cli_args.mqtt:
        settings.MQTT['HOST'] = cli_args.host
        settings.MQTT['PORT'] = cli_args.port
        if ( settings.MQTT['HOST'] and settings.MQTT['PORT'] ):
            settings.MQTT_ENABLE = True

    return settings

def init_logging(settings):
    """ initialize logger """

    logfile = getattr(settings, "LOGFILE", None)
    if logfile is not None:
        logfile = os.path.expanduser(logfile)
    
    loglevel = getattr(settings, "LOGLEVEL", logging.INFO)
    debug = getattr(settings, "DEBUG", False) or (loglevel == logging.DEBUG)
    
    if debug:
        loglevel = logging.DEBUG
        logformat = '[%(asctime)s] %(levelname)s %(module)s.%(funcName)s %(message)s'
    else:
        logformat = '[%(asctime)s] %(levelname)s %(message)s'

    logging.basicConfig(filename=logfile, format=logformat, datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)

def init_outfile(outfile_path):
    """ Initialize output file """
    # TODO: add some way to rotate or split files
    
    if outfile_path is None:
        return None

    outfile = os.path.expanduser(outfile_path)

    try:
        fh = open(outfile, 'a')
    except OSError as err:
        logger.error("Failed to open output file %s", err)
        return None
    
    logger.info("Saving page data to %s", outfile)
    return fh


def init_mqtt(mqtt_config):
    """ 
    Connect to the mqtt broker and return a client object

    mqtt_config (dict) with the necessary config elements

        MQTT = {
            'HOST': None,
            'PORT': 1883,
            'USER': None,
            'PASS': None,
        }    
    """
    # TODO: Add TLS support

    def mqtt_on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT broker")
        else:
            logger.error("Failed to connect to MQTT broker: return code %d", rc)

    broker = mqtt_config.get('HOST', None)

    if broker is None:
        logger.error("Failed to init mqtt: invalid or missing hostname")
        return None

    try:
        port = int(mqtt_config.get('PORT', 1883))
    except (TypeError, ValueError):
        logger.error("Failed to init mqtt: invalid port number")
        return None

    client_id = "norcom-pager-{}".format(random.randint(0, 1000))

    # Set Connecting Client ID
    client = mqtt.Client(client_id)
    if mqtt_config.get('USER', ''):
        client.username_pw_set(mqtt_config['USER'], mqtt_config.get('PASS', ''))

    client.on_log=mqtt_on_log
    client.on_connect = mqtt_on_connect
    client.on_disconnect=mqtt_on_disconnect
    client.on_publish=mqtt_on_publish
    
    logger.info("Connecting to MQTT broker at {}:{}...".format(broker, port))
    try:
        client.connect(broker, port)
        client.loop_start()
    except OSError as err:
        logger.error("Failed to connect to broker %s", err)
        return None
    return client

def main():
    argparser = init_args()
    args = argparser.parse_args()
    settings = init_settings(args)

    try: 
        init_logging(settings)
    except OSError as err:
        logger.error("Failed to open log file %s", err)
        sys.exit(1)

    logger.info("Initialized logging")

    outfile = None
    if getattr(settings, 'OUTPUT_FILE', None):
        outfile = init_outfile(getattr(settings, 'OUTPUT_FILE_PATH', None))
        if outfile is None:
            sys.exit(1)

    mclient = None
    if getattr(settings, 'MQTT_ENABLE', False):
        mclient = init_mqtt(getattr(settings, 'MQTT', {}))
        if mclient is None:
            sys.exit(1)

        # Block while we wait - this probably needs some safeties added
        while not mclient.is_connected():
            pass

    parser = PageParser()

    ka_last_received = time.time()
    ka_last_missed = 0
    
    while True:
        try:
            for line in sys.stdin:
                line = line.strip()

                logger.debug("Received %s", " ".join(line.split()[:5]))

                page = parser.parse(line)

                if page is None:
                    continue

                if page.parsed:
                    logger.info("Parsed %s page to %s: %s; %s; %s",
                                page.agency,
                                page.capcode,
                                page.get_calltype(),
                                page.channel,
                                page.address_raw
                            )
                    # print(page.to_json())
                    if mclient is not None:
                        publish_incident(page, mclient)
                    if outfile is not None:
                        write_incident(page, outfile)
                elif page.keepalive:
                    ka_last_received = page.timestamp
                    logger.info("Parsed %s page to %s: %s",
                                page.agency,
                                page.capcode,
                                page.get_calltype()
                            )
                    if mclient is not None:
                        if getattr(settings, 'MQTT_PUBLISH_KEEPALIVES', True):
                            publish_incident(page, mclient)

                    if outfile is not None:
                        if getattr(settings, 'OUTPUT_FILE_KEEPALIVES', False):
                            write_incident(page, outfile)
                elif page.agency == PageAgency.NORCOM:
                    # Couldn't parse as an incident page, but we'll 
                    # see if the page text is worth grabbing

                    if not mclient:
                        page = None
                        continue

                    # Make sure it's not a SNO011 page sent to NORCOM capcodes (mutual-aid)
                    if page.alpha.startswith('>>'):
                        page = None
                        continue

                    page_text = page.alpha.replace("<EOT>","").replace("<NUL>","")

                    if len(page_text) < 1:
                        page = None
                        continue

                    if not " " in page_text:
                        page = None
                        continue


                    logger.info("Raw Alpha: %s", page.alpha)
                        
                    page_data = {
                        'timestamp': page.timestamp,
                        'text': page_text,
                        'agency': str(page.agency),
                        'capcode': page.capcode,
                    }

                    publish_page(page_data, mclient)

                else:
                    page = None

            #check if we've missed a keepalive
            ka_check = time.time()
            ka_max = getattr(settings, 'KEEPALIVE_MISSED', 3) * 1
            ka_interval = getattr(settings, 'KEEPALIVE_INTERVAL', 3) * 1
            ka_delta = round(ka_check - ka_last_missed) if (ka_last_missed > 0) else round(ka_check - ka_last_received)

            if (ka_delta > ka_interval):
                logger.info("No keepalive received for %d seconds", ka_interval)
                ka_last_missed = ka_check

                if ka_max > 0:
                    if round(ka_check - ka_last_received) >= (ka_interval * ka_max):
                        logger.error("Too many missed keepalives, I'm giving up.")
                        if mclient is not None:
                            mclient.disconnect(reasoncode=0)
                        sys.exit(1)

                # break
        except KeyboardInterrupt:
            if mclient is not None:
                mclient.disconnect(reasoncode=0)
            print("")
            sys.exit(0)


main()