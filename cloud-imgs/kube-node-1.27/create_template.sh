#!/bin/bash

set -e

if [ -z $VM_ID ]; then
    hour=$(date +%H)
    minute=$(date +%M)
    VM_ID="127${hour}${minute}"
fi

echo VM_ID: $VM_ID

# SECTION: create vm template
IMAGE_FILE=kube-node.img
KUBE_VERSION=1.27
VM_CORE_COUNT=4
VM_MEM=8192
STORAGE=local # TODO: your storage name

qm create $VM_ID --cores $VM_CORE_COUNT --memory $VM_MEM --scsihw virtio-scsi-pci
qm set $VM_ID --scsi0 $STORAGE:0,import-from=$PWD/$IMAGE_FILE
qm set $VM_ID --ide2 $STORAGE:cloudinit
qm set $VM_ID --boot order=scsi0
qm set $VM_ID --serial0 socket --vga serial0
qm set $VM_ID --name kube-node-$KUBE_VERSION
qm template $VM_ID