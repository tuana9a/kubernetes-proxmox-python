#!/usr/bin/env python3

import os
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
vm_id_range = cfg.get("vm_id_range", [0, 9999])
load_balancer_vm_id = cfg.get("load_balancer_vm_id", None)
control_plane_vm_ids = cfg.get("control_plane_vm_ids", [])

nodectl = NodeController(
    ProxmoxAPI(
        proxmox_host,
        user=proxmox_user,
        password=proxmox_password,
        verify_ssl=False,  # TODO: verify later with ca cert
    ),
    proxmox_node,
    log=log)

vm_list = nodectl.list_vm()

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
# kubeadm reset is needed when deploying stacked control plane
# https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-reset/#reset-workflow
# Remove the control plane with etcd will avoid this error
# https://serverfault.com/questions/1029654/deleting-a-control-node-from-the-cluster-kills-the-apiserver
cmd = ["kubeadm", "reset", "-f"]

try:
    vmctl.exec(cmd)
except Exception as err:
    log.error(err)

if load_balancer_vm_id:
    target_vm_name = target_vm["name"]
    kubeconfig_filepath = "/etc/kubernetes/admin.conf"
    if len(control_plane_vm_ids):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node",
            target_vm_name
        ]
        for vm_id in control_plane_vm_ids:
            exitcode, _, _ = nodectl.vm(vm_id).exec(cmd, interval_check=3)
            if exitcode == 0:
                break

    lbctl = nodectl.vm(load_balancer_vm_id)
    cmd = [
        "/usr/local/bin/delete_backend_server_haproxy_cfg.py", "-c",
        "/etc/haproxy/haproxy.cfg", "-n", target_vm_id, "--backend-name",
        "control-plane"
    ]
    exitcode, stdout, stderr = lbctl.exec(cmd, interval_check=3)
    if exitcode != 0:
        log.error(str(stderr))
    lbctl.exec(["systemctl", "reload", "haproxy"], interval_check=3)

vmctl.shutdown()
vmctl.wait_for_shutdown()
vmctl.delete()
