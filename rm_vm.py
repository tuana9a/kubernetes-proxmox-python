#!/usr/bin/env python3

import os
import time
import urllib3

from proxmoxer import ProxmoxAPI
from kubernetes import config, client as klient

from app.logger import Logger
from app.config import profiles

config.load_kube_config()
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

r = xlient.nodes(cfg.proxmox_node).qemu.get()
vm_list = []
for vm in r:
    vmid = vm["vmid"]
    if (vmid >= cfg.proxmox_vm_id_range[0]
            and vmid <= cfg.proxmox_vm_id_range[1]):
        vm_list.append(vm)

target_vm = None
log.debug("len(vm_list)", len(vm_list))
for vm in vm_list:
    vmid = vm["vmid"]
    if str(vmid) == str(target_vmid):
        target_vm = vm

if not target_vm:
    log.debug("vmid", target_vmid, "not found")
    exit(1)

log.debug("vm", target_vm)

try:
    klient.CoreV1Api().delete_node(target_vm["name"])
except Exception as err:
    log.debug(err)

r = xlient.nodes(cfg.proxmox_node).qemu(target_vmid).status.shutdown.post()
log.debug("shutdown", r)

status = None
timeout = 5 * 60
duration = 0
interval_check = 5

while True:
    if duration > timeout:
        log.debug("shutdown timeout reached")
        exit(1)
    r = xlient.nodes(cfg.proxmox_node).qemu(target_vmid).status.current.get()
    status = r["status"]
    if status == "stopped":
        break
    log.debug("wait for vm to stop")
    time.sleep(interval_check)
    duration += interval_check

r = xlient.nodes(cfg.proxmox_node).qemu(target_vmid).delete()
log.debug("delete", r)
