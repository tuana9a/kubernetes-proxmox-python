#!/usr/bin/env python3

import os
import time
import urllib3
import ipaddress

from proxmoxer import ProxmoxAPI
from kubernetes import config, client as klient
from kubernetes.client.models import V1Secret
from datetime import datetime, timedelta, timezone

from app.logger import Logger
from app.config import profiles
from app import util

urllib3.disable_warnings()

config.load_kube_config()
config_path = os.getenv("CONFIG_PATH")

if not config_path:
    raise ValueError("env: CONFIG_PATH is missing")
if not os.path.exists(config_path):
    raise FileNotFoundError(config_path)

log = Logger.DEBUG
profiles.load_from_file(config_path=config_path)
cfg = profiles.get_selected()
xlient = ProxmoxAPI(
    cfg.proxmox_host,
    user=cfg.proxmox_user,
    password=cfg.proxmox_password,
    verify_ssl=False,  # TODO: verify later with ca cert
)

pve_network_response = xlient.nodes(cfg.proxmox_node).network(
    cfg.proxmox_vm_network).get()
pve_network_interface = ipaddress.IPv4Interface(pve_network_response["cidr"])
pve_network_gw = str(
    pve_network_interface.ip) or pve_network_response["address"]
pve_network = pve_network_interface.network
pve_vm_ip_pool = []
for ip in pve_network.hosts():
    pve_vm_ip_pool.append(str(ip))
pve_network_preserved_ips = cfg.proxmox_network_preserved_ips
pve_network_preserved_ips.append(pve_network_gw)
log.debug("pve_network_preserved_ips", pve_network_preserved_ips)

vm_list = xlient.nodes(cfg.proxmox_node).qemu.get()
log.debug("len(vm_list)", len(vm_list))
exist_vm_id = set()
exist_vm_ip = set()
exist_vm_ip.update(pve_network_preserved_ips)
for vm in vm_list:
    vmid = vm["vmid"]
    exist_vm_id.add(vmid)
    vm_config = xlient.nodes(cfg.proxmox_node).qemu(vmid).config.get()
    ifconfig0 = vm_config.get("ipconfig0", None)
    if not ifconfig0: continue
    vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
    if vm_ip: exist_vm_ip.add(vm_ip)

log.debug("exist_vm_id", exist_vm_id)
newid = util.find_missing_number(cfg.proxmox_vm_id_range[0],
                                 cfg.proxmox_vm_id_range[1], exist_vm_id)
if not newid:
    log.debug("Error: can't find new id")
    exit(1)
log.debug("newid", newid)

log.debug("exist_vm_ip", exist_vm_ip)
new_ip = util.find_missing(pve_vm_ip_pool, exist_vm_ip)
if not new_ip:
    log.debug("Error: can't find new ip")
    exit(1)
log.debug("new_ip", new_ip)

clone_respone = xlient.nodes(cfg.proxmox_node).qemu(
    cfg.proxmox_template_vm_id).clone.post(newid=newid)
log.debug("clone", clone_respone)

edit_vm_respone = xlient.nodes(cfg.proxmox_node).qemu(newid).config.put(
    name=f"{cfg.proxmox_vm_name_prefix}{newid}",
    ciuser="u",
    cipassword="1",
    agent="enabled=1,fstrim_cloned_disks=1",
    ipconfig0=f"ip={new_ip}/24,gw={pve_network_gw}")
log.debug("edit", edit_vm_respone)

resize_disk_response = xlient.nodes(cfg.proxmox_node).qemu(newid).resize.put(
    disk="scsi0", size="+20G")
log.debug("resize", resize_disk_response)

start_vm_response = xlient.nodes(
    cfg.proxmox_node).qemu(newid).status.start.post()
log.debug("start_vm", start_vm_response)

# TODO: find a better way: first boot command, or interval poll checking if node is ready
time.sleep(3 * 60)

token_id = util.KubeUtil.gen_token_id()
token_secret = util.KubeUtil.gen_token_secret()
token_string_data = {
    "token-id": token_id,
    "token-secret": token_secret,
    "usage-bootstrap-authentication": "true",
    "usage-bootstrap-signing": "true",
    "auth-extra-groups": "system:bootstrappers:kubeadm:default-node-token",
    "expiration": (datetime.now(timezone.utc) +
                   timedelta(minutes=5)).isoformat()  # 5 minute from now
}
v1_secret = V1Secret(
    type="bootstrap.kubernetes.io/token",
    metadata={"name": f"bootstrap-token-{token_id}"},
    string_data=token_string_data,
)
klient.CoreV1Api().create_namespaced_secret(
    "kube-system",
    v1_secret,
)

join_command = [
    "kubeadm",
    "join",
    cfg.kubernetes_api_server,
    "--token",
    f"{token_id}.{token_secret}",
    "--discovery-token-ca-cert-hash",
    f"sha256:{cfg.kubernetes_discovery_token_ca_cert_hash}",
]
exec_response = (xlient.nodes(
    cfg.proxmox_node).qemu(newid).agent.exec.post(command=join_command))
log.debug("exec_response", exec_response)
pid = exec_response.get("pid", None)
if not pid:
    log.debug("Unknown status")
    exit(1)
log.debug("pid", pid)

pid_exited = 0
pid_stdout = None
pid_exitcode = None
while not pid_exited:
    status = xlient.nodes(
        cfg.proxmox_node).qemu(newid).agent("exec-status").get(pid=pid)
    pid_exited = status["exited"]
    pid_stdout = status.get("out-data", None)
    pid_exitcode = status.get("exitcode", None)
    time.sleep(5)

log.debug("exitcode", pid_exitcode)
log.debug(pid_stdout)
