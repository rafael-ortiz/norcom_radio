import sys
import logging, coloredlogs, verboselogs
from PageParser import PageParser

coloredlogs.install(level=11,fmt='%(asctime)s - %(levelname)s - %(message)s')
filename = sys.argv[1]

parser = PageParser()
with open(filename, "r") as rawfile:
    for line in rawfile.readlines():
        page = parser.parse(line)

        if page is None:
            logging.error("FAIL: {}".format(line))
            continue

        if page.parsed:
            logging.info("OK: {}".format(page.to_json()))
        elif page.skipped:
            logging.warning("SKIP: {} {}".format(page.skip_reason, page.alpha))
        else:
            logging.error("FAIL: {}".format(page.raw))

