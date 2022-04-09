.PHONY: all build run reload clean


DEVICE = /dev/bus/usb/002/002
CONTAINER = norcom_radio
all: build run

build:
	@echo "Building image..."
	docker build -t norcom_radio:latest .
run:
	@echo "Launching container with RTL device at ${DEVICE}"
	docker run -it --device=${DEVICE} --name ${CONTAINER} norcom_radio:latest
reload:
	@echo "Copying files into container"
	docker cp . ${CONTAINER}:/app

clean:
	@echo "Deleting container"
	docker rm norcom_radio

