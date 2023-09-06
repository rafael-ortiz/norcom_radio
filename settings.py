
DEBUG = False
LOGFILE = None

# Publish incident pages to MQTT
MQTT_ENABLE = False

# Publish Pagergate keepalives to MQTT
MQTT_PUBLISH_KEEPALIVES = True

# MQTT Broker config
MQTT = {
    'HOST': None,
    'PORT': 1883,
    'USER': None,
    'PASS': None,
}

# Save each page to a local file
OUTPUT_FILE = False
OUTPUT_FILE_PATH = None

## Format to write the output lines. Currently only json is supported
OUTPUT_FILE_FORMAT = "json"

# Write Pagergate keepalives to file
OUTPUT_FILE_KEEPALIVES = False


try:
    from local_settings import *
except ImportError:
    pass
