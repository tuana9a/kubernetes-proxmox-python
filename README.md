# kubernetes-proxmox-cluster-autoscaler

# [TODO] Prepare the network for vm

# Prefare vm template

Login to your proxmox host as root user

```bash
#!/bin/bash

apt-get install -y cloud-init
apt-get install -y libguestfs-tools

IMAGE_FILE=bionic-server-cloudimg-amd64.img
wget https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img -O $PWD/$IMAGE_FILE
virt-customize -a $IMAGE_FILE --install qemu-guest-agent
virt-customize -a $IMAGE_FILE --run install-kube.sh
virt-customize -a $IMAGE_FILE --copy-in $PWD/containerd/config.toml:/etc/containerd/

NETWORK=vmbr56 # TODO: your network
TEMPLATE_VM_ID=9000
TEMPLATE_VM_CORE_COUNT=4
TEMPLATE_VM_MEM=8192
qm create $TEMPLATE_VM_ID --cores $TEMPLATE_VM_CORE_COUNT --memory $TEMPLATE_VM_MEM --net0 virtio,bridge=$NETWORK --scsihw virtio-scsi-pci

STORAGE=local # TODO: your storage name
qm set $TEMPLATE_VM_ID --scsi0 $STORAGE:0,import-from=$PWD/$IMAGE_FILE
qm set $TEMPLATE_VM_ID --ide2 $STORAGE:cloudinit
qm set $TEMPLATE_VM_ID --boot order=scsi0
qm set $TEMPLATE_VM_ID --serial0 socket --vga serial0
# qm resize $TEMPLATE_VM_ID scsi0 +20G # it's really working but don't know why it's returning 500 and the size in the UI stay the same
qm template $TEMPLATE_VM_ID
```

# Prepare the config.json

## Extract the --discovery-token-ca-cert-hash

https://www.reddit.com/r/kubernetes/comments/h7wfnc/how_do_i_derive_certificate_pem_data_from/

https://stackoverflow.com/questions/66860670/how-to-programatically-get-value-printed-by-kubernetes-in-discovery-token-ca-c

```bash
openssl x509 -in /etc/kubernetes/pki/ca.crt -noout -pubkey | openssl rsa -pubin -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1
```

```bash
cat ~/.kube/config | grep certificate-authority-data | awk '{ print $2 }' | base64 --decode | openssl x509 -noout -pubkey | openssl rsa -pubin -outform DER 2>/dev/null | sha256sum | awk '{print $1}'
```

# Add vm

```bash
./add_vm.py
```