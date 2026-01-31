#!/bin/sh
SN=${RTL_DEVICE:-"00000001"}
DEVICE_INDEX=$(rtl_test -d 99 2>&1 | grep -Po '^\s*\K\d+(?=\s*:.*\bSN:\s*'"$SN"'(?:\s|$))')

if [ -z "$DEVICE_INDEX" ]; then
    echo "Could not find RTL-SDR device with serial number $SN"
    exit 1
fi

rtl_fm -d $DEVICE_INDEX -f $FREQ -s 22050 -p $PPM - | \
    multimon-ng --timestamp -t raw -a POCSAG1200 -f alpha - |\
    tee -a /app/raw |\
    /app/norcom_pager.py -d
