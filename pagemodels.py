import re
import coloredlogs, logging, verboselogs
from verboselogs import VerboseLogger as getLogger
import datetime

logger = getLogger(__name__)


class Page:
    page_type = None
    time = None
    address = None
    # location = None
    lat = None
    lon = None
    type = None
    type2 = None
    channel = None
    units = None
    pager_address = None
    description = None

    def __init__(self, page_type, address, payload):
        self.page_type = page_type
        self.pager_address = address
        self.description = payload
        self.time = datetime.datetime.now().isoformat()

    def __str__(self):
        return repr((self.__dict__))


class SnohomishPage(Page):
    pattern = "  >>([A-Z0-9\- ]+)<<(.+)"
    channel_pattern = " * FIRE ?TAC ?(\d\d)(.*)"
    location_pattern = " *([^\/]*) *\/ +([^\/]*) +\/ +(.*)"
    location_pattern2 = " *([^\/]*) *\/\/ *(.*)"
    unit_pattern = "([A-Z0-9]+) +\*([A-Z0-9, ]+)\*(.*)"

    def __init__(self, address, payload):
        super().__init__(self.__class__.__name__, address, payload)
        m = re.match(self.pattern, payload)
        self.type = m.group(1)
        if " - " in self.type:
            self.type, self.type2 = self.type.split(" - ")
        self.description = m.group(2)
        m = re.match(self.channel_pattern, self.description)
        if m:
            self.channel = m.group(1)
            self.description = m.group(2)
        m = re.match(self.location_pattern, self.description)
        n = re.match(self.location_pattern2, self.description)
        if m:
            self.address = m.group(1)
            # self.location = m.group(2)
            self.description = m.group(3)
        elif n:
            self.address = n.group(1)
            # self.location = ""
            self.description = n.group(2)
        m = re.match(self.unit_pattern, self.description)
        if m:
            # self.station = m.group(1)
            self.units = m.group(2)
            self.description = m.group(3).strip()
        self.description = self.description.strip()


class NORCOMPage(Page):
    pattern = "  (.*)#(.*)FTAC(\d)(.*)#LAT:?(\d+) *#LON:?(\d+)(.*)"

    def __init__(self, address, payload):
        super().__init__(self.__class__.__name__, address, payload)
        m = re.match(self.pattern, payload)
        self.address = m.group(1).strip()
        self.type = m.group(2)[-30:].strip()
        if " - " in self.type:
            self.type, self.type2 = self.type.split(" - ")[0:2]
        self.description = m.group(2)[:-30].strip()
        self.channel = m.group(3)
        self.units = m.group(4).strip().split(" ")[0].split(",")
        self.lat = m.group(5)
        self.lon = m.group(6)


class NORCOMAddressChange(Page):
    pattern = "  ADDRESS CHANGE:?(.*)#(.*)#(.*)"

    def __init__(self, address, payload):
        super().__init__(self.__class__.__name__, address, payload)
        m = re.match(self.pattern, payload)
        self.address = m.group(1).strip()
        # lat/long on address changes are blank
        # self.lat = m.group(2).strip()
        # self.lon = m.group(3).strip()
        #
        self.description = None
