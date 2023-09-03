#!/usr/bin/env python3

import re
import json
import os
import sys
import time
import ssl
import random
import logging

import paho.mqtt.client as mqtt

import utils
import settings
import PageParser

logger = logging.getLogger(__name__)

def mqtt_on_publish(client, userdata, mid):
    logger.debug("[MQTT] Published message id %d", mid)

def mqtt_on_log(client, userdata, level, buf):
    logging.debug(buf)

def mqtt_on_disconnect(client, userdata, rc):
    logging.info("MQTT client disconnected")

def publish_page(page, mqtt_client):
    # this is where all the various outputs would go
    topic = "page/{}/{}".format(str(page.agency), page.call_type)

    logging.info("Publishing page to MQTT topic %s", topic)

    message = page.to_json()

    res = mqtt_client.publish(
        topic=topic,
        payload=message.encode('utf-8')
    )
    logging.debug("Message %d queued for publishing", res.mid)
    # res.wait_for_publish()


def init_logging(settings):
    """Setup logging """

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


def init_mqtt(mqtt_config):
    def mqtt_on_connect(client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT broker")
        else:
            logging.error("Failed to connect to MQTT broker: return code %d", rc)

    broker = mqtt_config.get('HOST', None)

    if broker is None:
        logging.error("Failed to init mqtt: invalid or missing hostname")
        return None

    try:
        port = int(mqtt_config.get('PORT', 1883))
    except (TypeError, ValueError):
        logging.error("Failed to init mqtt: invalid port number")
        return None

    client_id = f'norcom-pager-{random.randint(0, 1000)}'

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
        logging.error("Failed to connect to broker %s", err)
        return None
    return client

def create_page(raw_page, capcode, page_alpha):
    
    agency = PageParser.PageAgency.from_capcode(capcode)

    if agency == PageParser.PageAgency.NORCOM:
        return PageParser.PageNorcom(raw=raw_page, capcode=capcode, alpha=page_alpha)
    elif agency == PageParser.PageAgency.VALCOM:
        # Use the NORCOM processor until we see enough of them to decide otherwise
        return PageParser.PageNorcom(raw=raw_page, capcode=capcode, alpha=page_alpha)
    elif agency == PageParser.PageAgency.SNO911:
        return PageParser.PageSnohomish(raw=raw_page, capcode=capcode, alpha=page_alpha)
    else:
        # Unknown capcode
        # TODO: add some logging
        print("Unknown CAPCODE: {}".format(raw_page))
        return None

    return None



def main():
    parser = utils.setup_parser()
    args = parser.parse_args()
    settings = utils.init_settings(args)

    try: 
        init_logging(settings)
    except OSError as err:
        logger.error("Failed to open log file %s", err)
        sys.exit(1)

    logger.info("Initialized logging")

    mclient = None
    if getattr(settings, 'MQTT_ENABLE', False):
        mclient = init_mqtt(getattr(settings, 'MQTT', {}))
        if mclient is None:
            sys.exit(1)

        # Block while we wait - this probably needs some safeties added
        while not mclient.is_connected():
            pass

    page_pattern = re.compile(r"POCSAG1200:\s+Address:\s+(\d+)\s+Function:\s+\d\s+Alpha:\s+(.*)$")

    while True:
        try:
            for line in sys.stdin:
                line = line.strip()

                logger.debug("Received %s", " ".join(line.split()[:3]))
                matches = page_pattern.match(line)
                
                if matches is None:
                    logger.info("Ignoring page: unknown page format")
                    logger.debug("Unknown format: %s", line)
                    continue

                try:
                    raw_page = matches.group(0)
                    capcode = matches.group(1)
                    alpha = matches.group(2)
                except IndexError as err:
                    # invalid or malformed page
                    logger.info("Ignoring page: malformed or invalid format")
                    logger.debug("%s: %s", err, line)
                    return None

                # TODO: Add some capcode matching and/or filtering
                page = create_page(raw_page, capcode, alpha)
                
                if page is not None:
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
                            publish_page(page, mclient)
                    else:
                        page = None
                        continue
                else:
                    logger.warn("Failed to parse page: %s", line)
                    continue
            # break
        except KeyboardInterrupt:
            if mclient is not None:
                mclient.disconnect(reasoncode=0)
            print("")
            sys.exit(0)



main()