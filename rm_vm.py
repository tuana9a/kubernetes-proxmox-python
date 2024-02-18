#!/usr/bin/env python3

import os
import time
import urllib3

from proxmoxer import ProxmoxAPI
from kubernetes import config, client as klient

from app.logger import Logger
from app.config import profiles

urllib3.disable_warnings()

config.load_kube_config()
config_path = os.getenv("CONFIG_PATH")
rm_vmid = os.getenv("VMID")

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

vm_list_response = xlient.nodes(cfg.proxmox_node).qemu.get()
vm_list = []
for vm in vm_list_response:
    vmid = vm["vmid"]
    if (vmid >= cfg.proxmox_vm_id_range[0]
            and vmid <= cfg.proxmox_vm_id_range[1]):
        vm_list.append(vm)

rm_vm = None
log.debug("len(vm_list)", len(vm_list))
for vm in vm_list:
    vmid = vm["vmid"]
    if str(vmid) == str(rm_vmid):
        rm_vm = vm

if not rm_vm:
    log.debug("vmid", rm_vmid, "not found")
    exit(1)

log.debug("rm_vm", rm_vm)

try:
    klient.CoreV1Api().delete_node(rm_vm["name"])
except Exception as err:
    print(err)

shutdown_vm_response = xlient.nodes(cfg.proxmox_node).qemu(rm_vmid).status.shutdown.post()
log.debug("shutdown_vm_response", shutdown_vm_response)

status = None

while status != "stopped":
    current_status_response = xlient.nodes(cfg.proxmox_node).qemu(rm_vmid).status.current.get()
    status = current_status_response["status"]
    log.debug("wait for vm to stop")
    time.sleep(5)

rm_vm_response = xlient.nodes(cfg.proxmox_node).qemu(rm_vmid).delete()
log.debug("rm_vm_response", rm_vm_response)
