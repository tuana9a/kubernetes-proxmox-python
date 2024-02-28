#!/usr/bin/env python3

import urllib3

from proxmoxer import ProxmoxAPI

from app.controller import NodeController
from app.logger import Logger
from app.config import load_config

urllib3.disable_warnings()
log = Logger.from_env()

cfg = load_config(log=log)
proxmox_host = cfg["proxmox_host"]
proxmox_user = cfg["proxmox_user"]
proxmox_password = cfg["proxmox_password"]
proxmox_node = cfg["proxmox_node"]
control_plane_vm_ids = cfg.get("control_plane_vm_ids", None)

nodectl = NodeController(
    ProxmoxAPI(
        proxmox_host,
        user=proxmox_user,
        password=proxmox_password,
        verify_ssl=False,  # TODO: verify later with ca cert
    ),
    proxmox_node,
    log=log)

kubeconfig_filepath = "/etc/kubernetes/admin.conf"
cat_kubeconfig_cmd = ["cat", kubeconfig_filepath]
for vm_id in control_plane_vm_ids:
    exitcode, stdout, _ = nodectl.vm(vm_id).exec(cat_kubeconfig_cmd,
                                                 interval_check=3)
    print(stdout)
