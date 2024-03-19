#!/bin/bash

if [ -z $TEMPLATE_VM_ID ]; then
    echo TEMPLATE_VM_ID is not set, exitting...
    exit 1
fi

# SECTION: build os image
BASE_IMAGE_FILE=ubuntu.img
IMAGE_FILE=kube-lb.img
if [ ! -f $BASE_IMAGE_FILE ]; then
    wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O $BASE_IMAGE_FILE
fi
rm -f $IMAGE_FILE
cp $BASE_IMAGE_FILE $IMAGE_FILE
virt-customize -a $IMAGE_FILE --install qemu-guest-agent
virt-customize -a $IMAGE_FILE --install haproxy
virt-customize -a $IMAGE_FILE --copy-in config_haproxy.py:/usr/local/bin/
virt-customize -a $IMAGE_FILE --run userdata.sh # Optional

# SECTION: create template vm
IMAGE_FILE=kube-lb.img
TEMPLATE_VM_CORE_COUNT=2
TEMPLATE_VM_MEM=2048
STORAGE=local # TODO: your storage name

qm create $TEMPLATE_VM_ID --cores $TEMPLATE_VM_CORE_COUNT --memory $TEMPLATE_VM_MEM --scsihw virtio-scsi-pci
qm set $TEMPLATE_VM_ID --scsi0 $STORAGE:0,import-from=$PWD/$IMAGE_FILE
qm set $TEMPLATE_VM_ID --ide2 $STORAGE:cloudinit
qm set $TEMPLATE_VM_ID --boot order=scsi0
qm set $TEMPLATE_VM_ID --serial0 socket --vga serial0
qm set $TEMPLATE_VM_ID --name kube-lb
qm template $TEMPLATE_VM_ID
