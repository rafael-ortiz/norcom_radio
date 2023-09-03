
DEBUG = False
LOGFILE = None

MQTT_ENABLE = False

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
OUTPUT_FORMAT = "json"


try:
    from local_settings import *
except ImportError:
    pass
