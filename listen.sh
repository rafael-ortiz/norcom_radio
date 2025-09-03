rtl_fm -f $FREQ -s 22050 -p $PPM - | \
    multimon-ng --timestamp -t raw -a POCSAG1200 -f alpha - |\
    tee -a /app/raw |\
    /app/norcom_pager.py -d
