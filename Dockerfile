FROM sysrun/multimon-ng:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt update && apt install -y soapysdr-tools python3-soapysdr python3-numpy soapysdr-module-hackrf libsoapysdr-dev rtl-sdr git python3-pip tzdata
RUN pip3 install coloredlogs verboselogs

RUN git clone "https://github.com/rxseger/rx_tools" && \
    cd rx_tools && \
    cmake . && \
    make 

COPY . /app
ENV TZ="America/Los_Angeles"
ENV COLOREDLOGS_LOG_FORMAT='%(asctime)s - %(message)s'
CMD /app/listen.sh 
