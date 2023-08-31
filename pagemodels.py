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
        self.time = datetime.datetime.now().astimezone().isoformat()

    def __str__(self):
        return repr((self.__dict__))


class SnohomishPage(Page):
    page_type = 'SNOHOMISH'
    pattern = "  >>([A-Z0-9\- ]+)<<(.+)"
    channel_pattern = " * FIRE ?TAC ?(\d\d)(.*)"
    location_pattern = " *([^\/]*) *\/ +([^\/]*) +\/ +(.*)"
    location_pattern2 = " *([^\/]*) *\/\/ *(.*)"
    unit_pattern = "([A-Z0-9]+) +\*([A-Z0-9, ]+)\*(.*)"
    alarm_pattern = "-? ?Alarm Level: ?(\d+) (.*)"

    def __init__(self, address, payload):
        super().__init__(self.page_type, address, payload)
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
        #filter out alarm levels
        m = re.match(self.alarm_pattern, self.address)
        if m:
            self.address = m.group(2)
        m = re.match(self.unit_pattern, self.description)
        if m:
            # self.station = m.group(1)
            self.units = [i.strip() for i in m.group(2).strip().split(",")]
            self.description = m.group(3).strip()
        self.description = self.description.strip()


class NORCOMPage(Page):
    page_type = 'NORCOM'
    #pattern = "  (.*)#(.*)FTAC(\d)(.*)#LAT:?(\d+) *#LON:?(\d+)(.*)"
    pattern = "  ([\w -]+); \*(FTAC - \d)?\*;  ([\w\d \/]+)?; ([\d\w, @]+); ([\d\w ,]+); ([\d.]+);(-[\d.]+)"

    def __init__(self, address, payload):
        super().__init__(self.page_type, address, payload)
        m = re.match(self.pattern, payload)
        self.address = m.group(4).strip()
        self.type = m.group(1).strip()
        if " - " in self.type:
            self.type, self.type2 = self.type.split(" - ")[0:2]
        self.description = m.group(3)
        if self.description:
            self.description = self.description.strip()
        self.channel = m.group(2)
        if self.channel and " - " in self.channel:
            self.channel = self.channel.split(" - ")[1].strip()
        self.units = [i.strip() for i in m.group(5).strip().split(", ")]
        self.lat = m.group(6)
        self.lon = m.group(7)


class NORCOMAddressChange(Page):
    page_type = 'NORCOM_ADDRESS_CHANGE'
    pattern = "  ADDRESS CHANGE:?(.*)#(.*)#(.*)"

    def __init__(self, address, payload):
        super().__init__(self.page_type, address, payload)
        m = re.match(self.pattern, payload)
        self.address = m.group(1).strip()
        # lat/long on address changes are blank
        # self.lat = m.group(2).strip()
        # self.lon = m.group(3).strip()
        #
        self.description = None
