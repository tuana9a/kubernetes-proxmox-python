import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
from app.error import *
from app import util


class WorkerController:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def create_worker(self,
                      vm_network_name,
                      worker_template_id,
                      control_plane_vm_ids,
                      preserved_ips=[],
                      vm_id_range=[0, 9999],
                      vm_name_prefix="i-",
                      vm_username="u",
                      vm_password="1",
                      vm_ssh_keys=None,
                      **kwargs):
        nodectl = self.nodectl
        log = self.log
        r = nodectl.describe_network(vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for ip in vm_network.hosts():
            ip_pool.append(str(ip))
        preserved_ips.append(network_gw_ip)
        log.debug("preserved_ips", preserved_ips)

        new_vm_id = nodectl.new_vm_id(vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"
        nodectl.clone(worker_template_id, new_vm_id)

        vmctl = nodectl.vm(new_vm_id)
        vmctl.update_config(
            name=new_vm_name,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
        )

        vmctl.resize_disk(disk="scsi0", size="+20G")
        vmctl.startup()
        vmctl.wait_for_guest_agent(timeout=5 * 60)

        join_cmd = None
        cmd = ["kubeadm", "token", "create", "--print-join-command"]
        for vm_id in control_plane_vm_ids:
            exitcode, stdout, _ = nodectl.vm(vm_id).exec(cmd)
            if exitcode == 0:
                join_cmd = stdout.split()
                break

        if not join_cmd:
            raise ValueError("can't get join_cmd")

        log.debug("join_cmd", " ".join(join_cmd))
        vmctl.exec(join_cmd)
        return new_vm_id

    def delete_worker(self,
                      vm_id,
                      control_plane_vm_ids,
                      drain_first=True,
                      **kwargs):
        nodectl = self.nodectl
        log = self.log

        vm_list = nodectl.list_vm()

        vm = None
        log.debug("len(vm_list)", len(vm_list))
        for x in vm_list:
            id = x["vmid"]
            if str(id) == str(vm_id):
                vm = x

        if not vm:
            log.error("vm", vm_id, "not found")
            raise VmNotFoundError(vm_id)

        log.debug("vm", vm)

        vm_name = vm["name"]
        kubeconfig_filepath = "/etc/kubernetes/admin.conf"

        for id in control_plane_vm_ids:
            try:
                vmctl = nodectl.vm(id)
                # drain the node before remove it
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain",
                    "--ignore-daemonsets", vm_name
                ]
                if drain_first:
                    vmctl.exec(cmd, interval_check=5,
                               timeout=30 * 60)  # 30 mins should be enough
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete",
                    "node", vm_name
                ]
                exitcode, _, _ = vmctl.exec(cmd, interval_check=3)
                if exitcode == 0:
                    break
            except Exception as err:
                log.error(err)

        vmctl = nodectl.vm(vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
        return vm_id
