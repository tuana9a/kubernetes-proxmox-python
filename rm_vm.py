#!/usr/bin/env python3

import os
import time
import urllib3

from proxmoxer import ProxmoxAPI

from app.logger import Logger
from app.config import load_config
from app.controller import NodeController

urllib3.disable_warnings()
log = Logger.from_env()

target_vm_id = os.getenv("VMID")
log.debug("target_vm_id", target_vm_id)

if not target_vm_id:
    raise ValueError("env: VMID is missing")

cfg = load_config(log=log)
proxmox_host = cfg["proxmox_host"]
proxmox_user = cfg["proxmox_user"]
proxmox_password = cfg["proxmox_password"]
proxmox_node = cfg["proxmox_node"]

nodectl = NodeController(
    ProxmoxAPI(
        proxmox_host,
        user=proxmox_user,
        password=proxmox_password,
        verify_ssl=False,  # TODO: verify later with ca cert
    ),
    proxmox_node,
    log=log)

vmctl = nodectl.vm(target_vm_id)
vmctl.shutdown()
vmctl.wait_for_shutdown()
vmctl.delete()
