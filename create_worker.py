#!/usr/bin/env python3

import os
import urllib3
import ipaddress

from proxmoxer import ProxmoxAPI

from app import util
from app.logger import Logger
from app.config import load_config
from app.controller import NodeController

urllib3.disable_warnings()
log = Logger.DEBUG

config_path = os.getenv("CONFIG_PATH")

if not config_path:
    raise ValueError("env: CONFIG_PATH is missing")
if not os.path.exists(config_path):
    raise FileNotFoundError(config_path)

log.debug("config_path", config_path)
cfg = load_config(config_path)
proxmox_host = cfg["proxmox_host"]
proxmox_user = cfg["proxmox_user"]
proxmox_password = cfg["proxmox_password"]
proxmox_node = cfg["proxmox_node"]
vm_network_name = cfg["vm_network_name"]
preserved_ips = cfg.get("preserved_ips", [])
vm_id_range = cfg.get("vm_id_range", [0, 9999])
worker_template_id = cfg["worker_template_id"]
vm_name_prefix = cfg.get("vm_name_prefix", "i-")
vm_username = cfg.get("vm_username", "u")
vm_password = cfg.get("vm_password", "1")
vm_ssh_keys = cfg.get("vm_ssh_keys", None)
control_plane_vm_ids = cfg["control_plane_vm_ids"]

nodectl = NodeController(
    ProxmoxAPI(
        proxmox_host,
        user=proxmox_user,
        password=proxmox_password,
        verify_ssl=False,  # TODO: verify later with ca cert
    ),
    proxmox_node,
    log=log)
r = nodectl.describe_network(vm_network_name)
network_interface = ipaddress.IPv4Interface(r["cidr"])
vm_network_gw = str(network_interface.ip) or r["address"]
vm_network = network_interface.network
vm_ip_pool = []
for ip in vm_network.hosts():
    vm_ip_pool.append(str(ip))
preserved_ips = preserved_ips
preserved_ips.append(vm_network_gw)
log.debug("preserved_ips", preserved_ips)

vm_list = nodectl.list_vm(vm_id_range[0], vm_id_range[1])

log.debug("len(vm_list)", len(vm_list))
exist_vm_id = set()
exist_vm_ip = set()
exist_vm_ip.update(preserved_ips)
for vm in vm_list:
    vm_id = vm["vmid"]
    exist_vm_id.add(vm_id)
    vm_config = nodectl.vm(vm_id).current_config()
    ifconfig0 = vm_config.get("ipconfig0", None)
    if not ifconfig0: continue
    vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
    if vm_ip: exist_vm_ip.add(vm_ip)
log.debug("exist_vm_id", exist_vm_id)
log.debug("exist_vm_ip", exist_vm_ip)

vm_id_new = util.find_missing_number(vm_id_range[0], vm_id_range[1],
                                     exist_vm_id)
if not vm_id_new:
    log.debug("Error: can't find new id")
    exit(1)
log.debug("newid", vm_id_new)

log.debug("exist_vm_ip", exist_vm_ip)
vm_ip_new = util.find_missing(vm_ip_pool, exist_vm_ip)
if not vm_ip_new:
    log.debug("Error: can't find new ip")
    exit(1)
log.debug("new_ip", vm_ip_new)

nodectl.clone(worker_template_id, vm_id_new)

vmctl = nodectl.vm(vm_id_new)

vmctl.update_config(
    name=f"{vm_name_prefix}{vm_id_new}",
    ciuser=vm_username,
    cipassword=vm_password,
    sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
    agent="enabled=1,fstrim_cloned_disks=1",
    net0=f"virtio,bridge={vm_network_name}",
    ipconfig0=f"ip={vm_ip_new}/24,gw={vm_network_gw}",
)

vmctl.resize_disk(disk="scsi0", size="+20G")
vmctl.startup()
vmctl.wait_for_guest_agent(timeout=5 * 60)

join_cmd = None
create_token_cmd = ["kubeadm", "token", "create", "--print-join-command"]
for vm_id in control_plane_vm_ids:
    exitcode, stdout, _ = nodectl.vm(vm_id).exec(create_token_cmd)
    if exitcode == 0:
        join_cmd = stdout.split()
        break

if not join_cmd:
    raise ValueError("can't get join_cmd")

log.debug("join_cmd", " ".join(join_cmd))
vmctl.exec(join_cmd)