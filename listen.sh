rtl_fm -f 152007500 -s 22050 - | \
    multimon-ng -t raw -a POCSAG1200 -f alpha - |\
    tee /app/raw |\
    /app/listen.py
