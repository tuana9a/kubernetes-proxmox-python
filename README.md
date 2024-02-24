# kubernetes-proxmox-cluster-autoscaler

# [TODO] Prepare the network for vm

ssh into the proxmox host

`vim /etc/network/interfaces`

Add these line to add a new NAT network with cidr 192.168.56.1/24

```txt
auto vmbr56
iface vmbr56 inet static
        address 192.168.56.1/24
        bridge-ports none
        bridge-stp off
        bridge-fd 0
        post-up   iptables -t nat -A POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
        post-down iptables -t nat -D POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
```

# Prefare vm template

Login to your proxmox host as root user, run these scripts, for files that using in the scripts see [examples/](./examples/), for example:
- [install-kube.sh](./examples/install-kube.sh)
- [containerd/config.toml](./examples/containerd/config.toml)

Install necessary tools to build vm image

```bash
apt-get install -y cloud-init
apt-get install -y libguestfs-tools
```

Build the vm image

```bash
IMAGE_FILE=bionic-server-cloudimg-amd64.img
wget https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img -O $PWD/$IMAGE_FILE
virt-customize -a $IMAGE_FILE --install qemu-guest-agent
virt-customize -a $IMAGE_FILE --run install-kube.sh
virt-customize -a $IMAGE_FILE --copy-in $PWD/containerd/config.toml:/etc/containerd/
```

OPTIONAL: for my personal use with https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner

```bash
virt-customize -a $IMAGE_FILE --install nfs-common
```

```bash
virt-customize -a $IMAGE_FILE --install haproxy
```

Create the vm template

```bash
IMAGE_FILE=bionic-server-cloudimg-amd64.img
TEMPLATE_VM_ID=9000
TEMPLATE_VM_CORE_COUNT=4
TEMPLATE_VM_MEM=8192
qm create $TEMPLATE_VM_ID --cores $TEMPLATE_VM_CORE_COUNT --memory $TEMPLATE_VM_MEM --scsihw virtio-scsi-pci

STORAGE=local # TODO: your storage name
qm set $TEMPLATE_VM_ID --scsi0 $STORAGE:0,import-from=$PWD/$IMAGE_FILE
qm set $TEMPLATE_VM_ID --ide2 $STORAGE:cloudinit
qm set $TEMPLATE_VM_ID --boot order=scsi0
qm set $TEMPLATE_VM_ID --serial0 socket --vga serial0
qm set $TEMPLATE_VM_ID --name kube-1.27
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

See `./examples/config.json`

# Add vm

```bash
./add_vm.py
```