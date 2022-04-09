#!/usr/bin/env python3
import re
import coloredlogs, logging, verboselogs
from verboselogs import VerboseLogger as getLogger
import pagemodels
import inspect 

coloredlogs.install(fmt="%(asctime)s - %(levelname)s - %(message)s")
logger = getLogger(__name__)
logger.disabled = True  # change this if you want colored logs


def process_line(line):

    # Extract valid payload
    m = re.match(
        "POCSAG1200: Address: +(\d+)  Function: \d  Alpha: ([A-Za-z0-9#: <>\/*\"\-\(\)'.,?]+).*",
        line,
    )
    if not m:
        if "Alpha" not in line:
            logger.spam(line)
            return
        logger.error(line)
        return

    address = m.group(1)
    payload = m.group(2).split("<EOT>")[0]
    # Return if corrupted payload
    if len(payload) < 16 or any(
        x in payload
        for x in ["<SOH>", "<DEL>", "<SI>", "<CAN>", "<EM>", "<DC2>", "<DC4>", "<NAK>"]
    ):
        logger.spam(line)
        return
    # Keep alive messages are spam
    if "  SNO911: PAGEGATE KEEP ALIVE NORMAL" == payload:
        logger.spam(payload)
        return

    for cls in get_subclasses(pagemodels, pagemodels.Page):
        match = re.match(cls.pattern, payload)
        if match:
            page = cls(address, payload)
            logger.info(page)
            return page
    return
    # Idenify Snohomish pages
    sno_match = re.match(SnohomishPage.pattern, payload)
    if sno_match:
        page = SnohomishPage(address, payload)
        logger.info(page)
        return page

    # Identify NORCOM pages

    norcom_match = re.match(NORCOMPage.pattern, payload)
    if norcom_match:
        page = NORCOMPage(address, payload)
        logger.info(page)
        return page

    # Identify Address Change:
    address_change_pattern = "  ADDRESS CHANGE:?(.*)#(.*)#(.*)"
    address_change_match = re.match(address_change_pattern, payload)
    if address_change_match:
        logger.info(payload)
        return
    # Warn about unclassified messages
    logger.warning("Address:" + address + ", Payload:" + payload)
    return


def get_subclasses(mod, cls):
    """Yield the classes in module ``mod`` that inherit from ``cls``"""
    for name, obj in inspect.getmembers(mod):
        if hasattr(obj, "__bases__") and cls in obj.__bases__:
            yield obj


if __name__ == "__main__":
    import sys

    process_line(sys.argv[1])
