#!/bin/bash

# Setup container runtime https://kubernetes.io/docs/setup/production-environment/container-runtimes/
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# Sysctl params required by setup, params persist across reboots
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# Apply sysctl params without reboot
sysctl --system

# Add Docker's official GPG key:
apt-get update
apt-get install apt-transport-https ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \"$(. /etc/os-release && echo $VERSION_CODENAME)\" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update

# **IMPORTANT**: cri: dockerd is not supported from 1.24, No need to install `docker-ce` and `docker-ce-cli`
apt install -y containerd.io

# Add the repository for K8S
kubernetes_version="1.27"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list

# Install kubernetes dependencies
apt-get update
apt install -y kubelet kubeadm kubectl

# [OPTIONAL] Install etcdctl https://github.com/etcd-io/etcd/releases/
ETCD_VER=v3.5.12

# Choose either URL
GOOGLE_URL=https://storage.googleapis.com/etcd
GITHUB_URL=https://github.com/etcd-io/etcd/releases/download
DOWNLOAD_URL=${GITHUB_URL}

rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-${ETCD_VER} && mkdir -p /tmp/etcd-${ETCD_VER}

curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-${ETCD_VER} --strip-components=1
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

cp /tmp/etcd-${ETCD_VER}/etcd /usr/local/bin/
cp /tmp/etcd-${ETCD_VER}/etcdctl /usr/local/bin/
cp /tmp/etcd-${ETCD_VER}/etcdutl /usr/local/bin/
