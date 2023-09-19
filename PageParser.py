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
    
class PageParser:
    pattern = r"POCSAG1200:\s+Address:\s+(\d+)\s+Function:\s+\d\s+Alpha:\s+(.*)$"
    pattern_re = None

    last_keepalive = 0

    capcode_ignorelist = []

    def __init__(self, pattern=None):
        if pattern is not None:
            self.pattern = pattern

        try:
            self.pattern_re = re.compile(self.pattern)
        except re.error as err:
            logging.error("Failed to load pattern: %s", err)
            raise ValueError("expected valid regex pattern, got %s", pattern)

    def parse(self, line):
        matches = self.pattern_re.match(line)
        if matches is None:
            logger.warning("Ignoring page: unknown page format")
            logger.debug("Unknown format: %s", line)
            return None

        try:
            raw_page = matches.group(0)
            capcode = matches.group(1)
            alpha = matches.group(2)
        except IndexError as err:
            # invalid or malformed page
            logger.info("Ignoring page: malformed or invalid format")
            logger.debug("%s: %s", err, line)
            return None
        
        if capcode in PageParser.capcode_ignorelist:
            logging.info("Ignoring page: CAPCODE is on ignore list")
            logger.debug("Ignored CAPCODE %s %s", capcode, alpha)
            return None
        
        # return {'raw': raw_page, 'capcode': capcode, 'alpha': alpha}
        return self.create_page(raw_page, capcode, alpha)

    def create_page(self, raw_page, capcode, page_alpha):
        
        agency = PageAgency.from_capcode(capcode)

        if agency == PageAgency.NORCOM:
            return PageNorcom(raw=raw_page, capcode=capcode, alpha=page_alpha)
        elif agency == PageAgency.VALCOM:
            # Use the NORCOM processor until we see enough of them to decide otherwise
            return PageNorcom(raw=raw_page, capcode=capcode, alpha=page_alpha)
        elif agency == PageAgency.SNO911:
            return PageSnohomish(raw=raw_page, capcode=capcode, alpha=page_alpha)
        else:
            # Unknown capcode
            logging.warn("Ignoring page: unknown CAPCODE")

        return None

class Page:
    # TODO: Make the internal structure more closely match the json model

    timestamp = 0
    parsed = False
    keepalive = False
    skipped = False
    skip_reason = "unknown"

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

    def __init__(self, raw, capcode, alpha):
        self.timestamp = time.time()
        self.raw = raw
        self.capcode = capcode
        self.alpha = alpha

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
        # I would not consider this a stable interface quite yet
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
            'incident': {
                'type': self.call_type,
                'subtype': self.call_subtype,
            },
            'alarm_level': self.alarm_level,
            'reference': self.call_id,
            'cad_notes': self.call_notes
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

        if "PAGEGATE KEEP ALIVE NORMAL" in parse_alpha:
            self.call_type = "PAGEGATE KEEPALIVE"
            self.keepalive = True
            return True

        try:
            type_match = re.match(r">>([A-Za-z0-9 -]+)<<", parse_alpha)

            if type_match is None:
                # This is probably not a valid event
                self.skipped = True
                self.skip_reason = "malformed"
                logger.warning("PARSE FAILED: missing call type %s", self.alpha)
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
            else:
                self.skipped = True
                self.skip_reason = "malformed"
                logger.warning("PARSE FAILED: couldn't parse address fields %s", self.alpha)
                return False

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
            logger.warning("PARSE FAILED: %s %s".format(err, self.alpha))
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

        if "PAGEGATE KEEP ALIVE NORMAL" in self.alpha:
            self.call_type = "PAGEGATE KEEPALIVE"
            self.keepalive = True
            return True

        try:
            parse_alpha = self.alpha.replace("<EOT>","").replace("<NUL>","").replace(";;", ";").split(';')
 
            if len(parse_alpha) > 7:
                self.skip_reason = "malformed"
                self.skipped = True
                logger.error("PARSE FAILED: unexpected field %s", self.alpha)
                return False
            
            (call, channel, addr_name, addr_street, units, geo_lat, geo_long) = [ None ] * 7

            try:
                call = parse_alpha[0].strip()
                channel = parse_alpha[1].strip()
                addr_name = parse_alpha[2].strip()
                addr_street = parse_alpha[3].strip()
                units = parse_alpha[4].strip()
                geo_lat = parse_alpha[5].strip()
                geo_long = parse_alpha[6].strip()
            except IndexError:
                pass


            if addr_street is None:
                # Don't even bother parsing the rest
                self.skip_reason = "malformed"
                self.skipped = True
                logger.error("PARSE FAILED: Missing expected fields %s", self.alpha)
                return False


            call = re.sub(r'[<>]', '', call)
            if "-" in call:
                (self.call_type, self.call_subtype) = [ k.strip() for k in call.split('-', 1) ]
            else:
                self.call_type = call

            self.channel = re.sub(r'[\* -]','',channel)
            self.address_name = addr_name
            self.address_raw = addr_street

            self.units = []
            if units is not None:
                for unit in units.split(','):
                    if len(unit.strip()) < 3:
                        continue
                    self.units.append(unit.strip())

            self.geo = {'lat': geo_lat, 'long': geo_long }
        except (ValueError, IndexError) as err:
            # Couldn't unpack values correctly
            logger.error("PARSE FAILED: {} {}".format(err, self.alpha))
            self.skipped = True
            self.skip_reason = "malformed"
            return False
        
        self.parsed = True
        return True