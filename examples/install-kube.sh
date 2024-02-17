#!/bin/bash

# Disable swap
swapoff -a -v

# To avoid [ERROR FileContent--proc-sys-net-bridge-bridge-nf-call-iptables]: /proc/sys/net/bridge/bridge-nf-call-iptables does not exist
# Solution https://stackoverflow.com/questions/44125020/cant-install-kubernetes-on-vagrant
echo br_netfilter > /etc/modules-load.d/br_netfilter.conf
systemctl restart systemd-modules-load.service

echo 1 > /proc/sys/net/bridge/bridge-nf-call-iptables
echo 1 > /proc/sys/net/bridge/bridge-nf-call-ip6tables

echo net.ipv4.ip_forward=1 >> /etc/sysctl.conf
echo net.bridge.bridge-nf-call-iptables=1 >> /etc/sysctl.conf
sysctl -p

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
K8S_MINOR_VERSION=1.27 # TODO: need to change in a "template" way
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v$K8S_MINOR_VERSION/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v$K8S_MINOR_VERSION/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list

# Install K8S dependencies
apt-get update
apt install -y kubelet kubeadm kubectl
