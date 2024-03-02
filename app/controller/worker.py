import os
import ipaddress

from app.controller.node import NodeController
from app.logger import Logger
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
        vm_network_gw = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        vm_ip_pool = []
        for ip in vm_network.hosts():
            vm_ip_pool.append(str(ip))
        preserved_ips = preserved_ips
        preserved_ips.append(vm_network_gw)
        log.debug("preserved_ips", preserved_ips)

        vm_list = nodectl.list_vm()

        log.debug("len(vm_list)", len(vm_list))
        exist_vm_id = set()
        exist_vm_ip = set()
        exist_vm_ip.update(preserved_ips)
        for vm in vm_list:
            vm_id = vm["vmid"]
            exist_vm_id.add(vm_id)
            vm_config = nodectl.vm(vm_id).current_config()
            ifconfig0 = vm_config.get("ipconfig0", None)
            if not ifconfig0: continue
            vm_ip = util.ProxmoxUtil.extract_ip(ifconfig0)
            if vm_ip: exist_vm_ip.add(vm_ip)
        log.debug("exist_vm_id", exist_vm_id)
        log.debug("exist_vm_ip", exist_vm_ip)

        vm_id_new = util.find_missing_number(vm_id_range[0], vm_id_range[1],
                                             exist_vm_id)
        vm_name_new = f"{vm_name_prefix}{vm_id_new}"

        if not vm_id_new:
            log.debug("Error: can't find new id")
            exit(1)
        log.debug("newid", vm_id_new)

        vm_ip_new = util.find_missing(vm_ip_pool, exist_vm_ip)
        if not vm_ip_new:
            log.debug("Error: can't find new ip")
            exit(1)
        log.debug("new_ip", vm_ip_new)

        nodectl.clone(worker_template_id, vm_id_new)

        vmctl = nodectl.vm(vm_id_new)

        vmctl.update_config(
            name=vm_name_new,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={vm_ip_new}/24,gw={vm_network_gw}",
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

    def delete_worker(self,
                      target_vm_id,
                      control_plane_vm_ids,
                      drain_first=True,
                      **kwargs):
        nodectl = self.nodectl
        log = self.log

        vm_list = nodectl.list_vm()

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

        for vm_id in control_plane_vm_ids:
            try:
                vmctl = nodectl.vm(vm_id)
                # drain the node before remove it
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain",
                    "--ignore-daemonsets", target_vm_name
                ]
                if drain_first:
                    vmctl.exec(cmd, interval_check=5,
                               timeout=30 * 60)  # 30 mins should be enough
                cmd = [
                    "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete",
                    "node", target_vm_name
                ]
                exitcode, _, _ = vmctl.exec(cmd, interval_check=3)
                if exitcode == 0:
                    break
            except Exception as err:
                log.error(err)

        vmctl = nodectl.vm(target_vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
