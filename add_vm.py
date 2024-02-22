#!/usr/bin/env python3

import os
import time
import urllib3
import ipaddress
import urllib.parse

from proxmoxer import ProxmoxAPI
from kubernetes import config, client as klient
from kubernetes.client.models import V1Secret
from datetime import datetime, timedelta, timezone

from app.logger import Logger
from app.config import profiles
from app import util

config.load_kube_config()
urllib3.disable_warnings()
log = Logger.DEBUG

config_path = os.getenv("CONFIG_PATH")
log.debug("config_path", config_path)

if not config_path:
    raise ValueError("env: CONFIG_PATH is missing")
if not os.path.exists(config_path):
    raise FileNotFoundError(config_path)

profiles.load_from_file(config_path=config_path)
cfg = profiles.get_selected()
xlient = ProxmoxAPI(
    cfg.proxmox_host,
    user=cfg.proxmox_user,
    password=cfg.proxmox_password,
    verify_ssl=False,  # TODO: verify later with ca cert
)

r = xlient.nodes(cfg.proxmox_node).network(cfg.proxmox_vm_network).get()
pve_network_interface = ipaddress.IPv4Interface(r["cidr"])
pve_network_gw = str(pve_network_interface.ip) or r["address"]
pve_network = pve_network_interface.network
vm_ip_pool = []
for ip in pve_network.hosts():
    vm_ip_pool.append(str(ip))
pve_network_preserved_ips = cfg.proxmox_network_preserved_ips
pve_network_preserved_ips.append(pve_network_gw)
log.debug("pve_network_preserved_ips", pve_network_preserved_ips)

r = xlient.nodes(cfg.proxmox_node).qemu.get()
vm_list = []
for vm in r:
    vm_id = vm["vmid"]
    if (vm_id >= cfg.proxmox_vm_id_begin and vm_id <= cfg.proxmox_vm_id_end):
        vm_list.append(vm)

log.debug("len(vm_list)", len(vm_list))
exist_vm_id = set()
exist_vm_ip = set()
exist_vm_ip.update(pve_network_preserved_ips)
for vm in vm_list:
    vm_id = vm["vmid"]
    exist_vm_id.add(vm_id)
    vm_config = xlient.nodes(cfg.proxmox_node).qemu(vm_id).config.get()
    ifconfig0 = vm_config.get("ipconfig0", None)
    if not ifconfig0: continue
    vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
    if vm_ip: exist_vm_ip.add(vm_ip)

log.debug("exist_vm_id", exist_vm_id)
new_id = util.find_missing_number(cfg.proxmox_vm_id_begin,
                                  cfg.proxmox_vm_id_end, exist_vm_id)
if not new_id:
    log.debug("Error: can't find new id")
    exit(1)
log.debug("newid", new_id)

log.debug("exist_vm_ip", exist_vm_ip)
new_ip = util.find_missing(vm_ip_pool, exist_vm_ip)
if not new_ip:
    log.debug("Error: can't find new ip")
    exit(1)
log.debug("new_ip", new_ip)

r = xlient.nodes(cfg.proxmox_node).qemu(
    cfg.proxmox_template_vm_id).clone.post(newid=new_id)
log.debug("clone", r)

r = xlient.nodes(cfg.proxmox_node).qemu(new_id).config.put(
    name=f"{cfg.proxmox_vm_name_prefix}{new_id}",
    ciuser=cfg.proxmox_vm_username,
    cipassword=cfg.proxmox_vm_password,
    sshkeys=urllib.parse.quote(cfg.proxmox_vm_ssh_keys, safe=""), # NOTE: https://github.com/proxmoxer/proxmoxer/issues/153
    agent="enabled=1,fstrim_cloned_disks=1",
    net0=f"virtio,bridge={cfg.proxmox_vm_network}",
    ipconfig0=f"ip={new_ip}/24,gw={pve_network_gw}",
)
log.debug("edit", r)

r = xlient.nodes(cfg.proxmox_node).qemu(new_id).resize.put(disk="scsi0",
                                                           size="+20G")
log.debug("resize_disk", r)

r = xlient.nodes(cfg.proxmox_node).qemu(new_id).status.start.post()
log.debug("start_vm", r)

status = None
timeout = 5 * 60
duration = 0
interval_check = 10

while True:
    if duration > timeout:
        log.debug("timeout reached")
        exit(1)
    try:
        r = xlient.nodes(cfg.proxmox_node).qemu(new_id).agent.ping.post()
        log.debug("guest-agent is ready")
        break
    except Exception as err:
        log.debug("guest-agent", err)
    time.sleep(interval_check)
    duration += interval_check

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
log.debug(" ".join(join_command))
r = (xlient.nodes(
    cfg.proxmox_node).qemu(new_id).agent.exec.post(command=join_command))
log.debug("exec_response", r)
pid = r.get("pid", None)
if not pid:
    log.debug("Unknown status")
    exit(1)
log.debug("pid", pid)

pid_exited = 0
pid_stdout = None
pid_stderr = None
pid_exitcode = None
interval_check = 10
while not pid_exited:
    time.sleep(interval_check)
    status = xlient.nodes(
        cfg.proxmox_node).qemu(new_id).agent("exec-status").get(pid=pid)
    pid_exited = status["exited"]
    pid_stdout = status.get("out-data", None)
    pid_stderr = status.get("err-data", None)
    pid_exitcode = status.get("exitcode", None)

log.debug("exitcode", pid_exitcode)
log.debug("pid_stdout", pid_stdout)
log.debug("pid_stderr", pid_stderr)
