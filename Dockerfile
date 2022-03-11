FROM sysrun/multimon-ng:latest

RUN apt update && apt install -y soapysdr-tools python3-soapysdr python3-numpy soapysdr-module-hackrf libsoapysdr-dev rtl-sdr git

RUN git clone "https://github.com/rxseger/rx_tools" && \
    cd rx_tools && \
    cmake . && \
    make 

COPY . /app
CMD rtl_fm -f 152007500 -s 22050 - |\
multimon-ng -t raw -a POCSAG1200 -f alpha - |\
xargs -n1 -d'\n' /app/process_line.py


