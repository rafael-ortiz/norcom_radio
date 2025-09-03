#!/bin/sh
rtl_fm -f $FREQ -s 22050 -p $PPM - | \
    multimon-ng -t raw -a POCSAG1200 -f alpha - |\
    tee -a /app/raw |\
    /app/norcom_pager.py
