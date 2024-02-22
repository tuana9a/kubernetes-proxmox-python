#!/usr/bin/env python3

import os
import time
import urllib3

from proxmoxer import ProxmoxAPI

from app.logger import Logger
from app.config import profiles

urllib3.disable_warnings()
log = Logger.DEBUG

config_path = os.getenv("CONFIG_PATH")
log.debug("config_path", config_path)
target_vm_id = os.getenv("VMID")
log.debug("target_vm_id",target_vm_id)

if not target_vm_id:
    raise ValueError("env: VMID is missing")
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

try:
    r = xlient.nodes(
        cfg.proxmox_node).qemu(target_vm_id).status.shutdown.post()
    log.debug("shutdown", r)
except Exception as err:
    log.debug(err)

status = None
timeout = 5 * 60
duration = 0
interval_check = 5
while True:
    log.debug("wait for vm to stop")
    time.sleep(interval_check)
    duration += interval_check
    if duration > timeout:
        log.debug("timeout reached")
        exit(1)
    r = xlient.nodes(cfg.proxmox_node).qemu(target_vm_id).status.current.get()
    status = r["status"]
    if status == "stopped":
        break
