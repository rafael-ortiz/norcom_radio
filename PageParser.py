import json
import re
import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class PageAgency(Enum):
    NONE = 0
    NORCOM = 1
    SNO911 = 2
    VALCOM = 3

    @classmethod
    def from_capcode(cls, capcode):
        if capcode[:3] in ["147", "117"]:
            return cls(1)
        elif capcode[:3] in ["131"]:
            return cls(2)
        else:
            return cls(0)
        
    def __str__(self):
        return self.name

class Page:
    timestamp = 0
    parsed = False

    agency = PageAgency.NONE
    
    raw = None
    capcode = None
    alpha = None

    call_type = None
    call_subtype = None
    call_notes = None
    call_id = None

    alarm_level = None

    channel = None

    address_name = None
    address_raw = None
    address_parsed = {}

    units = []
    geo = {}

    skipped = False
    skip_reason = "unknown"

    capcode_ignorelist = []

    def __init__(self, raw, capcode, alpha):
        self.timestamp = time.time()
        self.raw = raw
        self.capcode = capcode
        self.alpha = alpha

        if self.capcode in Page.capcode_ignorelist:
            logging.info("Ignoring page: CAPCODE is on ignore list")
            self.skipped = True
            self.skip_reason = "ignore list"
            return False

        self.parse_page()

    def parse_page(self):
        raise NotImplementedError("Parser not implemented")
    
    def get_calltype(self):
        """ Re-join the call type components if they're not empty """
        if self.call_subtype:
            return "{} - {}".format(self.call_type, self.call_subtype)
        else:
            return self.call_type

    def to_json(self):
        page_data = {
            'timestamp': self.timestamp,
            'capcode': self.capcode,
            'agency': str(self.agency),
            'channel': self.channel,
            'units': self.units,
            'location': {
                'name': self.address_name,
                'address': self.address_raw,
                'geo': self.geo,
            },
            'alarm_level': self.alarm_level,
            'call_type': self.call_type,
            'call_subtype': self.call_subtype,
            'call_id': self.call_id,
            'call_notes': self.call_notes,
        }
        return json.dumps(page_data)

class PageSnohomish(Page):
    def __init__(self, raw, capcode, alpha, agency=PageAgency.SNO911):
        super().__init__(raw, capcode, alpha)
        self.agency = agency
        
    def parse_page(self):
        if self.alpha is None:
            return None
        
        logger.debug("Attempting to parse as SNO911")

        parse_alpha = self.alpha.replace("<EOT>","").replace("<NUL>","")

        if "PAGEGATE KEEP ALIVE" in parse_alpha:
            # TODO: Do something useful with the keepalives
            self.skipped = True
            self.skip_reason = "keepalive"
            logger.info("Ignoring page: PAGEGATE Keepalive")
            return False

        try:
            type_match = re.match(r">>([A-Za-z0-9 -]+)<<", parse_alpha)

            if type_match is None:
                # This is probably not a valid event
                self.skipped = True
                self.skip_reason = "malformed"
                logger.warn("PARSE FAILED: missing call type %s", self.alpha)
                return False

            call_types = type_match.group(1)

            (self.call_type, self.call_subtype) = [ k.strip() for k in call_types.split('-', 1) ]

            # Remove the call type from the text and keep parsing
            parse_alpha = parse_alpha.replace(type_match.group(0), '').strip()

            parse_groups = parse_alpha.split('/')
            channel_address = parse_groups[0].strip()
            self.address_name = parse_groups[1].strip()
            call_details = parse_groups[2].strip()

            channel_match = re.match(r"(FIRE\s+TAC\s+\d+)", parse_alpha)
            if channel_match is not None:
                self.channel = channel_match.group(1)
                parse_alpha = parse_alpha.replace(self.channel, '').strip()
            
            alarm_match = re.match(r"-\s+Alarm Level:\s+(\d+)", parse_alpha)
            if alarm_match is not None:
                self.alarm_level = alarm_match.group(1)
                parse_alpha = parse_alpha.replace(alarm_match.group(0), '').strip()
            
            address_match = re.match(r"(.*)\/(.*?)\/\s+([A-Z0-9]+)?\s+\*", parse_alpha)
            if address_match is not None:
                self.address_raw = address_match.group(1)
                self.address_name = address_match.group(2)
                if (len(address_match.groups()) == 3):
                    self.call_id = address_match.group(3)

            call_details = parse_alpha.replace(address_match.group(0)[:-1], '')

            unit_match = re.match(r"\*([A-Za-z0-9\s,]+)\*?", call_details)
            # Some pages are too long to include all of the units
            if (unit_match.group(0)[-1:] != "*"):
                # Reached the end of text without the other delimiter
                units = [ k.strip() for k in unit_match.group(1).split(',') ]
                call_details = ""

                # pop the last element if it doesn't conform to the expected unit format
                unit_id_match = re.match(r"[A-Z]+[0-9]+", units[-1:].pop())
                if unit_id_match is None:
                    units.pop()

                self.units = units

            else:
                self.units = [ k.strip() for k in unit_match.group(1).split(',') ]
                self.call_notes = call_details.replace(unit_match.group(0), '').strip()
        except (IndexError, ValueError) as err:
            logger.warn("PARSE FAILED: {} {}".format(err, self.alpha))
            self.skip_reason = "malformed"
            self.skipped = True
            return False

        self.parsed = True
        return True


class PageNorcom(Page):
    def __init__(self, raw, capcode, alpha, agency=PageAgency.NORCOM):
        super().__init__(raw, capcode, alpha)
        self.agency = agency

    def parse_page(self):
        if self.alpha is None:
            return None
        
        logger.debug("Attempting to parse as NORCOM")

        try:
            parse_alpha = self.alpha.replace("<EOT>","").replace("<NUL>","").replace(";;", ";").split(';')

            if len(parse_alpha) < 7:
                # Missing some values
                self.skip_reason = "malformed"
                self.skipped = True
                logger.warn("PARSE FAILED: Missing expected field {}", self.alpha)
                return False
            elif len(parse_alpha) > 7:
                self.skip_reason = "malformed"
                self.skipped = True
                logger.warn("PARSE FAILED: unexpected field {}", self.alpha)
                return False

            (call, channel, addr_name, addr_street, units, geo_lat, geo_long) = [ k.strip() for k in parse_alpha ]

            if "-" in call:
                (self.call_type, self.call_subtype) = [ k.strip() for k in call.split('-', 1) ]
            else:
                self.call_type = call

            self.channel = re.sub(r'[\* -]','',channel)
            self.address_name = addr_name
            self.address_raw = addr_street

            self.units = [ k.strip() for k in units.split(',') ]

            self.geo = {'lat': geo_lat, 'long': geo_long }
        except (ValueError, IndexError) as err:
            # Couldn't unpack values correctly
            logger.warn("PARSE FAILED: {} {}".format(err, self.alpha))
            self.skipped = True
            self.skip_reason = "malformed"
            return False
        
        self.parsed = True
        return True