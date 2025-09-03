FROM ubuntu:noble AS base
RUN apt-get update
RUN apt-get install -y python3-pip libusb-1.0-0 tzdata


FROM base AS builder
RUN apt-get install -y build-essential libusb-1.0-0-dev git cmake pkg-config debhelper libsoapysdr-dev libssl-dev
WORKDIR /rtl-sdr
RUN git clone --depth 1 --branch v1.3.6 "https://github.com/rtlsdrblog/rtl-sdr-blog" && \
    cd rtl-sdr-blog && \
    dpkg-buildpackage -b --no-sign && \
    mkdir build && cd build && \
    cmake ../ && make && \
    cd ../.. && \
    dpkg -i librtlsdr0_*.deb && \
    dpkg -i librtlsdr-dev_*.deb


WORKDIR /multimon
RUN git clone --depth 1 --branch 1.4.1 "https://github.com/EliasOenal/multimon-ng.git" && \
    cd multimon-ng && \
    mkdir build && cd build && \
    cmake .. && \
    make

FROM base AS runner
COPY --from=builder /rtl-sdr/rtl-sdr-blog/build/src/rtl_* /usr/local/bin/
COPY --from=builder /multimon/multimon-ng/build/multimon-ng /usr/local/bin/
COPY --from=builder /rtl-sdr/librtlsdr0_*.deb /tmp/
RUN dpkg -i /tmp/librtlsdr0_*.deb && \
    rm -rf /tmp/librtlsdr0_*.deb

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


WORKDIR /app
COPY . .
RUN pip install -r /app/requirements.txt --break-system-packages

ENV TZ="America/Los_Angeles"
ENV COLOREDLOGS_LOG_FORMAT='%(asctime)s - %(message)s'
ENV RTL_DEVICE=/dev/null
ENV FREQ=152007500
ENV PPM=0

CMD ["/app/listen.sh"]
