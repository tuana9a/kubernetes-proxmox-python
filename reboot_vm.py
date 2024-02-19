#!/usr/bin/env python3

import os
import time
import urllib3

from proxmoxer import ProxmoxAPI

from app.logger import Logger
from app.config import profiles

urllib3.disable_warnings()

config_path = os.getenv("CONFIG_PATH")
target_vmid = os.getenv("VMID")

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

try:
    r = xlient.nodes(cfg.proxmox_node).qemu(target_vmid).status.reboot.post()
    log.debug("reboot", r)
except Exception as err:
    log.debug(err)
