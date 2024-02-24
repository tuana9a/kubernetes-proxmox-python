#!/usr/bin/env python3

import os
import urllib3

from proxmoxer import ProxmoxAPI

from app.logger import Logger
from app.config import load_config
from app.controller import NodeController

urllib3.disable_warnings()
log = Logger.DEBUG

config_path = os.getenv("CONFIG_PATH")
log.debug("config_path", config_path)
target_vm_id = os.getenv("VMID")
log.debug("target_vm_id", target_vm_id)

if not target_vm_id:
    raise ValueError("env: VMID is missing")
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
vm_id_range = cfg.get("vm_id_range", [0, 9999])

nodectl = NodeController(
    ProxmoxAPI(
        proxmox_host,
        user=proxmox_user,
        password=proxmox_password,
        verify_ssl=False,  # TODO: verify later with ca cert
    ),
    proxmox_node,
    log=log)

vm_list = nodectl.list_vm(vm_id_range[0], vm_id_range[1])

target_vm = None
log.debug("len(vm_list)", len(vm_list))
for vm in vm_list:
    vmid = vm["vmid"]
    if str(vmid) == str(target_vm_id):
        target_vm = vm
        break

if not target_vm:
    log.debug("vmid", target_vm_id, "not found")
    exit(1)

log.debug("vm", target_vm)

vmctl = nodectl.vm(target_vm_id)
vmctl.shutdown()
vmctl.wait_for_shutdown()
vmctl.delete()
