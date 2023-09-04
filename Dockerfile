FROM sysrun/multimon-ng:latest as base
RUN apt update 
RUN apt install -y python3-pip tzdata 
#RUN apt update && apt install -y soapysdr-tools python3-soapysdr python3-numpy soapysdr-module-hackrf libsoapysdr-dev rtl-sdr git python3-pip tzdata

FROM base as builder
RUN apt install -y soapysdr-tools libsoapysdr-dev git
RUN git clone "https://github.com/rxseger/rx_tools" && \
    cd rx_tools && \
    cmake . && \
    make

FROM base as runner
COPY --from=builder /rx_tools/rx_* /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# #RUN apt update && apt install -y soapysdr-tools python3-soapysdr python3-numpy soapysdr-module-hackrf rtl-sdr git python3-pip tzdata
# RUN apt install -y python3-pip

WORKDIR /app
COPY . .
RUN pip3 install -r /app/requirements.txt

ENV TZ="America/Los_Angeles"
ENV COLOREDLOGS_LOG_FORMAT='%(asctime)s - %(message)s'
ENV RTL_DEVICE=/dev/null
ENV FREQ=152007500

CMD /app/listen.sh 
