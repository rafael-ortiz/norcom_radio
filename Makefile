.PHONY: all build run

DEVICE = /dev/bus/usb/002/002

all: build run

build:
	@echo "Building image..."
	docker build -t norcom_radio:latest

run:
	@echo "Launching container with RTL device at ${DEVICE}"
	docker run -it --device=${DEVICE} norcom_radio:v1
