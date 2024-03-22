#!/bin/bash

set -e

# SECTION: build os image
BASE_IMAGE_FILE=ubuntu.img
IMAGE_FILE=kube-lb.img

if [ ! -f $BASE_IMAGE_FILE ]; then
    wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O $BASE_IMAGE_FILE
fi

rm -f $IMAGE_FILE
cp $BASE_IMAGE_FILE $IMAGE_FILE

qemu-img resize $IMAGE_FILE +20G
virt-resize --format qcow2 --expand /dev/sda1 $BASE_IMAGE_FILE $IMAGE_FILE
virt-customize -a $IMAGE_FILE --install qemu-guest-agent
virt-customize -a $IMAGE_FILE --install haproxy
virt-customize -a $IMAGE_FILE --copy-in config_haproxy.py:/usr/local/bin/
# [OPTIONAL]
virt-customize -a $IMAGE_FILE --run userdata.sh
