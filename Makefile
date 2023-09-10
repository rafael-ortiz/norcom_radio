.PHONY: all build run reload clean

# Set RTL_DEVICE on the Env 
# $ RTL_DEVICE=/dev/bus/usb/001/002 make run

IMAGE=norcom_radio
CONTAINER=norcom_radio
FREQ=152007500

all: build run

build:
	@echo "Building image..."
	docker build -t ${IMAGE}:latest .
run:
	@echo "Launching container with RTL device at ${RTL_DEVICE}"
	docker run -d --device=${RTL_DEVICE} -e "RTL_DEVICE=${RTL_DEVICE}" -e FREQ=${FREQ}  --name ${CONTAINER} ${IMAGE}:latest
debug:
	@echo "Launching container with RTL device at ${RTL_DEVICE}"
	docker run -it --device=${RTL_DEVICE} -e "RTL_DEVICE=${RTL_DEVICE}" -e FREQ=${FREQ}  --name ${CONTAINER} ${IMAGE}:latest
reload:
	@echo "Copying files into container"
	docker cp . ${CONTAINER}:/app

clean:
	@echo "Deleting container"
	docker kill ${CONTAINER} || docker rm ${CONTAINER}

