import argparse
import os

import settings

def setup_parser():
    """ Create argument parser and add arguments. """
    parser = argparse.ArgumentParser(
        description="NORCOM Page Collector"
    )

    parser.add_argument('-d', '--debug', action='store_true', help="Enable Debug Output")

    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('-f', '--format', help='Output format (json, csv)')
    
    parser.add_argument('-m', '--mqtt', help='MQTT host')
    parser.add_argument('-p', '--port', help='MQTT Port')

    parser.add_argument('-t', '--topic', help='MQTT subscribe topic')

    return parser

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
