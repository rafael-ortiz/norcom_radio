#!/usr/bin/env python3
import sys
import logging

from PageParser import PageParser
from PageParser import PagePSAP

logger = logging.getLogger(__name__)

def main():
    loglevel = logging.DEBUG
    logformat = '[%(asctime)s] %(levelname)s %(module)s.%(funcName)s %(message)s'
    logging.basicConfig(format=logformat, datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)
    logger.info("Initialized logging")
    parser = PageParser()

    while True:
        try:
            for line in sys.stdin:
                line = line.strip()

                logger.info("Received %s", " ".join(line.split()[:5]))

                page = parser.parse(line)

                if page is None:
                    continue

                if page.parsed:
                    logger.info("Parsed %s page to %s: %s; %s; %s",
                                page.psap,
                                page.capcode,
                                page.get_calltype(),
                                page.channel,
                                page.address_raw
                            )
                    # print(page.to_json())
                elif page.keepalive:
                    logger.info("Parsed %s page to %s: %s",
                                page.psap,
                                page.capcode,
                                page.get_calltype()
                            )
                elif page.psap == PagePSAP.NORCOM:
                    # Make sure it's not a SNO011 page sent to NORCOM capcodes (mutual-aid)
                    if page.alpha.startswith('>>'):
                        logger.info("Ignoring SNO911 page sent to NORCOM address")
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
                else:
                    page = None
        except KeyboardInterrupt:
            print("")
            sys.exit(0)

main()