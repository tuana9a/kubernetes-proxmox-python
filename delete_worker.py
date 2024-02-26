#!/usr/bin/env python3

import os
import urllib3

from proxmoxer import ProxmoxAPI

from app.logger import Logger
from app.config import load_config
from app.controller import NodeController

urllib3.disable_warnings()
log = Logger.DEBUG

target_vm_id = os.getenv("VMID")
log.debug("target_vm_id", target_vm_id)

if not target_vm_id:
    raise ValueError("env: VMID is missing")

cfg = load_config(log=log)
proxmox_host = cfg["proxmox_host"]
proxmox_user = cfg["proxmox_user"]
proxmox_password = cfg["proxmox_password"]
proxmox_node = cfg["proxmox_node"]
vm_id_range = cfg.get("vm_id_range", [0, 9999])
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

vm_list = nodectl.list_vm(vm_id_range[0], vm_id_range[1])

target_vm = None
log.debug("len(vm_list)", len(vm_list))
for vm in vm_list:
    vm_id = vm["vmid"]
    if str(vm_id) == str(target_vm_id):
        target_vm = vm

if not target_vm:
    log.debug("vmid", target_vm_id, "not found")
    exit(1)

log.debug("vm", target_vm)

target_vm_name = target_vm["name"]
kubeconfig_filepath = "/etc/kubernetes/admin.conf"
delete_node_cmd = [
    "kubectl", "delete", f"--kubeconfig={kubeconfig_filepath}", "node",
    target_vm_name
]

for vm_id in control_plane_vm_ids:
    # TODO: drain the node before remove it
    nodectl.vm(vm_id).exec(delete_node_cmd, interval_check=3)
vmctl = nodectl.vm(target_vm_id)
vmctl.shutdown()
vmctl.wait_for_shutdown()
vmctl.delete()
